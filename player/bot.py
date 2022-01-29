from asyncio.log import logger
from logging import handlers
import game
from .player import Player
from constants import COLORS
import GameData
from typing import List, Dict, Set, Tuple
from itertools import chain
import numpy as np
import logging
from game_utils import Table
import os


class Bot(Player):
    def __init__(
        self, host: str, port: int, player_name: str, games_to_play: int = 1
    ) -> None:
        super().__init__(host, port, player_name)
        self.logger = logging.getLogger(self.player_name)
        self.players = []  # type: List[str]
        self.turn_of = ""
        self.remaining_hints = 8
        self.lives = 3
        self.table = Table()
        self.player_cards = {}  # type: Dict[str, List[game.Card]]
        self.need_info = False
        self.games_to_play = games_to_play
        # Logger
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        handler = logging.FileHandler(f"{self.player_name}.log", "w+")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)

    def _next_player(self, player_name: str) -> str:
        next_player_index = (self.players.index(player_name) + 1) % len(self.players)
        return self.players[next_player_index]

    def _cards_to_ndarray(self, *cards: game.Card):
        """Create an array that count the occurences of each card type."""
        ndarray = np.zeros([5, 5], dtype=np.uint8)
        for card in cards:
            ndarray[COLORS.index(card.color), card.value - 1] += 1
        return ndarray

    def _count_cards_in_hands(self) -> np.ndarray:
        """Create an array that count the occurences of each card type in player hands."""
        total = np.zeros([5, 5], dtype=np.uint8)
        for hand in self.player_cards.values():
            total += self._cards_to_ndarray(*hand)
        return total

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        self.remaining_hints = 8 - infos.usedNoteTokens
        self.lives = 3 - infos.usedStormTokens
        # Update possible cards
        for player in infos.players:
            self.player_cards[player.name] = player.hand

        self.table.set_table(infos.tableCards)
        self.table.set_discard_pile(infos.discardPile)

    def _process_discard(self, action: GameData.ServerActionValid) -> None:
        self.turn_of = action.player
        self.need_info = True

    def _process_played_card(self, action: GameData.ServerPlayerMoveOk) -> None:
        self.turn_of = action.player
        self.need_info = True

    def _process_error(self, action: GameData.ServerPlayerThunderStrike) -> None:
        self.logger.warning("Mistake")
        self.turn_of = action.player
        self.need_info = True

    def _process_game_start(self, action: GameData.ServerStartGameData) -> None:
        self._player_ready()
        self.status = "Game"
        self.players = action.players
        self.turn_of = self.players[0]
        self.need_info = True

        self.logger.info(
            f"Starting game with {len(action.players)}. Turn of {self.turn_of}"
        )

    def _process_game_over(self, data: GameData.ServerGameOver):
        self.logger.info(f"Score: {data.score}")
        self.games_to_play -= 1
        self.logger.info(f"Remaining games to play: {self.games_to_play}")
        if self.games_to_play == 0:
            self._disconnect()
            os._exit(0)
        self.turn_of = self.players[0]
        self.remaining_hints = 8
        self.lives = 3
        self.table = Table()
        for k in self.player_cards:
            self.player_cards[k].clear()
        self.need_info = True

    def _process_invalid(self, data: GameData.ServerActionInvalid):
        self.logger.error(data.message)

    def run(self) -> None:
        super().run()
        self._start_game()

    def end(self) -> None:
        super().end()
