from .player import Player
import sys
import threading


class Human(Player):
    def _manage_input(self) -> None:
        while True:
            command = input()
            # Choose data to send
            if command == "exit":
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
        super().run()
        # Start the input manager for user
        self.input_manager = threading.Thread(target=self._manage_input)
        self.input_manager.start()

    def end(self) -> None:
        self.input_manager.join()
        super().end()
