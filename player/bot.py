from .player import Player
from constants import COLORS, INITIAL_DECK, DATASIZE
import GameData
from typing import List
from itertools import chain
import numpy as np


class Bot(Player):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.players = []  # type: List[str]
        self.turn_of = ""
        self.remaining_tokens = 8
        self.known_cards = np.zeros([5, 5], dtype=np.uint8)

    def _merge_infos_in_deck(self, infos: GameData.ServerGameStateData) -> np.ndarray:
        player_cards = [player.hand for player in infos.players]
        deck = np.zeros([5, 5], dtype=np.uint8)
        for x in chain(infos.discardPile, *player_cards, *infos.tableCards.values()):
            deck[COLORS.index(x.color), x.value - 1] += 1
        return deck

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        self.turn_of = infos.currentPlayer
        self.remaining_tokens = 8 - infos.usedNoteTokens
        # Update possible cards
        self.known_cards = self._merge_infos_in_deck(infos)

    def _process_valid_action(self, action: GameData.ServerActionValid) -> None:
        self.turn_of = action.player

    def _pass_turn(self):
        if not self.players:
            return
        next_player = (self.players.index(self.turn_of) + 1) % len(self.players)
        self.turn_of = self.players[next_player]

    def _process_standard_responses(self, data):
        if type(data) is GameData.ServerPlayerStartRequestAccepted:
            self.status = "Game"
            self.socket.send(
                GameData.ClientPlayerReadyData(self.player_name).serialize()
            )
        if type(data) is GameData.ServerStartGameData:
            self.players = data.players
            self.turn_of = self.players[0]
        if type(data) is GameData.ServerActionValid:
            self._process_valid_action(data)

    def run(self) -> None:
        super().run()
        self._start_game()

    def end(self) -> None:
        super().end()
