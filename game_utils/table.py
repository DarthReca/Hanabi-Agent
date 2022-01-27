import game
from constants import COLORS
from typing import List, Dict, Set, Tuple
from itertools import chain
import numpy as np


class Table:
    """This is the table manager for discard pile and played cards."""

    def __init__(self) -> None:
        self.table_array = np.zeros([5, 5], dtype=np.uint8)
        self.discard_array = np.zeros([5, 5], dtype=np.uint8)

    def set_discard_pile(self, pile: List[game.Card]):
        self.discard_array.fill(0)
        for card in pile:
            self.discard_array[COLORS.index(card.color), card.value - 1] += 1

    def set_table(self, table: Dict[str, List[game.Card]]):
        for card in chain(*table.values()):
            self.table_array[COLORS.index(card.color), card.value - 1] = 1

    def next_playable_cards(self) -> Set[Tuple[str, int]]:
        colors, values = np.nonzero(self.next_playables_mask())
        return {(COLORS[colors[i]], values[i] + 1) for i in range(colors.shape[0])}

    def next_playables_mask(self) -> np.ndarray:
        """Create an array with True if card is currently playable, otherwise False."""
        playables = np.zeros([5, 5], dtype=np.bool8)
        playables[:, np.argmin(self.table_array, axis=1)] = True
        return playables

    def playables_mask(self) -> np.ndarray:
        """Create an array with True if the card was not already played, otherwise False."""
        return self.table_array == 0

    def total_table_card(self) -> np.ndarray:
        """Create an array with the count of the public cards (table + discard pile)."""
        return self.table_array + self.discard_array
