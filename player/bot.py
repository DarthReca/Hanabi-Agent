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


class Table:
    """This is the table manager for discard pile and played cards."""

    def __init__(self) -> None:
        self.table_array = np.zeros([5, 5], dtype=np.uint8)
        self.discard_array = np.zeros([5, 5], dtype=np.uint8)

    def set_discard_pile(self, pile: List[game.Card]):
        self.discard_array.fill(0)
        for card in pile:
            self.discard_array[COLORS.index(card.color), card.value - 1] += 1

    def set_table(self, table: Dict[str, List[game.Card]]):
        for card in chain(*table.values()):
            self.table_array[COLORS.index(card.color), card.value - 1] = 1

    def next_playable_cards(self) -> Set[Tuple[str, int]]:
        colors, values = np.nonzero(self.next_playables_mask())
        return {(COLORS[colors[i]], values[i] + 1) for i in range(colors.shape[0])}

    def next_playables_mask(self) -> np.ndarray:
        """Create an array with True if card is currently playable, otherwise False."""
        playables = np.zeros([5, 5], dtype=np.bool8)
        playables[:, np.argmin(self.table_array, axis=1)] = True
        return playables

    def playables_mask(self) -> np.ndarray:
        """Create an array with True if the card was not already played, otherwise False."""
        return self.table_array == 0

    def total_table_card(self) -> np.ndarray:
        """Create an array with the count of the public cards (table + discard pile)."""
        return self.table_array + self.discard_array


class Bot(Player):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.logger = logging.getLogger(self.player_name)
        self.players = []  # type: List[str]
        self.turn_of = ""
        self.remaining_hints = 8
        self.lives = 3
        self.table = Table()
        self.player_cards = {}  # type: Dict[str, List[game.Card]]
        self.need_info = False
        # Logger
        formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
        handler = logging.FileHandler(f"{self.player_name}.log", "w+")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _next_player(self) -> str:
        next_player_index = (self.players.index(self.player_name) + 1) % len(
            self.players
        )
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
        self.turn_of = infos.currentPlayer
        self.remaining_hints = 8 - infos.usedNoteTokens
        self.lives = 3 - infos.usedStormTokens
        # Update possible cards
        for player in infos.players:
            self.player_cards[player.name] = player.hand

        self.table.set_table(infos.tableCards)
        self.table.set_discard_pile(infos.discardPile)

    def _process_discard(self, action: GameData.ServerActionValid) -> None:
        self.logger.info(f"{action.lastPlayer} discarded")
        self.turn_of = action.player
        self.need_info = True

    def _process_played_card(self, action: GameData.ServerPlayerMoveOk) -> None:
        self.logger.info(f"{action.lastPlayer} played")
        self.turn_of = action.player
        self.need_info = True

    def _process_error(self, action: GameData.ServerPlayerThunderStrike) -> None:
        self.turn_of = action.player
        self.need_info = True

    def _process_game_start(self, action: GameData.ServerStartGameData) -> None:
        self.status = "Game"
        self.players = action.players
        self.turn_of = self.players[0]
        self.need_info = True

        self.logger.info(
            f"Starting game with {len(action.players)}. Turn of {self.turn_of}"
        )

    def _pass_turn(self):
        if not self.players:
            return
        next_player = (self.players.index(self.turn_of) + 1) % len(self.players)
        self.turn_of = self.players[next_player]

    def _process_game_over(self, data: GameData.ServerGameOver):
        self.logger.info("Score: " + data.score)
        self._disconnect()

    def _process_invalid(self, data: GameData.ServerActionInvalid):
        self.logger.error(data.message)

    def run(self) -> None:
        super().run()
        self._start_game()

    def end(self) -> None:
        super().end()
