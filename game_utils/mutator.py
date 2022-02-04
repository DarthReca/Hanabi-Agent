import numpy as np
from typing import Dict


class Mutator:
    def __init__(self, starting_variance: float, params_count: int) -> None:
        self.params_count = params_count
        self.variance = starting_variance
        self.lr = 1 / np.sqrt(params_count)
        self.last_params = ({}, -1.0)
        self.active = True
        self.rng = np.random.default_rng()

    def activate(self, active: bool):
        self.active = active

    def mutate(self, params: Dict[str, float], result: float) -> Dict[str, float]:
        if result > self.last_params[1]:
            self.last_params = (params, result)
        if not self.active:
            return self.last_params[0]
        self.variance = self.variance * np.exp(self.lr * self.rng.standard_normal())
        mutated = {}
        for k, v in self.last_params[0].items():
            # Sample from a normal, remove useless values and select one
            samples = self.rng.normal(loc=v, scale=self.variance, size=100)
            samples = samples[np.logical_and(samples >= 0, samples <= 1)]
            mutated[k] = self.rng.choice(samples)
        return mutated

    def best_one(self):
        return self.last_params[0]
