from .player import Player
import constants
import GameData
from typing import List, Union, Set, Tuple, Dict, Counter
from itertools import product, chain
import game
import collections

Deck = Counter[Tuple[str, int]]


class Possibility:
    def __init__(self) -> None:
        self.value = set(product(constants.COLORS, [i for i in range(1, 6)]))

    def set_color(self, color: str):
        self.value = set(filter(lambda x: x[0] == color, self.value))

    def set_value(self, value: int):
        self.value = set(filter(lambda x: x[1] == value, self.value))

    def remove_cards(self, cards: Deck):
        self.value &= set((constants.INITIAL_DECK - cards).keys())

    def known(self) -> bool:
        return len(self.value) == 1


class Bot(Player):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.players = []  # type: List[str]
        self.turn_of = ""
        self.possible_hand = [Possibility() for _ in range(5)]
        self.table_cards = []
        self.remaining_tokens = 8

    def _merge_infos_in_deck(self, infos: GameData.ServerGameStateData) -> Deck:
        player_cards = [player.hand for player in infos.players]
        return collections.Counter(
            [
                (x.color, x.value)
                for x in chain(
                    infos.discardPile, *player_cards, *infos.tableCards.values()
                )
            ]
        )

    def _elaborate_hint(self, hint: GameData.ServerHintData) -> None:
        for i in hint.positions:
            if hint.type == "value":
                self.possible_hand[i].set_value(hint.value)
            else:
                self.possible_hand[i].set_color(hint.value)

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        self.turn_of = infos.currentPlayer
        self.players = [x.name for x in infos.players] + [self.player_name]
        self.table_cards = infos.tableCards
        self.remaining_tokens = 8 - infos.usedNoteTokens
        # Update possible cards
        known_cards = self._merge_infos_in_deck(infos)
        for possibility in self.possible_hand:
            possibility.remove_cards(known_cards)

    def _process_valid_action(self, action: GameData.ServerActionValid) -> bool:
        self.turn_of = action.player

    def _pass_turn(self):
        if not self.players:
            return
        next_player = (self.players.index(self.turn_of) + 1) % len(self.players)
        self.turn_of = self.players[next_player]

    def run(self) -> None:
        super().run()
        self._start_game()
        while True:
            data = self.socket.recv(constants.DATASIZE)
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
