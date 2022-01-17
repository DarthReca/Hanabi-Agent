import enum
import re
from .bot import Bot, Table
import numpy as np
from constants import COLORS, INITIAL_DECK, DATASIZE
from typing import Literal, Optional, Tuple, Dict, List, Set
import GameData
from itertools import product
from game import Card
from collections import namedtuple

Hint = namedtuple("Hint", ["type", "value", "informativity"])


class CardKnowledge:
    def __init__(self) -> None:
        # Rows are colors, Columns are (values - 1)
        self.canbe = np.ones([5, 5], dtype=np.bool8)

    def possible_values(self) -> np.ndarray:
        return np.nonzero(self.can_be == True)[1] + 1

    def possible_colors(self) -> Set[str]:
        return {COLORS[c] for c in np.nonzero(self.can_be == True)[0]}

    def set_suggested_color(self, color: str):
        index = COLORS.index(color)
        mask = np.zeros([5, 5], dtype=np.bool8)
        mask[index] = True
        self.canbe &= mask

    def set_suggested_value(self, value: int):
        index = value - 1
        mask = np.zeros([5, 5], dtype=np.bool8)
        mask[:, index] = True
        self.canbe &= mask

    def remove_cards(self, cards: np.ndarray):
        self.canbe &= INITIAL_DECK - cards != 0

    def can_be(self, color: Optional[str], value: Optional[int]) -> bool:
        if color is None and value is None:
            return True
        color_index = np.arange(5)
        value_index = np.arange(5)
        if not color is None:
            color_index = COLORS.index(color)
        if not value is None:
            value_index = value - 1
        return np.any(self.canbe[color_index, value_index])

    def preciousness(self, table: Table, players_cards: np.ndarray) -> float:
        """Probability the card could be a valuable one (it could be the only card of this type)"""
        valuables = INITIAL_DECK - players_cards - table.total_table_card() == 1
        return np.sum(self.canbe & valuables & table.playables_mask()) / np.sum(
            self.canbe
        )

    def playability(self, table: Table) -> float:
        """Probability the card is currently playable"""
        return np.sum(self.can_be & table.next_playables_mask()) / np.sum(self.can_be)

    def usability(self, table: Table) -> float:
        """Probability the card can still be played"""
        return np.sum(self.can_be & table.playables_mask()) / np.sum(self.can_be)

    def is_known(self) -> bool:
        return len(self.possible_colors()) == 1 and self.possible_values().shape[0] == 1


class Poirot(Bot):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.players_knowledge = {self.player_name: [CardKnowledge() for _ in range(5)]}

    def _process_game_start(self, action: GameData.ServerStartGameData) -> None:
        super()._process_game_start(action)
        # For each player create his knowledge
        for player in self.players:
            self.players_knowledge[player] = [CardKnowledge() for _ in range(5)]

    def _elaborate_hint(self, hint: GameData.ServerHintData) -> None:
        self.turn_of = hint.player
        self.need_info = True
        for i in hint.positions:
            if hint.type == "value":
                self.players_knowledge[hint.destination][i].set_suggested_value(
                    hint.value
                )
            else:
                self.players_knowledge[hint.destination][i].set_suggested_color(
                    hint.value
                )

    def _process_discard(self, action: GameData.ServerActionValid) -> None:
        super()._process_discard(action)
        self._delete_knowledge(action.lastPlayer, action.cardHandIndex)

    def _process_played_card(self, action: GameData.ServerPlayerMoveOk) -> None:
        super()._process_played_card(action)
        self._delete_knowledge(action.lastPlayer, action.cardHandIndex)

    def _process_error(self, action: GameData.ServerPlayerThunderStrike) -> None:
        super()._process_error(action)
        self._delete_knowledge(action.lastPlayer, action.cardHandIndex)

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        super()._update_infos(infos)
        for possibility in self.players_knowledge[self.player_name]:
            possibility.remove_cards(
                self._count_cards_in_hands() + self.table.total_table_card()
            )

    def _delete_knowledge(self, player_name: str, index: int):
        self.players_knowledge[player_name].pop(index)
        self.players_knowledge[player_name].append(CardKnowledge())

    def _valuable_mask_of_player(self, target_player: str) -> np.ndarray:
        target_hand = self._cards_to_ndarray(*self.player_cards[target_player])
        # Remove cards in table
        valuables = INITIAL_DECK - self.table.total_table_card()
        # Remove cards in other players hand
        for player, hand in self.player_cards.items():
            if player != target_player:
                valuables -= self._cards_to_ndarray(*hand)
        # Remove cards I know I have in my hand
        for knowledge in self.players_knowledge[self.player_name]:
            if knowledge.is_known():
                valuables[
                    COLORS.index(knowledge.possible_colors()[0]),
                    knowledge.possible_values().item(0) - 1,
                ] -= 1
        return valuables == 1 & self.table.playables_mask() & target_hand > 0

    def _maybe_play_lowest_value(self) -> bool:
        """Play a card we are sure can be played with the lowest value possible"""
        playables = [
            x
            for x in self.players_knowledge[self.player_name]
            if x.playability(self.table) == 1
        ]
        if len(playables) == 0:
            return False
        knowledge = min(
            playables,
            key=lambda x: np.min(x.possible_values()),
        )
        card_index = self.players_knowledge[self.player_name].index(knowledge)
        self._play(card_index)
        self._delete_knowledge(card_index)
        return True

    def _maybe_discard_useless(self) -> bool:
        """Discard the oldest card we are sure is not usable anymore"""
        discardable = [
            x
            for x in self.players_knowledge[self.player_name]
            if x.usability(self.table) == 0
        ]
        if len(discardable) == 0:
            return False
        # Discard oldest
        card_index = self.players_knowledge[self.player_name].index(discardable[0])
        self._discard(card_index)
        self._delete_knowledge(card_index)
        return True

    def _next_discard_index(self, player_name: str) -> Optional[int]:
        """Select the next card to discard if there is no sure card to play or discard"""
        unknown_discardable = []
        for knowledge in self.players_knowledge[player_name]:
            if (
                knowledge.playability(self.table) == 1
                or knowledge.usability(self.table) == 0
            ):
                return None
            elif knowledge.preciousness(self.table, self._count_cards_in_hands()) == 0:
                unknown_discardable.append(knowledge)
        if len(unknown_discardable) == 0:
            return None
        return self.players_knowledge[self.player_name].index(unknown_discardable[0])

    def _best_hint_for(self, player_name: str) -> Hint:
        """Select most informative hint for player. Return (color, inted_color) or (value, inted_value)"""
        # Cards in hand that can be played now
        really_playables = np.array(
            [
                (card.color, card.value) in self.table.next_playable_cards()
                for card in self.player_cards[player_name]
            ]
        )
        # Cards `player_name` knows are curretly playable
        known_is_playable = np.array(
            [
                knowledge.playability(self.table) == 1
                for knowledge in self.players_knowledge[player_name]
            ]
        )
        # Try give color hint with unknown-playable cards, without including unplayable
        # Column 0: Color, Column 1: Informativity. Column 2: Misinformativity
        informativity = np.array([5, 3])
        for i, color in enumerate(COLORS):
            # Card of given color
            cards_of_color = np.array(
                [card.color == color for card in self.player_cards[player_name]]
            )
            informativity[i, 0] = i
            informativity[i, 1] = np.sum(
                np.logical_not(known_is_playable) & really_playables & cards_of_color
            )
            informativity[i, 2] = np.logical_not(really_playables) & cards_of_color
        # Most informative without misinformations
        non_mis = informativity[informativity[:, 2] == 0]
        best_color_hint = np.zeros([3])
        if non_mis.shape[0] != 0:
            best_color_hint = np.copy(informativity[np.argmax(non_mis[:, 1])])
        # Avoid giving hint that could be interpreted as warnings (avoid precious cards)
        next_discard = self._next_discard_index(player_name)
        value_to_avoid = -1
        if next_discard is not None:
            value_to_avoid = self.player_cards[player_name][next_discard].value
            knowledge = self.players_knowledge[player_name][next_discard]
            if knowledge.preciousness(
                self.table, self._count_cards_in_hands()
            ) == 0 and knowledge.can_be(None, value_to_avoid):
                value_to_avoid = -1

        # Try give a value hint
        for i, value in enumerate(range(1, 6)):
            if value_to_avoid:
                informativity[i] = np.array([i, 0, 100])
                continue
            cards_of_value = np.array(
                [card.value == value for card in self.player_cards[player_name]]
            )
            informativity[i, 0] = value
            informativity[i, 1] = np.sum(
                np.logical_not(known_is_playable) & really_playables & cards_of_value
            )
            informativity[i, 2] = np.logical_not(really_playables) & cards_of_value
        # Most informative without misinformations
        non_mis = informativity[informativity[:, 2] == 0]
        best_value_hint = np.zeros([3])
        if non_mis.shape[0] != 0:
            best_value_hint = np.copy(informativity[np.argmax(non_mis[:, 1])])

        if best_value_hint[1] > best_color_hint[1]:
            return Hint("value", best_value_hint.item(0), best_value_hint.item(1))
        return Hint("color", best_color_hint.item(0), best_color_hint.item(1))

    def _maybe_give_valuable_warning(self) -> bool:
        next_player_index = (self.players.index(self.player_name) + 1) % len(
            self.players
        )
        next_player = self.players[next_player_index]
        discard_index = self._next_discard_index(next_player)
        # Player knows which card to play/discard
        if discard_index is None:
            return False
        discard_card = self.player_cards[next_player][discard_index]
        valuables = self._valuable_mask_of_player(next_player)
        # Player wants to discard a useless card
        if not valuables[COLORS.index(discard_card.color), discard_card.value - 1]:
            return False
        # Cannot give any hint
        if self.remaining_hints == 0:
            return False
        hint = self._best_hint_for(next_player)
        # Found an hint to suggest player another action
        if hint.informativity > 0:
            self._give_hint(next_player, hint.type, hint.value)
            return True
        # Necessary to give a warning
        self._give_hint(next_player, "value", discard_card.value)
        return True

    def run(self) -> None:
        super().run()
        while True:
            data = self.socket.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
            # Process infos
            if type(data) is GameData.ServerPlayerStartRequestAccepted:
                self._process_start_request(data)
            if type(data) is GameData.ServerStartGameData:
                self._process_game_start(data)
            if type(data) is GameData.ServerActionValid:
                self._process_discard(data)
            if type(data) is GameData.ServerHintData:
                self._elaborate_hint(data)
            if type(data) is GameData.ServerGameStateData:
                self._update_infos(data)
            # Exec bot turn
            if self.turn_of == self.player_name:
                print("My turn")
                if self.need_info:
                    self._get_infos()
                    self.need_info = False
