#!/usr/bin/env python3

from constants import *
import argparse
import random
import player
import os


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
    parser.add_argument("--evolve", default=False, action="store_const", const=True)
    parser.add_argument(
        "--bot",
        help="Type of bot if this is not a player",
        default="",
        type=str,
        choices=["Poirot", "Canaan", "Nexto"],
    )
    parser.add_argument("--epochs", type=int, default=1)
    args = parser.parse_args()
    # Select type of player
    if not args.bot:
        player = player.Human(args.host, args.port, args.player_name)
    elif args.bot == "Poirot":
        player = player.Poirot(args.host, args.port, args.player_name, args.epochs)
    elif args.bot == "Canaan":
        player = player.CanaanBot(
            args.host,
            args.port,
            args.player_name,
            args.epochs,
            "params/canaan2_params.json",
            args.evolve,
        )
    elif args.bot == "Nexto":
        player = player.Nexto(
            args.host,
            args.port,
            args.player_name,
            args.epochs,
            "params/nexto1_params.json",
            args.evolve,
        )

    player.run()
    player.end()
