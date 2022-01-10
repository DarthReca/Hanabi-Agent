from .player import Player
from constants import COLORS, INITIAL_DECK, DATASIZE
import GameData
from typing import List, Optional, Union, Set, Tuple, Dict, Counter
from itertools import product, chain
import game
import numpy as np

Deck = Counter[Tuple[str, int]]


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

    def known(self) -> bool:
        return self.color != "" and self.value != -1

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


class Bot(Player):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.players = []  # type: List[str]
        self.turn_of = ""
        self.possible_hand = [CardKnowledge() for _ in range(5)]
        self.remaining_tokens = 8
        self.known_cards = np.zeros([5, 5], dtype=np.uint8)

    def _merge_infos_in_deck(self, infos: GameData.ServerGameStateData) -> np.ndarray:
        player_cards = [player.hand for player in infos.players]
        deck = np.zeros([5, 5], dtype=np.uint8)
        for x in chain(infos.discardPile, *player_cards, *infos.tableCards.values()):
            deck[COLORS.index(x.color), x.value - 1] += 1
        return deck

    def _elaborate_hint(self, hint: GameData.ServerHintData) -> None:
        for i in hint.positions:
            if hint.type == "value":
                self.possible_hand[i].set_value(hint.value)
            else:
                self.possible_hand[i].set_color(hint.value)

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        self.turn_of = infos.currentPlayer
        # self.players = [x.name for x in infos.players] + [self.player_name]
        self.remaining_tokens = 8 - infos.usedNoteTokens
        # Update possible cards
        self.known_cards = self._merge_infos_in_deck(infos)
        for possibility in self.possible_hand:
            possibility.remove_cards(self.known_cards)

    def _process_valid_action(self, action: GameData.ServerActionValid) -> bool:
        self.turn_of = action.player

    def _pass_turn(self):
        if not self.players:
            return
        next_player = (self.players.index(self.turn_of) + 1) % len(self.players)
        self.turn_of = self.players[next_player]

    def _delete_knowledge(self, index: int):
        self.possible_hand.pop(index)
        self.possible_hand.insert(0, CardKnowledge())

    def _is_valuable(self, color: str, value: int) -> bool:
        """It is valuable if it is the only remaining card"""
        return (INITIAL_DECK - self.known_cards)[COLORS.index(color), value] == 0

    def _could_be_valuable(self, knowledge: CardKnowledge, value: int) -> bool:
        """Test if a unknown card can be a valuable one"""
        for color in COLORS:
            if knowledge.can_be(color, value) and self._is_valuable(color, value):
                return True
        return False

    def run(self) -> None:
        super().run()
        self._start_game()
        while True:
            data = self.socket.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
            # Ready to play
            if type(data) is GameData.ServerPlayerStartRequestAccepted:
                self.status = "Game"
                self.socket.send(
                    GameData.ClientPlayerReadyData(self.player_name).serialize()
                )
                continue
            # Playing
            if self.status == "Game":
                if type(data) is GameData.ServerStartGameData:
                    self.players = data.players
                    self.turn_of = self.players[0]
                if type(data) is GameData.ServerHintData:
                    if data.destination == self.player_name:
                        self._elaborate_hint(data)
                    # Pass turn
                    self._pass_turn()
                if type(data) is GameData.ServerGameStateData:
                    self._update_infos(data)
                if type(data) is GameData.ServerActionValid:
                    self._process_valid_action(data)
                # Exec bot turn
                if self.turn_of == self.player_name:
                    print("My turn")

    def end(self) -> None:
        super().end()
