from concurrent.futures import thread
from subprocess import Popen, PIPE, STDOUT
import argparse
from multiprocessing import Pool
from time import sleep
import os


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--bot_number", default=2, type=int)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if os.path.exists("Bot0.log"):
        os.remove("Bot0.log")
        os.remove("Bot1.log")
        os.remove("game.log")
    server = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    sleep(1)
    bots = []
    try:
        for i in range(args.bot_number):
            bots.append(
                Popen(
                    [
                        "python",
                        "client.py",
                        "--bot",
                        "Poirot",
                        "--player_name",
                        f"Bot{i}",
                    ],
                    stdin=PIPE,
                    stdout=PIPE,
                    stderr=STDOUT,
                )
            )
    except:
        server.kill()

    for bot in bots:
        bot.wait()
    server.kill()
