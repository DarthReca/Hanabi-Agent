#!/usr/bin/env python3

from constants import *
import argparse
import random
import player
import player


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
        "--bot",
        help="Type of bot if this is not a player",
        default="",
        type=str,
        choices=["Poirot", "MrSimple"],
    )
    args = parser.parse_args()
    # Select type of player
    if not args.bot:
        player = player.Human(args.host, args.port, args.player_name)
    elif args.bot == "Poirot":
        player = player.Poirot(args.host, args.port, args.player_name)
    elif args.bot == "MrSimple":
        player = player.MrSimple(args.host, args.port, args.player_name)

    player.run()
    player.end()
