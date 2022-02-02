from game_utils.mutator import Mutator
from .poirot import Poirot, Hint
import numpy as np
from typing import Optional


class CanaanBot(Poirot):
    """
    Reference: https://arxiv.org/pdf/1809.09764.pdf
    """

    def __init__(
        self,
        host: str,
        port: int,
        player_name: str,
        games_to_play: int = 1,
        evolve: bool = False,
    ) -> None:
        super().__init__(host, port, player_name, games_to_play)
        # These are defaults
        self.parameters = {"safeness": 0.6, "usability": 0.4, "knowledge": 0.0}
        self.load_parameters("params/canaan_params.json")
        self.mutator = Mutator(0.2, len(self.parameters))
        self.mutator.activate(evolve)

    def _select_oldest_unidentified(
        self, max_knowledge: int, target_player: Optional[str] = None
    ) -> Optional[int]:
        target_player = self.player_name if target_player is None else target_player
        hand = self.players_knowledge[target_player]
        possibilities = np.array(
            [len(card.possible_colors()) * len(card.possible_values()) for card in hand]
        )
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
                self.logger.info(f"Playing {current_knol[card_index]}")
                self._play(card_index)
                return
        hint = self._select_helpful_hint()
        if hint is not None and self.remaining_hints > 0:
            self.logger.info(f"Giving hint {repr(hint)}")
            self._give_hint(hint.to, hint.type, hint.value)
            return
        card_index = self._select_probably_safe(1.0)
        if card_index is not None:
            self.logger.info(f"Playing {current_knol[card_index]}")
            self._play(card_index)
            return
        if self.remaining_hints < 8:
            card_index = self._select_probably_useless(self.parameters["usability"])
            if card_index is not None:
                self.logger.info(f"Discarding {current_knol[card_index]}")
                self._discard(card_index)
                return
            card_index = self._select_oldest_unidentified(self.parameters["knowledge"])
            if card_index is not None:
                self.logger.info(f"Discarding {current_knol[card_index]}")
                self._discard(card_index)
                return
            card_index = self._select_oldest_unidentified(1.0)
            self.logger.info(f"Discarding {current_knol[card_index]}")
            self._discard(card_index)
        else:
            next_player = self._next_player(self.player_name)
            card_index = self._select_oldest_unidentified(1.0, next_player)
            card_knol = self.players_knowledge[next_player][card_index]
            card = self.player_cards[next_player][card_index]
            hint = Hint(next_player, "color", card.color, 1)
            if len(card_knol.possible_colors()) < len(card_knol.possible_values()):
                hint.type = "value"
                hint.value = card.value
            self.logger.info(f"Giving hint {repr(hint)}")
            self._give_hint(hint.to, hint.type, hint.value)
