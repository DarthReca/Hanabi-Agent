from game_utils import Mutator, Table
from .poirot import Poirot, Hint
import numpy as np
from typing import Optional
from constants import COLORS


class CanaanBot(Poirot):
    """
    CanaanBot is a rule-based bot using the "old" rules of Canaan paper[1].

    References
    ----------
    [1] https://arxiv.org/pdf/1809.09764.pdf

    """

    def __init__(
        self,
        host: str,
        port: int,
        player_name: str,
        games_to_play: int = 1,
        parameters_file: Optional[str] = None,
        evolve: bool = False,
    ) -> None:
        super().__init__(host, port, player_name, games_to_play)
        self.load_parameters(parameters_file)
        self.mutator = Mutator(0.2, len(self.parameters))
        self.mutator.activate(evolve)

    def _select_disposable_hint(self, target_player: str) -> Optional[Hint]:
        """Select an hint to advice about useless cards of `target_player`."""
        hand = self.player_cards[target_player]
        disposable = np.array(
            [
                self.table.table_array[COLORS.index(card.color), card.value - 1] == 1
                for card in hand
            ]
        )
        knowledge = self.players_knowledge[target_player]
        known_disposable = np.array(
            [
                np.sum(self.table.table_array | knowl.can_be)
                <= np.sum(self.table.table_array)
                for knowl in knowledge
            ]
        )
        # Select only unknown
        values = np.array([card.value for card in hand])
        hints = values[disposable & np.logical_not(known_disposable)]
        if hints.shape[0] == 0:
            return None
        # Select only non-misinformative hint
        stats = []
        for h in hints:
            cards_with_value = values == h
            # Colors of cards of value h that were not played
            colors_to_exclude = np.flatnonzero(self.table.table_array[:, h - 1] == 0)
            informativity = np.sum(cards_with_value)
            disinformativity = np.sum(cards_with_value & np.logical_not(disposable))
            if colors_to_exclude.shape[0] != 0:
                # It is disinformative selecting a card that can be still playable
                disinformativity += sum(
                    [
                        np.sum(knowledge[i].can_be[colors_to_exclude])
                        for i in np.flatnonzero(cards_with_value)
                    ]
                )
            if disinformativity == 0:
                stats.append((h, informativity))
        if len(stats) == 0:
            return None
        most_informative = max(stats, key=lambda x: x[1])
        self.logger.debug(f"Giving disposable hint")
        return Hint(target_player, "value", most_informative[0], most_informative[1])

    def _select_oldest_unidentified(
        self, max_knowledge: float, target_player: Optional[str] = None
    ) -> Optional[int]:
        """Select the most unidentified card in hand of `target_player` with knowledge <= `max_knowledge`."""
        target_player = self.player_name if target_player is None else target_player
        player_knowledge = self.players_knowledge[target_player]
        possibilities = np.array([np.sum(knol.can_be) for knol in player_knowledge])
        # The knowledge (0..1) is higher if the possibilities are less
        knowledge = 1 - possibilities / 25
        less_known = np.argmin(knowledge)
        if knowledge[less_known] <= max_knowledge:
            return less_known
        return None

    def _make_action(self) -> None:
        cards = {
            k: [(c.color, c.value) for c in v] for k, v in self.player_cards.items()
        }
        self.logger.debug(repr(cards))
        current_knol = self.players_knowledge[self.player_name]
        if self.lives > 1:
            card_index = self._select_probably_safe(self.parameters["safeness"])
            if card_index is not None:
                self.logger.info(f"Playing {card_index}: {current_knol[card_index]}")
                self._play(card_index)
                return
        hint = self._select_helpful_hint()
        if hint is not None and self.remaining_hints > 0:
            self.logger.info(f"Giving hint {repr(hint)}")
            self._give_hint(hint.to, hint.type, hint.value)
            return
        card_index = self._select_probably_safe(1.0)
        if card_index is not None:
            self.logger.info(f"Playing {card_index}: {current_knol[card_index]}")
            self._play(card_index)
            return

        if self.remaining_hints < 8:
            card_index = self._select_probably_useless(self.parameters["usability"])
            if card_index is not None:
                self.logger.info(f"Discarding {card_index}: {current_knol[card_index]}")
                self._discard(card_index)
                return
            card_index = self._select_oldest_unidentified(self.parameters["knowledge"])
            if card_index is not None:
                self.logger.info(f"Discarding {card_index}: {current_knol[card_index]}")
                self._discard(card_index)
                return
            card_index = self._select_oldest_unidentified(1.0)
            self.logger.info(f"Discarding {card_index}: {current_knol[card_index]}")
            self._discard(card_index)
        else:
            next_player = self._next_player(self.player_name)
            hint = self._select_disposable_hint(next_player)
            if hint is not None:
                self.logger.info(f"Giving hint {repr(hint)}")
                self._give_hint(hint.to, hint.type, hint.value)
                return
            card_index = self._select_oldest_unidentified(1.0, next_player)
            card_knol = self.players_knowledge[next_player][card_index]
            card = self.player_cards[next_player][card_index]
            hint = Hint(next_player, "color", card.color, 1)
            if len(card_knol.possible_colors()) < len(card_knol.possible_values()):
                hint = Hint(next_player, "value", card.value, 1)
            self.logger.info(f"Giving hint {repr(hint)}")
            self._give_hint(hint.to, hint.type, hint.value)
