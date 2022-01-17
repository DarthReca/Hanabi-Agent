import game
from .player import Player
from constants import COLORS, INITIAL_DECK, DATASIZE
import GameData
from typing import List, Dict, Set, Tuple
from itertools import chain
import numpy as np


class Table:
    """This is the table manager for discard pile and played cards."""

    def __init__(self) -> None:
        self.table_array = np.zeros([5, 5], dtype=np.uint8)
        self.discard_array = np.zeros([5, 5], dtype=np.uint8)

    def set_discard_pile(self, pile: List[game.Card]):
        self.discard_array.fill(0)
        for card in chain(*pile):
            self.discard_pile[COLORS.index(card.color), card.value - 1] += 1

    def set_table(self, table: Dict[str, List[game.Card]]):
        for card in chain(*table.values()):
            self.table[COLORS.index(card.color), card.value - 1] = 1

    def next_playable_cards(self) -> Set[Tuple[str, int]]:
        colors, values = np.nonzero(self.next_playable_mask())
        return {(COLORS[colors[i]], values[i] + 1) for i in colors.shape[0]}

    def next_playables_mask(self) -> np.ndarray:
        """Create an array with True if card is currently playable, otherwise False."""
        playables = np.zeros([5, 5], dtype=np.bool8)
        playables[np.argmin(self.table_array, axis=1)] = True
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
        self.players = []  # type: List[str]
        self.turn_of = ""
        self.remaining_hints = 8
        self.table = Table()
        self.player_cards = {}  # type: Dict[str, List[game.Card]]
        self.need_info = False

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
        self.turn_of = action.player
        self.need_info = True

    def _process_game_start(self, action: GameData.ServerStartGameData) -> None:
        self.players = action.players
        self.turn_of = self.players[0]
        self.need_info = True

    def _pass_turn(self):
        if not self.players:
            return
        next_player = (self.players.index(self.turn_of) + 1) % len(self.players)
        self.turn_of = self.players[next_player]

    def _process_start_request(self, data):
        self.status = "Game"
        self.socket.send(GameData.ClientPlayerReadyData(self.player_name).serialize())

    def run(self) -> None:
        super().run()
        self._start_game()

    def end(self) -> None:
        super().end()
