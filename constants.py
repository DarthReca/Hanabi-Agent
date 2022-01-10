import numpy as np

# Program constants / server constants
HOST = "127.0.0.1"
PORT = 1024  # 0x4A7AB1 could have been a better port, but networkers did not allow us to have it
DATASIZE = 10240

COLORS = ["red", "yellow", "green", "blue", "white"]
CARD_COUNT = [3, 2, 2, 2, 1]
INITIAL_DECK = np.array(
    [CARD_COUNT for _ in range(5)],
    dtype=np.uint8,
)
