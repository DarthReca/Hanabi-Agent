from subprocess import Popen, PIPE, STDOUT
import argparse
from time import sleep


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("--bot_number", default=2, type=int)

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    server = Popen(["python", "server.py"], stdin=PIPE, stdout=PIPE, stderr=STDOUT)
    try:
        bots = [
            Popen(
                ["python", "client.py", "--bot", "Poirot", "--player_name", f"Bot{i}"],
                stdin=PIPE,
                stdout=PIPE,
                stderr=STDOUT,
            )
            for i in range(args.bot_number)
        ]
    except:
        server.kill()

    server.kill()
    for bot in bots:
        bot.kill()
