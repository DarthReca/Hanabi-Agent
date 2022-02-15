from typing import Set

import numpy as np

from constants import COLORS, INITIAL_DECK
from game_utils import Table


class CardKnowledge:
    def __init__(self) -> None:
        # Rows are colors, Columns are (values - 1)
        self.can_be = np.ones([5, 5], dtype=np.bool8)

    def possible_values(self) -> Set[int]:
        return {i + 1 for i in np.nonzero(self.can_be == True)[1]}

    def possible_colors(self) -> Set[str]:
        return {COLORS[c] for c in np.nonzero(self.can_be == True)[0]}

    def set_suggested_color(self, color: str):
        index = COLORS.index(color)
        mask = np.zeros([5, 5], dtype=np.bool8)
        mask[index] = True
        self.can_be &= mask

    def set_suggested_value(self, value: int):
        index = value - 1
        mask = np.zeros([5, 5], dtype=np.bool8)
        mask[:, index] = True
        self.can_be &= mask

    def remove_cards(self, cards: np.ndarray):
        self.can_be &= INITIAL_DECK - cards != 0

    def preciousness(self, table: Table) -> float:
        """Probability the card could be a valuable one (it could be the only card of this type)"""
        valuables = INITIAL_DECK - table.total_table_card() == 1  # - players_cards
        return np.sum(self.can_be & valuables & table.playables_mask()) / np.sum(
            self.can_be
        )

    def playability(self, table: Table) -> float:
        """Probability the card is currently playable"""
        return np.sum(self.can_be & table.next_playables_mask()) / np.sum(self.can_be)

    def usability(self, table: Table) -> float:
        """Probability the card can still be played"""
        return np.sum(self.can_be & table.playables_mask()) / np.sum(self.can_be)

    def is_known(self) -> bool:
        return len(self.possible_colors()) == 1 and len(self.possible_values()) == 1

    def __repr__(self) -> str:
        return f"Colors: {self.possible_colors()} | Values: {self.possible_values()}"

    def __str__(self) -> str:
        return f"Colors: {self.possible_colors()} | Values: {self.possible_values()}"
