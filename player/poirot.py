from .bot import Bot
import numpy as np
from constants import COLORS, INITIAL_DECK, DATASIZE
from typing import Optional, Tuple
import GameData
from itertools import product


class CardKnowledge:
    def __init__(self) -> None:
        # Rows are colors, Columns are (values - 1)
        self.canbe = np.ones([5, 5], dtype=np.bool8)

    def set_color(self, color: str):
        index = COLORS.index(color)
        mask = np.zeros([5, 5], dtype=np.bool8)
        mask[index] = True
        self.canbe &= mask

    def set_value(self, value: int):
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

    def valuableness(self, known_cards: np.ndarray) -> float:
        """Probability the card could be a valuable one (it could be the only card of this type) over all its possible values"""
        colors, values = self.valuable_cards(known_cards)
        valuables = np.zeros([5, 5], dtype=np.bool8)
        valuables[colors, values] = True
        return np.sum(self.canbe & valuables) / np.sum(self.canbe)

    def valuable_cards(self, known_cards: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        return np.nonzero(INITIAL_DECK - known_cards == 1)

    def could_be_playable(self) -> bool:
        pass


class Poirot(Bot):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.possible_hand = [CardKnowledge() for _ in range(5)]

    def _elaborate_hint(self, hint: GameData.ServerHintData) -> None:
        for i in hint.positions:
            if hint.type == "value":
                self.possible_hand[i].set_value(hint.value)
            else:
                self.possible_hand[i].set_color(hint.value)

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        super()._update_infos(infos)
        for possibility in self.possible_hand:
            possibility.remove_cards(self.known_cards)

    def _delete_knowledge(self, index: int):
        self.possible_hand.pop(index)
        self.possible_hand.insert(0, CardKnowledge())

    def run(self) -> None:
        super().run()
        while True:
            data = self.socket.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
            # Process some common responses
            self._process_standard_responses(data)
            # Playing
            if type(data) is GameData.ServerHintData:
                if data.destination == self.player_name:
                    self._elaborate_hint(data)
                # Pass turn
                self._pass_turn()
            if type(data) is GameData.ServerGameStateData:
                self._update_infos(data)
            # Exec bot turn
            if self.turn_of == self.player_name:
                print("My turn")
                self._get_infos()
