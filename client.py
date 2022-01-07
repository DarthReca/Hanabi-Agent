#!/usr/bin/env python3

from constants import *
import argparse
import random
import player
from player.bot import Bot
from player.human import Human


if __name__ == "__main__":
    # Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", help="Server IP", default=HOST, type=str)
    parser.add_argument("--port", help="Server listening port", default=PORT, type=int)
    parser.add_argument(
        "--player_name",
        help="Player's name",
        type=str,
    )
    parser.add_argument(
        "--bot", help="True if this player is a bot", default=False, type=bool
    )
    args = parser.parse_args()
    # Select type of player
    if not args.bot:
        player = Human(args.host, args.port, args.player_name)
    else:
        player = Bot(args.host, args.port, args.player_name)

    player.run()
    player.end()
