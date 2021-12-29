from .player import Player
import constants
import GameData
from typing import List


class Possibility:
    def __init__(self) -> None:
        self.color = ["red", "yellow", "green", "blue", "yellow"]
        self.value = [i for i in range(1, 6)]


class Bot(Player):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.players = []
        self.turn_of = ""
        self.possible_hand = [Possibility() for _ in range(5)]
        self.table_cards = []
        self.remaining_tokens = 8

    def _elaborate_hint(self, hint: GameData.ServerHintData) -> None:
        for i in hint.positions:
            if hint.type == "value":
                self.possible_hand[i].value = [hint.value]
            else:
                self.possible_hand[i].color = [hint.value]

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        self.turn_of = infos.currentPlayer
        self.players = infos.players
        self.table_cards = infos.tableCards
        self.remaining_tokens = 8 - infos.usedNoteTokens

    def _process_valid_action(self, action: GameData.ServerActionValid) -> bool:
        self.turn_of = action.player
        return self.turn_of == self.player_name

    def run(self) -> None:
        super().run()
        self._start_game()
        need_info = True
        while True:
            data = self.socket.recv(constants.DATASIZE)
            data = GameData.GameData.deserialize(data)
            # Ready to play
            if type(data) is GameData.ServerPlayerStartRequestAccepted:
                self.status = "Game"
                self.socket.send(
                    GameData.ClientPlayerReadyData(self.player_name).serialize()
                )
            # Playing
            if self.status == "Game":
                if (
                    type(data) is GameData.ServerHintData
                    and data.destination == self.player_name
                ):
                    self._elaborate_hint(data)
                if type(data) is GameData.ServerGameStateData:
                    self._update_infos(data)
                    need_info = False
                if type(data) is GameData.ServerActionValid:
                    need_info = self._process_valid_action(data)
                # Exec bot turn
                if self.turn_of == self.player_name:
                    print("My turn")
                    if need_info:
                        self._get_infos()

    def end(self) -> None:
        super().end()
