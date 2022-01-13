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
        self.table = np.zeros([5, 5], dtype=np.uint8)
        self.discard_pile = np.zeros([5, 5], dtype=np.uint8)
        self.player_cards = np.zeros([5, 5], dtype=np.uint8)
        self.need_info = False

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        self.turn_of = infos.currentPlayer
        self.remaining_tokens = 8 - infos.usedNoteTokens
        # Update possible cards
        for card in chain(*infos.tableCards.values()):
            self.table[COLORS.index(card.color), card.value - 1] = 1

        self.discard_pile.fill(0)
        for card in chain(*infos.discardPile):
            self.discard_pile[COLORS.index(card.color), card.value - 1] += 1

        self.player_cards.fill(0)
        for card in chain(*[player.hand for player in infos.players]):
            self.player_cards[COLORS.index(card.color), card.value - 1] += 1

    def _process_discard(self, action: GameData.ServerActionValid) -> None:
        self.turn_of = action.player
        self.need_info = True

    def _process_played_card(self, action: GameData.ServerPlayerMoveOk) -> None:
        self.turn_of = action.player
        self.need_info = True

    def _process_error(self, action: GameData.ServerPlayerThunderStrike) -> None:
        self.turn_of = action.player
        self.need_info = True

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
            self.need_info = True
        if type(data) is GameData.ServerActionValid:
            self._process_discard(data)

    def run(self) -> None:
        super().run()
        self._start_game()

    def end(self) -> None:
        super().end()
