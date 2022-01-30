from constants import COLORS
import numpy as np
from typing import Literal, Optional, Tuple, Dict, List, Set
from game_utils import Table
from constants import INITIAL_DECK


class CardKnowledge:
    def __init__(self) -> None:
        # Rows are colors, Columns are (values - 1)
        self.canbe = np.ones([5, 5], dtype=np.bool8)

    def possible_values(self) -> Set[int]:
        return {i + 1 for i in np.nonzero(self.canbe == True)[1]}

    def possible_colors(self) -> Set[str]:
        return {COLORS[c] for c in np.nonzero(self.canbe == True)[0]}

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
        return np.sum(self.canbe & table.next_playables_mask()) / np.sum(self.canbe)

    def usability(self, table: Table) -> float:
        """Probability the card can still be played"""
        return np.sum(self.canbe & table.playables_mask()) / np.sum(self.canbe)

    def is_known(self) -> bool:
        return len(self.possible_colors()) == 1 and len(self.possible_values()) == 1

    def __repr__(self) -> str:
        return f"Colors: {self.possible_colors()} | Values: {self.possible_values()}"

    def __str__(self) -> str:
        return f"Colors: {self.possible_colors()} | Values: {self.possible_values()}"
