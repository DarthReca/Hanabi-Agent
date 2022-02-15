import sys
import threading

import constants
import game_data
from .player import Player


class Human(Player):
    def _listen(self):
        while True:
            # Try receiving data otherwise terminate
            try:
                data = self.socket.recv(constants.DATASIZE)
            except BrokenPipeError:
                return
            # Process data if it is not empty
            if not data:
                continue
            data = game_data.GameData.deserialize(data)
            if type(data) is game_data.ServerPlayerStartRequestAccepted:
                dataOk = True
                print(
                    "Ready: "
                    + str(data.acceptedStartRequests)
                    + "/"
                    + str(data.connectedPlayers)
                    + " players"
                )
                data = self.socket.recv(constants.DATASIZE)
                data = game_data.GameData.deserialize(data)
            if type(data) is game_data.ServerStartGameData:
                dataOk = True
                print("Game start!")
                self.socket.send(
                    game_data.ClientPlayerReadyData(self.player_name).serialize()
                )
                self.status = "Game"
            if type(data) is game_data.ServerGameStateData:
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
            if type(data) is game_data.ServerActionInvalid:
                dataOk = True
                print("Invalid action performed. Reason:")
                print(data.message)
            if type(data) is game_data.ServerActionValid:
                dataOk = True
                print("Action valid!")
                print("Current player: " + data.player)
            if type(data) is game_data.ServerPlayerMoveOk:
                dataOk = True
                print("Nice move!")
                print("Current player: " + data.player)
            if type(data) is game_data.ServerPlayerThunderStrike:
                dataOk = True
                print("OH NO! The Gods are unhappy with you!")
            if type(data) is game_data.ServerHintData:
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
            if type(data) is game_data.ServerInvalidDataReceived:
                dataOk = True
                print(data.data)
            if type(data) is game_data.ServerGameOver:
                dataOk = True
                print(data.message)
                print(data.score)
                print(data.scoreMessage)
                sys.stdout.flush()
                return
            if not dataOk:
                print("Unknown or unimplemented data type: " + str(type(data)))

    def _manage_input(self) -> None:
        while True:
            command = input()
            # Choose data to send
            if command == "exit":
                self._disconnect()
                return
            elif command == "ready" and self.status == "Lobby":
                self._start_game()
            elif command == "show" and self.status == "Game":
                self._get_infos()
            elif command.split(" ")[0] == "discard" and self.status == "Game":
                try:
                    card_str = command.split(" ")
                    self._discard(int(card_str[1]))
                except:
                    print("Maybe you wanted to type 'discard <num>'?")
                    continue
            elif command.split(" ")[0] == "play" and self.status == "Game":
                try:
                    card_str = command.split(" ")
                    self._play(int(card_str[1]))
                except:
                    print("Maybe you wanted to type 'play <num>'?")
                    continue
            elif command.split(" ")[0] == "hint" and self.status == "Game":
                try:
                    destination = command.split(" ")[2]
                    t = command.split(" ")[1].lower()
                    if t != "colour" and t != "color" and t != "value":
                        print("Error: type can be 'color' or 'value'")
                        continue
                    value = command.split(" ")[3].lower()
                    if t == "value":
                        value = int(value)
                        if int(value) > 5 or int(value) < 1:
                            print("Error: card values can range from 1 to 5")
                            continue
                    else:
                        if value not in ["green", "red", "blue", "yellow", "white"]:
                            print(
                                "Error: card color can only be green, red, blue, yellow or white"
                            )
                            continue
                    self._give_hint(destination, t, value)
                except:
                    print(
                        "Maybe you wanted to type 'hint <type> <destinatary> <value>'?"
                    )
                    continue
            elif command == "":
                print("[" + self.player_name + " - " + self.status + "]: ", end="")
            else:
                print("Unknown command: " + command)
                continue
            sys.stdout.flush()

    def run(self) -> None:
        # Start the server listener
        self.listener = threading.Thread(target=self._listen, daemon=True)
        self.listener.start()
        # Start the input manager for user
        self.input_manager = threading.Thread(target=self._manage_input)
        self.input_manager.start()

    def end(self) -> None:
        self.input_manager.join()
        self.listener.join()
        super().end()
