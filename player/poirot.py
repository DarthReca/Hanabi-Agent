from operator import ne
from time import sleep
from .bot import Bot
from game_utils import Table, CardKnowledge
import numpy as np
from constants import COLORS, INITIAL_DECK, DATASIZE
from typing import Literal, Optional, Tuple, Dict, List, Set, Union
import GameData
from collections import namedtuple, defaultdict

Hint = namedtuple("Hint", ["to", "type", "value", "informativity"])


class Poirot(Bot):
    def __init__(
        self, host: str, port: int, player_name: str, games_to_play: int = 1
    ) -> None:
        super().__init__(host, port, player_name, games_to_play)
        self.players_knowledge = {self.player_name: [CardKnowledge() for _ in range(5)]}

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

    def _find_duplicates(self) -> int:
        knowns = defaultdict(lambda _: [])

        for i, knowl in enumerate(self.players_knowledge[self.player_name]):
            if knowl.is_known():
                knowns[
                    (knowl.possible_colors().pop(), knowl.possible_values().pop())
                ].append(i)

        for v in knowns.values():
            if len(v) > 1:
                return v[0]

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
            if (
                knowledge.preciousness(self.table, self._count_cards_in_hands()) == 0
                and value_to_avoid in knowledge.possible_values()
            ):
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
            return Hint(
                player_name, "value", best_value_hint.item(0), best_value_hint.item(1)
            )
        return Hint(
            player_name,
            "color",
            COLORS[best_color_hint.item(0)],
            best_color_hint.item(1),
        )

    def _select_valuable_warning(self) -> Optional[Hint]:
        # Cannot give any hint
        if self.remaining_hints == 0:
            return None
        next_player = self._next_player(self.player_name)
        discard_index = self._next_discard_index(next_player)
        # Player knows which card to play/discard
        if discard_index is None:
            return None
        discard_card = self.player_cards[next_player][discard_index]
        valuables = self._valuable_mask_of_player(next_player)
        # Player wants to discard a useless card
        if not valuables[COLORS.index(discard_card.color), discard_card.value - 1]:
            return None
        # Necessary to give a warning
        cards_of_value = [
            card
            for card in self.player_cards[next_player]
            if card.value == discard_card.value
        ]
        self.logger.info(
            f"Warning to {next_player} for card {discard_card.color}:{discard_card.value}"
        )
        return Hint(next_player, "value", discard_card.value, len(cards_of_value))

    def _select_helpful_hint(self) -> Optional[Hint]:
        if self.remaining_hints == 0:
            return None
        hints = [
            (player, self._best_hint_for(player))
            for player in self.players
            if player != self.player_name
        ]
        best = max(hints, key=lambda x: x[1].informativity)
        if best[1].informativity == 0:
            return None
        self.logger.info(f"Giving hint to {best[0]}: {repr(best[1])}")
        return best[1]

    def _hint_oldest_to_next_player(self) -> Hint:
        """Make an hint to give value information about the oldest card of the next player."""
        next_player = self._next_player(self.player_name)
        oldest_card = self.player_cards[next_player][0]
        cards_with_value = [
            card
            for card in self.player_cards[next_player]
            if card.value == oldest_card.value
        ]
        return Hint(next_player, "value", oldest_card.value, len(cards_with_value))

    def _select_probably_not_precious(self, max_preciousness: float) -> Optional[int]:
        """Select card with preciousness <= `max_preciousness`"""
        cards_in_hands = self._count_cards_in_hands()
        preciousness = np.array(
            [
                knowledge.preciousness(self.table, cards_in_hands)
                for knowledge in self.players_knowledge[self.player_name]
            ]
        )
        less_precious = np.argmin(preciousness)
        if less_precious <= max_preciousness:
            self.logger.info(
                f"Not precious with at most {max_preciousness}: {self.players_knowledge[self.player_name][less_precious]}"
            )
            return less_precious
        return None

    def _select_probably_safe(self, min_safeness: float) -> Optional[int]:
        """Select card with playability >= `min_safeness`"""
        playabilities = np.array(
            [
                k.playability(self.table)
                for k in self.players_knowledge[self.player_name]
            ]
        )
        safest = np.argmax(np.flip(playabilities))
        if playabilities[safest] >= min_safeness:
            self.logger.info(
                f"Safest card with at least {min_safeness}: {self.players_knowledge[self.player_name][safest]}"
            )
            return safest
        return None

    def _select_probably_useless(self, max_usability: float) -> Optional[int]:
        """Select the card with usability <= `max_usability`"""
        usabilities = np.array(
            [k.usability(self.table) for k in self.players_knowledge[self.player_name]]
        )
        most_useless = np.argmin(usabilities)
        if usabilities[most_useless] <= max_usability:
            self.logger.info(
                f"Useless card with at most {max_usability}: {self.players_knowledge[self.player_name][most_useless]}"
            )
            return most_useless
        return None

    def _make_action(self) -> None:
        cards = {
            k: [(c.color, c.value) for c in v] for k, v in self.player_cards.items()
        }
        self.logger.debug(repr(cards))
        current_knol = self.players_knowledge[self.player_name]
        # Play if possible
        card_to_play = self._select_probably_safe(1.0)
        if card_to_play is not None:
            self.logger.info(f"Playing {current_knol[card_to_play]}")
            self._play(card_to_play)
            return
        # Hint for warning
        hint = self._select_valuable_warning()
        if hint is not None:
            self.logger.info(f"Hinting {hint}")
            self._give_hint(hint.to, hint.type, hint.value)
            return
        # Useful hint
        hint = self._select_helpful_hint()
        if hint is not None:
            self.logger.info(f"Hinting {hint}")
            self._give_hint(hint.to, hint.type, hint.value)
            return
        # Discard if possible
        card_to_discard = self._select_probably_useless(1.0)
        if card_to_discard is not None and self.remaining_hints < 8:
            self.logger.info(f"Discarding {current_knol[card_to_discard]}")
            self._discard(card_to_discard)
            return

        for p in np.flip(np.linspace(0.0, 0.9, 10)):
            if self.remaining_hints < 8:
                card_to_discard = self._select_probably_useless(p)
                if card_to_discard is not None:
                    self.logger.info(
                        f"Discarding {current_knol[card_to_discard]} with p={p}"
                    )
                    self._discard(card_to_discard)
                    return
            elif self.lives > 1 and len(self.players_knowledge[self.player_name]) < 4:
                card_to_play = self._select_probably_safe(p)
                if card_to_play is not None:
                    self.logger.info(f"Playing {current_knol[card_to_play]} with p={p}")
                    self._play(card_to_play)
                    return
            else:
                hint = self._hint_oldest_to_next_player()
                self._give_hint(hint.to, hint.type, hint.value)

        """ Original Holmes
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
            self._tell_about_oldest_to_next()
        else:
            if self._maybe_discard_useless():
                return
            if self._maybe_discard_old_card():
                return
            self._discard_less_precious()
        """

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
            if type(data) is GameData.ServerActionInvalid:
                self._process_invalid(data)
                self.turn_of = ""
                continue
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
            if type(data) is GameData.ServerGameOver:
                self._process_game_over(data)

            # break
            # Exec bot turn
            if self.turn_of == self.player_name:
                if self.need_info:
                    self.logger.debug("Requesting infos...")
                    self._get_infos()
                else:
                    self.logger.info(f"Making turn of {self.turn_of}")
                    self._make_action()
