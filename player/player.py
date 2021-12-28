import socket
import threading
from typing import Literal
import GameData, constants
import sys


class Player:
    """
    Player is the base class for different type of game players (bot, human).

    Attributes
    ----------
    host: str
        The ip of the server.
    port: int
        The port of the server.
    player_name: str
        The name associated with this player.

    Methods
    -------
    run()
        Start this entity.
    end()
        Terminate this entity.
    """

    def __init__(self, host: str, port: int, player_name: str) -> None:
        self.status = "Lobby"
        self.player_name = player_name
        # Init socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        # Start connection
        self.socket.send(GameData.ClientPlayerAddData(player_name).serialize())
        data = self.socket.recv(constants.DATASIZE)
        data = GameData.GameData.deserialize(data)
        if type(data) is GameData.ServerPlayerConnectionOk:
            print("Connection accepted by the server. Welcome " + player_name)
        print(f"[{player_name}-{self.status}]: ", end="")

    def _start_game(self):
        self.socket.send(
            GameData.ClientPlayerStartRequest(self.player_name).serialize()
        )

    def _player_ready(self):
        self.socket.send(GameData.ClientPlayerReadyData(self.player_name).serialize())
        self.status = "Game"

    def _get_infos(self):
        self.socket.send(
            GameData.ClientGetGameStateRequest(self.player_name).serialize()
        )

    def _discard(self, card: int):
        self.socket.send(
            GameData.ClientPlayerDiscardCardRequest(self.player_name, card).serialize()
        )

    def _play(self, card: int):
        self.socket.send(
            GameData.ClientPlayerPlayCardRequest(self.player_name, card).serialize()
        )

    def _give_hint(self, player: str, hint_type: Literal["color", "value"], hint):
        self.socket.send(
            GameData.ClientHintData(
                self.player_name, player, hint_type, hint
            ).serialize()
        )

    def _listen(self):
        while True:
            data = self.socket.recv(constants.DATASIZE)
            if not data:
                continue
            data = GameData.GameData.deserialize(data)
            if type(data) is GameData.ServerPlayerStartRequestAccepted:
                dataOk = True
                print(
                    "Ready: "
                    + str(data.acceptedStartRequests)
                    + "/"
                    + str(data.connectedPlayers)
                    + " players"
                )
                data = self.socket.recv(constants.DATASIZE)
                data = GameData.GameData.deserialize(data)
            if type(data) is GameData.ServerStartGameData:
                dataOk = True
                print("Game start!")
                self.socket.send(
                    GameData.ClientPlayerReadyData(self.player_name).serialize()
                )
                self.status = "Game"
            if type(data) is GameData.ServerGameStateData:
                dataOk = True
                print("Current player: " + data.currentPlayer)
                print("Player hands: ")
                for p in data.players:
                    print(p.toClientString())
                print("Table cards: ")
                for pos in data.tableCards:
                    print(pos + ": [ ")
                    for c in data.tableCards[pos]:
                        print(c.toClientString() + " ")
                    print("]")
                print("Discard pile: ")
                for c in data.discardPile:
                    print("\t" + c.toClientString())
                print(f"Note tokens used: {data.usedNoteTokens}/8")
                print(f"Storm tokens used: {data.usedStormTokens}/3")
            if type(data) is GameData.ServerActionInvalid:
                dataOk = True
                print("Invalid action performed. Reason:")
                print(data.message)
            if type(data) is GameData.ServerActionValid:
                dataOk = True
                print("Action valid!")
                print("Current player: " + data.player)
            if type(data) is GameData.ServerPlayerMoveOk:
                dataOk = True
                print("Nice move!")
                print("Current player: " + data.player)
            if type(data) is GameData.ServerPlayerThunderStrike:
                dataOk = True
                print("OH NO! The Gods are unhappy with you!")
            if type(data) is GameData.ServerHintData:
                dataOk = True
                print("Hint type: " + data.type)
                print(
                    "Player "
                    + data.destination
                    + " cards with value "
                    + str(data.value)
                    + " are:"
                )
                for i in data.positions:
                    print("\t" + str(i))
            if type(data) is GameData.ServerInvalidDataReceived:
                dataOk = True
                print(data.data)
            if type(data) is GameData.ServerGameOver:
                dataOk = True
                print(data.message)
                print(data.score)
                print(data.scoreMessage)
                sys.stdout.flush()
                return
            if not dataOk:
                print("Unknown or unimplemented data type: " + str(type(data)))

    def run(self) -> None:
        """Start the threads to manage the game"""
        # Start the server listener
        self.listener = threading.Thread(target=self._listen, daemon=True)
        self.listener.start()

    def end(self) -> None:
        """Terminate all threads and close socket to finish the game"""
        self.socket.close()
