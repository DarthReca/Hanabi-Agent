from collections import defaultdict, namedtuple
from typing import Dict, List, Optional

import numpy as np

import game_data
from constants import COLORS, DATASIZE, INITIAL_DECK
from game_utils import CardKnowledge

from .bot import Bot

Hint = namedtuple("Hint", ["to", "type", "value", "informativity"])


class Poirot(Bot):
    """
    Poirot is a base version for knowledge-based players. We are tracking each player knowledge of his hand.

    References
    ----------
    [1] T. Kato, H. Osawa, "I Know You Better Than You Know Yourself: Estimation of Blind Self Improves Acceptance for an Agent"
    """

    def __init__(
        self,
        host: str,
        port: int,
        player_name: str,
        games_to_play: int = 1,
        evolve: bool = False,
    ) -> None:
        super().__init__(host, port, player_name, games_to_play)
        self.players_knowledge = {
            self.player_name: []
        }  # type: Dict[str, List[CardKnowledge]]
        self.mutator.activate(evolve)

    def _process_game_start(self, action: game_data.ServerStartGameData) -> None:
        super()._process_game_start(action)
        # For each player create his knowledge
        self.initial_cards = 5 if len(self.players) < 4 else 4
        for player in self.players:
            self.players_knowledge[player] = [
                CardKnowledge() for _ in range(self.initial_cards)
            ]

    def _process_game_over(self, data: game_data.ServerGameOver):
        super()._process_game_over(data)
        for player in self.players:
            self.players_knowledge[player] = [
                CardKnowledge() for _ in range(self.initial_cards)
            ]

    def _elaborate_hint(self, hint: game_data.ServerHintData) -> None:
        self.turn_of = hint.player
        if self.turn_of == self.player_name:
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

    def _process_discard(self, action: game_data.ServerActionValid) -> None:
        super()._process_discard(action)
        self._delete_knowledge(
            action.lastPlayer, action.cardHandIndex, action.handLength
        )

    def _process_played_card(self, action: game_data.ServerPlayerMoveOk) -> None:
        super()._process_played_card(action)
        self._delete_knowledge(
            action.lastPlayer, action.cardHandIndex, action.handLength
        )

    def _process_error(self, action: game_data.ServerPlayerThunderStrike) -> None:
        super()._process_error(action)
        self._delete_knowledge(
            action.lastPlayer, action.cardHandIndex, action.handLength
        )

    def _update_infos(self, infos: game_data.ServerGameStateData) -> None:
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
            elif knowledge.preciousness(self.table) == 0:
                unknown_discardable.append(knowledge)
        if len(unknown_discardable) == 0:
            return None
        return self.players_knowledge[player_name].index(unknown_discardable[0])

    def _best_hint_for(self, player_name: str) -> Hint:
        """Select most informative hint for player."""
        # Cards in hand that can be played now
        really_playables = np.array(
            [
                (card.color, card.value) in self.table.next_playable_cards()
                for card in self.player_cards[player_name]
            ],
            dtype=np.bool8,
        )
        # Cards `player_name` knows are currently playable
        known_is_playable = np.array(
            [
                knowledge.playability(self.table) == 1
                for knowledge in self.players_knowledge[player_name]
            ],
            dtype=np.bool8,
        )
        # Try give color hint with unknown-playable cards, without including unplayable
        # Column 0: Color, Column 1: Informativity - Misinformativity
        informativity = np.empty([5, 2], dtype=np.int32)
        for i, color in enumerate(COLORS):
            # Card of given color
            cards_of_color = np.array(
                [card.color == color for card in self.player_cards[player_name]]
            )
            informativity[i, 0] = i
            informativity[i, 1] = np.sum(
                np.logical_not(known_is_playable) & really_playables & cards_of_color
            ) - np.sum(np.logical_not(really_playables) & cards_of_color)
        # Most informative without misinformations
        best_color_hint = np.copy(informativity[np.argmax(informativity[:, 1])])
        # Try give a value hint
        for i, value in enumerate(range(1, 6)):
            cards_of_value = np.array(
                [card.value == value for card in self.player_cards[player_name]]
            )
            informativity[i, 0] = value
            informativity[i, 1] = np.sum(
                np.logical_not(known_is_playable) & really_playables & cards_of_value
            ) - np.sum(np.logical_not(really_playables) & cards_of_value)
        # Most informative without misinformations
        best_value_hint = np.copy(informativity[np.argmax(informativity[:, 1])])

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
        if best[1].informativity <= 0:
            return None
        self.logger.info(f"Giving hint to {best[0]}: {repr(best[1])}")
        return best[1]

    def _hint_oldest_to_next_player(self) -> Hint:
        """Make an hint to give value information about the oldest card of the next player."""
        next_player = self._next_player(self.player_name)
        player_hand = self.player_cards[next_player]
        player_knol = self.players_knowledge[next_player]
        oldest_card = player_hand[0]
        for i, card in enumerate(player_hand):
            if len(player_knol[i].possible_values()) != 1:
                oldest_card = card
                break
        cards_with_value = [
            card for card in player_hand if card.value == oldest_card.value
        ]
        return Hint(next_player, "value", oldest_card.value, len(cards_with_value))

    def _select_probably_not_precious(self, max_preciousness: float) -> Optional[int]:
        """Select card with preciousness <= `max_preciousness`"""
        preciousness = np.array(
            [
                knowledge.preciousness(self.table)
                for knowledge in self.players_knowledge[self.player_name]
            ]
        )
        less_precious = np.argmin(preciousness)
        if preciousness[less_precious] <= max_preciousness:
            self.logger.info(
                f"Not precious with at most {max_preciousness}: {self.players_knowledge[self.player_name][less_precious]}"
            )
            return less_precious
        return None

    def _select_probably_safe(self, min_safeness: float) -> Optional[int]:
        """Select card with playability >= `min_safeness`"""
        curr_knol = self.players_knowledge[self.player_name]
        playabilities = np.array([k.playability(self.table) for k in curr_knol])
        safest = len(curr_knol) - np.argmax(np.flip(playabilities)) - 1
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
        current_knol = self.players_knowledge[self.player_name]
        # Play if possible
        hint = self._select_valuable_warning()
        if hint is not None:
            self.logger.info(f"Giving hint {repr(hint)}")
            self._give_hint(hint.to, hint.type, hint.value)
            return
        card_index = self._select_probably_safe(1.0)
        if card_index is not None:
            self.logger.info(f"Playing {card_index}: {current_knol[card_index]}")
            self._play(card_index)
            return
        hint = self._select_helpful_hint()
        if hint is not None:
            self.logger.info(f"Giving hint {repr(hint)}")
            self._give_hint(hint.to, hint.type, hint.value)
            return
        if len(current_knol) < 5:
            card_index = self._select_probably_safe(0.5)
            if card_index is not None:
                self.logger.info(f"Playing {current_knol[card_index]}")
                self._play(card_index)
                return

        if self.remaining_hints < 8:
            card_index = self._select_probably_useless(0.0)
            if card_index is not None:
                self.logger.info(f"Discarding {card_index}: {current_knol[card_index]}")
                self._discard(card_index)
                return
            card_index = self._next_discard_index(self.player_name)
            if card_index is not None:
                self.logger.info(f"Discarding {card_index}: {current_knol[card_index]}")
                self._discard(card_index)
                return
            card_index = self._select_probably_not_precious(0.5)
            if card_index is not None:
                self.logger.info(f"Discarding {card_index}: {current_knol[card_index]}")
                self._discard(card_index)
                return

        if self.remaining_hints > 0:
            hint = self._hint_oldest_to_next_player()
            self.logger.info(f"Giving hint {repr(hint)}")
            self._give_hint(hint.to, hint.type, hint.value)
        else:
            card_index = self._select_probably_not_precious(1.0)
            if card_index is not None:
                self.logger.info(f"Discarding {card_index}: {current_knol[card_index]}")
                self._discard(card_index)
                return

    def run(self) -> None:
        super().run()
        while True:
            try:
                data = self.socket.recv(DATASIZE)
                data = game_data.GameData.deserialize(data)
            except:
                self.logger.error("Socket Error")
                self._disconnect()
                break
            # Process infos
            if type(data) is game_data.ServerActionInvalid:
                self._process_invalid(data)
                self.turn_of = ""
                continue
            if type(data) is game_data.ServerPlayerThunderStrike:
                self._process_error(data)
            if type(data) is game_data.ServerStartGameData:
                self._process_game_start(data)
            if type(data) is game_data.ServerActionValid:
                self._process_discard(data)
            if type(data) is game_data.ServerHintData:
                self._elaborate_hint(data)
            if type(data) is game_data.ServerGameStateData:
                self._update_infos(data)
            if type(data) is game_data.ServerPlayerMoveOk:
                self._process_played_card(data)
            if type(data) is game_data.ServerGameOver:
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
