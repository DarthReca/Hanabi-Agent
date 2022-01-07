from itertools import product
from collections import Counter

# Program constants / server constants
HOST = "127.0.0.1"
PORT = 1024  # 0x4A7AB1 could have been a better port, but networkers did not allow us to have it
DATASIZE = 10240

COLORS = ["red", "yellow", "green", "blue", "white"]
CARD_COUNT = [3, 2, 2, 2, 1]
INITIAL_DECK = Counter(
    {(c, i): CARD_COUNT[i - 1] for c, i in product(COLORS, [i for i in range(1, 6)])}
)
