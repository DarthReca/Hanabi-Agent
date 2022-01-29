from time import sleep
from .bot import Bot
from game_utils import Table, CardKnowledge
import numpy as np
from constants import COLORS, INITIAL_DECK, DATASIZE
from typing import Literal, Optional, Tuple, Dict, List, Set
import GameData
from collections import namedtuple

Hint = namedtuple("Hint", ["type", "value", "informativity"])


class Poirot(Bot):
    def __init__(
        self, host: str, port: int, player_name: str, games_to_play: int = 1
    ) -> None:
        super().__init__(host, port, player_name, games_to_play)
        self.players_knowledge = {self.player_name: [CardKnowledge() for _ in range(5)]}
        # self.socket.settimeout(10)

    def _process_game_start(self, action: GameData.ServerStartGameData) -> None:
        super()._process_game_start(action)
        # For each player create his knowledge
        for player in self.players:
            self.players_knowledge[player] = [CardKnowledge() for _ in range(5)]

    def _process_game_over(self, data: GameData.ServerGameOver):
        super()._process_game_over(data)
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
        self._delete_knowledge(
            action.lastPlayer, action.cardHandIndex, action.handLength
        )

    def _process_played_card(self, action: GameData.ServerPlayerMoveOk) -> None:
        super()._process_played_card(action)
        self._delete_knowledge(
            action.lastPlayer, action.cardHandIndex, action.handLength
        )

    def _process_error(self, action: GameData.ServerPlayerThunderStrike) -> None:
        super()._process_error(action)
        self._delete_knowledge(
            action.lastPlayer, action.cardHandIndex, action.handLength
        )

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        super()._update_infos(infos)
        for possibility in self.players_knowledge[self.player_name]:
            possibility.remove_cards(
                self._count_cards_in_hands() + self.table.total_table_card()
            )
        self.need_info = False

    def _delete_knowledge(self, player_name: str, index: int, new_hand_lenght: int):
        self.players_knowledge[player_name].pop(index)
        if new_hand_lenght != len(self.players_knowledge[player_name]):
            self.players_knowledge[player_name].append(CardKnowledge())

    def _valuable_mask_of_player(self, target_player: str) -> np.ndarray:
        target_hand_mask = self._cards_to_ndarray(*self.player_cards[target_player]) > 0
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
                    COLORS.index(knowledge.possible_colors().pop()),
                    knowledge.possible_values().pop() - 1,
                ] -= 1
        return (valuables == 1) & self.table.playables_mask() & target_hand_mask

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

        self.logger.info(
            f"Playing card n. {card_index}: {knowledge.possible_colors()} | {knowledge.possible_values()}"
        )

        self._play(card_index)
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

        self.logger.info(
            f"Discarding card n. {card_index}: {discardable[0].possible_colors()} | {discardable[0].possible_values()}"
        )

        self._discard(card_index)
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
        return self.players_knowledge[player_name].index(unknown_discardable[0])

    def _best_hint_for(self, player_name: str) -> Hint:
        """Select most informative hint for player. Return (color, inted_color) or (value, inted_value)"""
        # Cards in hand that can be played now
        really_playables = np.array(
            [
                (card.color, card.value) in self.table.next_playable_cards()
                for card in self.player_cards[player_name]
            ],
            dtype=np.bool8,
        )
        # Cards `player_name` knows are curretly playable
        known_is_playable = np.array(
            [
                knowledge.playability(self.table) == 1
                for knowledge in self.players_knowledge[player_name]
            ],
            dtype=np.bool8,
        )
        # Try give color hint with unknown-playable cards, without including unplayable
        # Column 0: Color, Column 1: Informativity. Column 2: Misinformativity
        informativity = np.empty([5, 3], dtype=np.uint8)
        for i, color in enumerate(COLORS):
            # Card of given color
            cards_of_color = np.array(
                [card.color == color for card in self.player_cards[player_name]]
            )
            informativity[i, 0] = i
            informativity[i, 1] = np.sum(
                np.logical_not(known_is_playable) & really_playables & cards_of_color
            )
            informativity[i, 2] = np.sum(
                np.logical_not(really_playables) & cards_of_color
            )
        # Most informative without misinformations
        non_mis = informativity[informativity[:, 2] == 0]
        best_color_hint = np.zeros([3], dtype=np.uint8)
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
            if value_to_avoid == value:
                informativity[i] = np.array([i, 0, 100])
                continue
            cards_of_value = np.array(
                [card.value == value for card in self.player_cards[player_name]]
            )
            informativity[i, 0] = value
            informativity[i, 1] = np.sum(
                np.logical_not(known_is_playable) & really_playables & cards_of_value
            )
            informativity[i, 2] = np.sum(
                np.logical_not(really_playables) & cards_of_value
            )
        # Most informative without misinformations
        non_mis = informativity[informativity[:, 2] == 0]
        best_value_hint = np.zeros([3], dtype=np.uint8)
        if non_mis.shape[0] != 0:
            best_value_hint = np.copy(informativity[np.argmax(non_mis[:, 1])])

        if best_value_hint[1] > best_color_hint[1]:
            return Hint("value", best_value_hint.item(0), best_value_hint.item(1))
        return Hint("color", COLORS[best_color_hint.item(0)], best_color_hint.item(1))

    def _maybe_give_valuable_warning(self) -> bool:
        next_player = self._next_player(self.player_name)
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
        self.logger.info(
            f"Warning to {next_player} for card {discard_card.color}:{discard_card.value}"
        )
        # Necessary to give a warning
        self._give_hint(next_player, "value", discard_card.value)
        return True

    def _maybe_give_helpful_hint(self) -> bool:
        if self.remaining_hints == 0:
            return False
        hints = [
            (player, self._best_hint_for(player))
            for player in self.players
            if player != self.player_name
        ]
        best = max(hints, key=lambda x: x[1].informativity)
        if best[1].informativity == 0:
            return False
        self.logger.info(f"Giving hint to {best[0]}: {repr(best[1])}")
        self._give_hint(best[0], best[1].type, best[1].value)
        return True

    def _maybe_play_unknown(self) -> bool:
        remaining = np.sum(
            INITIAL_DECK
            - self.table.total_table_card()
            - self._count_cards_in_hands()
            - 5
        )
        if remaining > 3:
            return False
        player_knowledge = self.players_knowledge[self.player_name]
        for i, knowledge in enumerate(reversed(player_knowledge)):
            if knowledge.playability(self.table) != 0:
                self.logger.info(
                    f"Playing unknown {len(player_knowledge) - 1 - i}: {knowledge.possible_colors()} | {knowledge.possible_values()}"
                )
                self._play(len(player_knowledge) - 1 - i)
                return True
        return False

    def _maybe_discard_old_card(self) -> bool:
        remaining_cards = np.sum(
            INITIAL_DECK - self._count_cards_in_hands() - self.table.total_table_card()
        )
        # Cards in hand
        remaining_cards -= 5
        if remaining_cards <= 1:
            for i, knowledge in enumerate(self.players_knowledge[self.player_name]):
                if (
                    knowledge.preciousness(self.table, self._count_cards_in_hands())
                    == 0
                ):
                    self.logger.info(
                        f"Discarding old {i}: {knowledge.possible_colors()} | {knowledge.possible_values()} "
                    )
                    self._discard(i)
                    return True
        return False

    def _discard_less_precious(self):
        cards_in_hands = self._count_cards_in_hands()
        preciousness = [
            knowledge.preciousness(self.table, cards_in_hands)
            for knowledge in self.players_knowledge[self.player_name]
        ]
        less_precious = preciousness.index(min(preciousness))
        selected_card = self.players_knowledge[self.player_name][less_precious]
        self.logger.info(
            f"Discard less precious {less_precious}: {selected_card.possible_colors()} | {selected_card.possible_values()}"
        )
        self._discard(less_precious)

    def _make_action(self) -> None:
        cards = {
            k: [(c.color, c.value) for c in v] for k, v in self.player_cards.items()
        }
        self.logger.debug(repr(cards))
        if self._maybe_give_valuable_warning():
            return
        if self._maybe_play_lowest_value():
            return
        if self._maybe_give_helpful_hint():
            return
        if self._maybe_play_unknown():
            return
        # Try discard if possible, otherwise give value hint on oldest card
        if self.remaining_hints == 8:
            next_player = self._next_player(self.player_name)
            oldest_card = self.player_cards[next_player][0]
            self._give_hint(next_player, "value", oldest_card.value)
        else:
            if self._maybe_discard_useless():
                return
            if self._maybe_discard_old_card():
                return
            self._discard_less_precious()

    def run(self) -> None:
        super().run()
        while True:
            try:
                data = self.socket.recv(DATASIZE)
                data = GameData.GameData.deserialize(data)
            except:
                self.logger.error("Socket Error")
                self._disconnect()
                break
            # Process infos
            if type(data) is GameData.ServerPlayerThunderStrike:
                self._process_error(data)
            if type(data) is GameData.ServerStartGameData:
                self._process_game_start(data)
            if type(data) is GameData.ServerActionValid:
                self._process_discard(data)
            if type(data) is GameData.ServerHintData:
                self._elaborate_hint(data)
            if type(data) is GameData.ServerGameStateData:
                self._update_infos(data)
            if type(data) is GameData.ServerPlayerMoveOk:
                self._process_played_card(data)
            if type(data) is GameData.ServerActionInvalid:
                self._process_invalid(data)
                self.need_info = True
            if type(data) is GameData.ServerGameOver:
                self._process_game_over(data)
                # break
            # Exec bot turn
            if self.turn_of == self.player_name:
                if self.need_info:
                    self.logger.info(f"Making turn of {self.turn_of}")
                    self._get_infos()
                    self.need_info = False
                else:
                    self._make_action()
