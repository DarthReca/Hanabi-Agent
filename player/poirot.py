from .bot import Bot, Table
import numpy as np
from constants import COLORS, INITIAL_DECK, DATASIZE
from typing import Optional, Tuple, Dict, List
import GameData
from itertools import product
from game import Card


class CardKnowledge:
    def __init__(self) -> None:
        # Rows are colors, Columns are (values - 1)
        self.canbe = np.ones([5, 5], dtype=np.bool8)

    def possible_values(self) -> np.ndarray:
        return np.nonzero(self.can_be == True)[1] + 1

    def possible_colors(self) -> List[str]:
        return [COLORS[c] for c in np.nonzero(self.can_be == True)[0]]

    def set_suggested_color(self, color: str):
        index = COLORS.index(color)
        mask = np.zeros([5, 5], dtype=np.bool8)
        mask[index] = True
        self.canbe &= mask

    def set_suggested_value(self, value: int):
        index = value - 1
        mask = np.zeros([5, 5], dtype=np.bool8)
        mask[:, index] = True
        self.canbe &= mask

    def remove_cards(self, cards: np.ndarray):
        self.canbe &= INITIAL_DECK - cards != 0

    def can_be(self, color: Optional[str], value: Optional[int]) -> bool:
        if color is None and value is None:
            return True
        color_index = np.arange(5)
        value_index = np.arange(5)
        if not color is None:
            color_index = COLORS.index(color)
        if not value is None:
            value_index = value - 1
        return np.any(self.canbe[color_index, value_index])

    def preciousness(self, table: Table, players_cards: np.ndarray) -> float:
        """Probability the card could be a valuable one (it could be the only card of this type)"""
        valuables = (
            INITIAL_DECK - table.discard_array - players_cards - table.table_array == 1
        )
        return np.sum(self.canbe & valuables & table.playables_mask()) / np.sum(
            self.canbe
        )

    def playability(self, table: Table) -> float:
        """Probability the card is currently playable"""
        return np.sum(self.can_be & table.next_playables_mask()) / np.sum(self.can_be)

    def usability(self, table: Table) -> float:
        """Probability the card can still be played"""
        return np.sum(self.can_be & table.playables_mask()) / np.sum(self.can_be)


class Poirot(Bot):
    def __init__(self, host: str, port: int, player_name: str) -> None:
        super().__init__(host, port, player_name)
        self.players_knowledge = {self.player_name: [CardKnowledge() for _ in range(5)]}

    def _process_game_start(self, action: GameData.ServerStartGameData) -> None:
        super()._process_game_start(action)
        # For each player create his knowledge
        for player in self.players:
            self.players_knowledge[player] = [CardKnowledge() for _ in range(5)]

    def _elaborate_hint(self, hint: GameData.ServerHintData) -> None:
        self.turn_of = hint.player
        self.need_info = True
        for i in hint.positions:
            if hint.type == "value":
                self.players_knowledge[hint.destination][i].set_suggested_value(
                    hint.value
                )
            else:
                self.players_knowledge[hint.destination][i].set_suggested_color(
                    hint.value
                )

    def _process_discard(self, action: GameData.ServerActionValid) -> None:
        super()._process_discard(action)
        self._delete_knowledge(action.lastPlayer, action.cardHandIndex)

    def _process_played_card(self, action: GameData.ServerPlayerMoveOk) -> None:
        super()._process_played_card(action)
        self._delete_knowledge(action.lastPlayer, action.cardHandIndex)

    def _process_error(self, action: GameData.ServerPlayerThunderStrike) -> None:
        super()._process_error(action)
        self._delete_knowledge(action.lastPlayer, action.cardHandIndex)

    def _update_infos(self, infos: GameData.ServerGameStateData) -> None:
        super()._update_infos(infos)
        for possibility in self.players_knowledge[self.player_name]:
            possibility.remove_cards(
                self._count_cards_in_hands() + self.table.total_table_card()
            )

    def _delete_knowledge(self, player_name: str, index: int):
        self.players_knowledge[player_name].pop(index)
        self.players_knowledge[player_name].append(CardKnowledge())

    def _maybe_play_lowest_value(self) -> bool:
        """Play a card we are sure can be played with the lowest value possible"""
        playables = [
            x
            for x in self.players_knowledge[self.player_name]
            if x.playability(self.table) == 1
        ]
        if len(playables) == 0:
            return False
        knowledge = min(
            playables,
            key=lambda x: np.min(x.possible_values()),
        )
        card_index = self.players_knowledge[self.player_name].index(knowledge)
        self._play(card_index)
        self._delete_knowledge(card_index)
        return True

    def _maybe_discard_useless(self) -> bool:
        """Discard the oldest card we are sure is not usable anymore"""
        discardable = [
            x
            for x in self.players_knowledge[self.player_name]
            if x.usability(self.table) == 0
        ]
        if len(discardable) == 0:
            return False
        # Discard oldest
        card_index = self.players_knowledge[self.player_name].index(discardable[0])
        self._discard(card_index)
        self._delete_knowledge(card_index)
        return True

    def _next_discard_index(self, player_name: str) -> Optional[int]:
        """Select the next card to discard if there is no sure card to play or discard"""
        unknown_discardable = []
        for knowledge in self.players_knowledge[player_name]:
            if (
                knowledge.playability(self.table) == 1
                or knowledge.usability(self.table) == 0
            ):
                return None
            elif knowledge.preciousness(self.table, self._count_cards_in_hands()) == 0:
                unknown_discardable.append(knowledge)
        if len(unknown_discardable) == 0:
            return None
        return self.players_knowledge[self.player_name].index(unknown_discardable[0])

    def _best_hint_for(self, player_name: str, table: Table):
        really_playables = (
            self.player_cards[player_name] > 0
        ) & table.next_playables_mask()
        # Try give color hint

    def run(self) -> None:
        super().run()
        while True:
            data = self.socket.recv(DATASIZE)
            data = GameData.GameData.deserialize(data)
            # Process infos
            if type(data) is GameData.ServerPlayerStartRequestAccepted:
                self._process_start_request(data)
            if type(data) is GameData.ServerStartGameData:
                self._process_game_start(data)
            if type(data) is GameData.ServerActionValid:
                self._process_discard(data)
            if type(data) is GameData.ServerHintData:
                self._elaborate_hint(data)
            if type(data) is GameData.ServerGameStateData:
                self._update_infos(data)
            # Exec bot turn
            if self.turn_of == self.player_name:
                print("My turn")
                if self.need_info:
                    self._get_infos()
                    self.need_info = False
