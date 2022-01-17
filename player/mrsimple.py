from .bot import Bot, Table
import numpy as np
from constants import COLORS, INITIAL_DECK, DATASIZE
from typing import Optional, Tuple, Dict, List
import GameData
from itertools import product
from game import Card

class CardKnowledge:
    def __init__(self) -> None:
        # Rows are colors, Columns are (values - 1)
        self.canbe = np.ones([5, 5], dtype=np.bool8)

    def possible_values(self) -> np.ndarray:
        return np.nonzero(self.can_be == True)[1] + 1

    def possible_colors(self) -> List[str]:
        return [COLORS[c] for c in np.nonzero(self.can_be == True)[0]]

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
        valuables = (
            INITIAL_DECK - table.discard_array - players_cards - table.table_array == 1
        )
        return np.sum(self.canbe & valuables & table.playables_mask()) / np.sum(
            self.canbe
        )

    def playability(self, table: Table) -> float:
        """Probability the card is currently playable"""
        return np.sum(self.can_be & table.next_playables_mask()) / np.sum(self.can_be)

    def usability(self, table: Table) -> float:
        """Probability the card can still be played"""
        return np.sum(self.can_be & table.playables_mask()) / np.sum(self.can_be)

class MrSimple(Bot):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.players_knowledge = {self.player_name: [CardKnowledge() for _ in range(5)]}