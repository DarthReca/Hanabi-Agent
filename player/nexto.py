from copy import deepcopy
from typing import Dict, List, Optional, Tuple

from game_utils.card_knowledge import CardKnowledge
from game_utils.mutator import Mutator

from .poirot import Hint
from .canaan_bot import CanaanBot
import numpy as np
from scipy.special import softmax


class Nexto(CanaanBot):
    def _next_actions(self) -> Dict[str, np.ndarray]:
        return {
            player: self._simulate_action(self.players_knowledge[player])
            for player in self.players
            if player != self.player_name
        }

    def _simulate_action(self, knowledge: List[CardKnowledge]) -> np.ndarray:
        stats = np.array(
            [
                [
                    k.playability(self.table),
                    k.usability(self.table),
                    k.preciousness(self.table),
                ]
                for k in knowledge
            ]
        )
        probable_played = np.argmax(stats[:, 0])
        probable_discarded = np.argmin(np.sum(stats[:, 1:2], axis=1))
        weights = np.array(
            [
                stats[probable_played, 0],
                self.parameters["hint_probability"],
                1 - stats[probable_discarded, 1],
            ]
        )
        if self.remaining_hints == 8:
            weights[2] = 0
        if self.remaining_hints == 0:
            weights[1] = 0
        weights = softmax(weights)
        return np.array(
            [
                (weights[0], probable_played),
                (weights[1], 0),
                (weights[2], probable_discarded),
            ]
        )

    def _simulate_hint(self, target_player: str, hint: Hint) -> Tuple[int, np.ndarray]:
        new_knowledge = deepcopy(self.players_knowledge[target_player])
        hand = self.player_cards[target_player]
        for i, card in enumerate(hand):
            if hint.type == "color" and card.color == hint.value:
                new_knowledge[i].set_suggested_color(hint.value)
            elif hint.type == "value" and card.value == hint.value:
                new_knowledge[i].set_suggested_value(hint.value)
        new_actions = self._simulate_action(new_knowledge)
        selected_action = np.argmax(new_actions[:, 0])
        return selected_action, new_actions[selected_action]

    def _evaluate_playing(self, player: str, card_index: int) -> Optional[Hint]:
        hand = self.player_cards[player]
        card = hand[card_index]
        knowledge = self.players_knowledge[player][card_index]
        if (card.color, card.value) not in self.table.next_playable_cards():
            if len(knowledge.possible_values()) != 1:
                return Hint(player, "value", card.value, 1)
            if len(knowledge.possible_colors()) != 1:
                return Hint(player, "color", card.color, 1)
        return None

    def _evaluate_discarding(self, player: str, card_index: int):
        hand = self.player_cards[player]
        card = hand[card_index]
        knowledge = self.players_knowledge[player][card_index]
        possible_hints = []
        if (card.color, card.value) in self.table.next_playable_cards().union(
            self.table.precious_cards()
        ):
            if len(knowledge.possible_values()) != 1:
                possible_hints.append(Hint(player, "value", card.value, 1))
            if len(knowledge.possible_colors()) != 1:
                possible_hints.append(Hint(player, "color", card.color, 1))
        for hint in possible_hints:
            new_action, stats = self._simulate_hint(player, hint)
            if new_action != 2 or int(stats[1]) != card_index:
                return hint
        return None

    def _make_action(self) -> None:
        next_actions = self._next_actions()
        player = self._next_player(self.player_name)
        selected_action = np.argmax(next_actions[player][:, 0])
        selected_card = int(next_actions[player][selected_action, 1])
        if selected_action == 0 and self.remaining_hints > 0:  # Play
            hint = self._evaluate_playing(player, selected_card)
            if hint is not None:
                best_hint = self._best_hint_for(player)
                new_action, stats = self._simulate_hint(player, best_hint)
                if (
                    np.all(stats == next_actions[player][selected_action])
                    and selected_action == new_action
                ):
                    self.logger.info(f"Next player will play wrong. Needs {hint}")
                    self._give_hint(hint.to, hint.type, hint.value)
                    return
        elif selected_action == 2 and self.remaining_hints > 0:  # Discard
            hint = self._evaluate_discarding(player, selected_card)
            if hint is not None:
                best_hint = self._best_hint_for(player)
                new_action, stats = self._simulate_hint(player, best_hint)
                if (
                    np.all(stats == next_actions[player][selected_action])
                    and selected_action == new_action
                ):
                    self.logger.debug(
                        f"Next player will discarding useful. Needs {hint}"
                    )
                    self._give_hint(hint.to, hint.type, hint.value)
                    return
        super()._make_action()
