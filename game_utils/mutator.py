import numpy as np
from typing import Dict


class Mutator:
    def __init__(self, starting_variance: float, params_count: int) -> None:
        self.params_count = params_count
        self.variance = starting_variance
        self.lr = 1 / np.sqrt(params_count)
        self.last_params = ({}, -1)
        self.active = True

    def activate(self, active: bool):
        self.active = active

    def mutate(self, params: Dict[str, float], result: float) -> Dict[str, float]:
        if result > self.last_params[1]:
            self.last_params = (params, result)
        if not self.active:
            return self.last_params[0]
        self.variance = self.variance * np.exp(self.lr * np.random.standard_normal())
        mutated = {}
        for k, v in self.last_params[0].items():
            mutated[k] = np.random.normal(loc=v, scale=self.variance)
            if mutated[k] < 0:
                mutated[k] = 0.0
            if mutated[k] > 1:
                mutated[k] = 1.0
        return mutated

    def best_one(self):
        return self.last_params[0]
