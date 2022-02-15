from copy import deepcopy
from typing import Dict, List, Optional

import numpy as np
from scipy.special import softmax

from game_utils import CardKnowledge, Mutator

from .canaan_bot import CanaanBot
from .poirot import Hint


class Nexto(CanaanBot):
    """
    Nexto extend the behavior of CanaanBot, trying to understand which will be the action of the next player. It is similar to depth-one search algorithm of Bouzy[1].

    References
    ----------
    [1] B. Bouzy, "Playing Hanabi Near-Optimally"
    """

    def _simulate_next_actions(self) -> Dict[str, np.ndarray]:
        """Foreach player returns the probability of each possible action."""
        return {
            player: self._simulate_action(self.players_knowledge[player])
            for player in self.players
            if player != self.player_name
        }

    def _simulate_action(self, knowledge: List[CardKnowledge]) -> np.ndarray:
        """
        With the given `knowledge` returns probability of each possible action.

        Returns
        -------
        weight_selection: np.ndarray
            Each row represents an action (Play, Hint, Discard) and contains (probability of doing the action, card affected by the action)
        """
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
        # Less usable and precious
        probable_discarded = np.argmin(np.sum(stats[:, 1:2], axis=1))
        # Denormalized weights
        weights = np.array(
            [
                stats[probable_played, 0],
                self.parameters["hint_probability"],
                1 - stats[probable_discarded, 1],  # We use only usability
            ]
        )
        if self.remaining_hints == 8:  # Cannot discard
            weights[2] = 0
        if self.remaining_hints == 0:  # Cannot hint
            weights[1] = 0
        # Normalized weights
        weights = softmax(weights)
        return np.array(
            [
                (weights[0], probable_played),
                (weights[1], -1),
                (weights[2], probable_discarded),
            ]
        )

    def _simulate_hint(self, target_player: str, hint: Hint) -> np.ndarray:
        """
        Simulate giving `hint` to `target_player`.

        Returns
        -------
        new_action: int
            new_action is the probable action the `target_player` will do after this hint.
        weight_selection: ndarray
            (probability of doing the action, card affected by the action)
        """
        # Simulate hint on a copy of player's knowledge
        new_knowledge = deepcopy(self.players_knowledge[target_player])
        hand = self.player_cards[target_player]
        for i, card in enumerate(hand):
            if hint.type == "color" and card.color == hint.value:
                new_knowledge[i].set_suggested_color(hint.value)
            elif hint.type == "value" and card.value == hint.value:
                new_knowledge[i].set_suggested_value(hint.value)
        # Simulate the action
        new_actions = self._simulate_action(new_knowledge)
        selected_action = np.argmax(new_actions[:, 0])
        return np.concatenate(
            [
                np.array([selected_action], dtype=np.float64),
                new_actions[selected_action],
            ]
        )

    def _evaluate_playing(self, player: str, card_index: int) -> Optional[Hint]:
        """Evaluate if playing `card_index` is risky for `player`. If risky try giving an hint to solve the problem."""
        hand = self.player_cards[player]
        card = hand[card_index]
        knowledge = self.players_knowledge[player][card_index]
        possible_hints = []
        if (card.color, card.value) not in self.table.next_playable_cards():
            if len(knowledge.possible_values()) != 1:
                cards_of_value = sum([1 for c in hand if c.value == card.value])
                possible_hints.append(Hint(player, "value", card.value, cards_of_value))
            if len(knowledge.possible_colors()) != 1:
                cards_of_color = sum([1 for c in hand if c.color == card.color])
                possible_hints.append(Hint(player, "color", card.color, cards_of_color))
        for hint in possible_hints:
            new_action = self._simulate_hint(player, hint)
            if new_action[0] != 0 or int(new_action[2]) != card_index:
                return hint  # We are changing action or at least card
        return None

    def _evaluate_discarding(self, player: str, card_index: int) -> Optional[Hint]:
        """Evaluate if discarding `card_index` is risky for `player`. If risky try giving an hint to solve the problem."""
        hand = self.player_cards[player]
        card = hand[card_index]
        knowledge = self.players_knowledge[player][card_index]
        # Select all reasonable hints to give
        possible_hints = []
        if (card.color, card.value) in self.table.next_playable_cards().union(
            self.table.precious_cards()
        ):
            if len(knowledge.possible_values()) != 1:
                cards_of_value = sum([1 for c in hand if c.value == card.value])
                possible_hints.append(Hint(player, "value", card.value, cards_of_value))
            if len(knowledge.possible_colors()) != 1:
                cards_of_color = sum([1 for c in hand if c.color == card.color])
                possible_hints.append(Hint(player, "color", card.color, cards_of_color))
        # Simulate if hints are useful or they do not change anything
        for hint in possible_hints:
            new_action = self._simulate_hint(player, hint)
            if new_action[0] != 2 or int(new_action[2]) != card_index:
                return hint  # We are changing action or at least card
        return None

    def _make_action(self) -> None:
        simulation = self._simulate_next_actions()
        # Focusing only on next player
        player = self._next_player(self.player_name)
        player_simulation = simulation[player]
        selected_action = np.argmax(player_simulation[:, 0])
        selected_card = int(player_simulation[selected_action, 1])
        hint = None
        if selected_action == 0 and self.remaining_hints > 0:  # Play
            hint = self._evaluate_playing(player, selected_card)
        elif selected_action == 2 and self.remaining_hints > 0:  # Discard
            hint = self._evaluate_discarding(player, selected_card)
        if hint is not None:
            # Try giving best_hint to see if player will change his behavior
            best_hint = self._best_hint_for(player)
            new_action = self._simulate_hint(player, best_hint)
            if new_action[2] != selected_card or new_action[0] != selected_action:
                hint = best_hint
            actions = ["play", "hint", "discard"]
            self.logger.info(
                f"Giving hint {hint}. Player is going to {actions[int(new_action[0])]} wrong."
            )
            self._give_hint(hint.to, hint.type, hint.value)
            return
        # Execute CanaanBot ruleset
        super()._make_action()
