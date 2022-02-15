from collections import Counter
from typing import Optional

import numpy as np
from scipy.ndimage.interpolation import shift

from server import ServerHintData

from .canaan_bot import CanaanBot
from .poirot import Hint


class HumanBot(CanaanBot):
    def __init__(self, host: str, port: int, player_name: str):
        super().__init__(host, port, player_name)
        # (ValueMarked, ColorMarked)
        self.marked = np.zeros([self.initial_cards, 2], dtype=np.bool8)
        self.hinted_as_playable = None

    def _elaborate_hint(self, hint: ServerHintData) -> None:
        super()._elaborate_hint(hint)
        self.marked[hint.positions, 0 if hint.type == "value" else 1] = True
        if hint.type == "color":
            self.hinted_as_playable = hint.positions[-1]

    def _delete_knowledge(self, player_name: str, index: int, new_hand_lenght: int):
        super()._delete_knowledge(player_name, index, new_hand_lenght)
        if player_name == self.player_name:
            self.marked[index:] = shift(self.marked[index + 1 :], [-1, 0], cval=False)

    def _make_color_clue(self, target_player: str) -> Optional[Hint]:
        player_hand = self.player_cards[target_player]
        player_knowledge = self.players_knowledge[target_player]
        playables = np.array(
            [
                (c.color, c.value) in self.table.next_playable_cards()
                for c in player_hand
            ]
        )
        known_playables = np.array(
            [c.playability(self.table) == 1 for c in player_knowledge]
        )
        if not np.any(playables & np.logical_not(known_playables)):
            return None

        hintables = []
        for i in np.nonzero(playables & np.logical_not(known_playables)):
            # Card of given color
            cards_of_color = np.array(
                [card.color == player_hand[i].color for card in player_hand]
            )
            # The newest card of color must be playable
            if np.sum(cards_of_color[i:]) == 1:
                hintables.append((player_hand[i].color, np.sum(cards_of_color)))
        if len(hintables) == 0:
            return None
        best_color = max(hintables, key=lambda x: x[1])
        return Hint(target_player, "color", best_color[0], best_color[1])

    def _make_value_clue(self, target_player: str) -> Optional[Hint]:
        player_hand = self.player_cards[target_player]
        player_knowledge = self.players_knowledge[target_player]
        precious_cards = np.array(
            [(c.color, c.value) in self.table.precious_cards() for c in player_hand]
        )
        known_precious = np.array(
            [k.preciousness(self.table) == 1 for k in player_knowledge]
        )

        values_to_hint = Counter(
            [
                player_hand[i].value
                for i in np.nonzero(precious_cards & np.logical_not(known_precious))
            ]
        )
        if len(values_to_hint) != 0:
            best_hint = values_to_hint.most_common(1)[0]
            return Hint(target_player, "value", best_hint[0], best_hint[1])
        hand_values = np.array([c.value for c in player_hand])
        if np.sum(hand_values == 2 | hand_values == 3) == 0:  # No 2 or 3
            return None
        if np.sum(hand_values == 2) > np.sum(hand_values == 3):
            return Hint(target_player, "value", 2, np.sum(hand_values == 2))
        return Hint(target_player, "value", 3, np.sum(hand_values == 3))

    def _make_action(self) -> None:
        card_index = self._select_probably_safe(1.0)
        if card_index is not None:
            self._play(card_index)
        card_index = self.hinted_as_playable
        if card_index is not None:
            self._play(card_index)
            self.card_index = None
        card_index = self._select_probably_useless(0.0)
        if card_index is not None:
            self._discard(card_index)
        if self.remaining_hints <= 5:
            card_index = self._select_oldest_unidentified(0.0)
            if card_index is not None:
                self._discard(card_index)
