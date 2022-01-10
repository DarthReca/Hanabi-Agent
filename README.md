# Computational Intelligence 2021-2022

Exam of computational intelligence 2021 - 2022. It requires teaching the client to play the game of Hanabi (rules can be found [here](https://www.spillehulen.dk/media/102616/hanabi-card-game-rules.pdf)).

## Server

The server accepts passing objects provided in GameData.py back and forth to the clients.
Each object has a `serialize()` and a `deserialize(data: str)` method that must be used to pass the data between server and client.

Watch out! I'd suggest to keep everything in the same folder, since serialization looks dependent on the import path (thanks Paolo Rabino for letting me know).

Commands for server:

- exit: exit from the server

## Client

Commands for client:

- exit: exit from the game
- ready: set your status to ready (lobby only)
- show: show cards
- hint \<type> \<destinatary> \<cards>:
  - type: 'color' or 'value'
  - destinatary: name of the person you want to ask the hint to
  - cards: the cards you are addressing to. They start from 0 and are shown in the hand order. (this will probably be removed in a later version)
- discard \<num>: discard the card _num_ (\[0-4]) from your hand

## Docs

### Researchs

- https://github.com/captn3m0/boardgame-research#hanabi
- https://helios2.mi.parisdescartes.fr/~bouzy/publications/bouzy-hanabi-2017.pdf
- [Evolving Agents for the Hanabi 2018 CIG
  Competition](https://arxiv.org/pdf/1809.09764.pdf)
- [Osawa](https://aaai.org/ocs/index.php/WS/AAAIW15/paper/view/10167/10193)
- [Sci-Hub | Advances in Computer Games. Lecture Notes in Computer Science | 10.1007/978-3-030-65883-0](https://sci-hub.se/10.1007/978-3-030-65883-0)
- [Frontiers | Emergence of Cooperative Impression With Self-Estimation, Thinking Time, and Concordance of Risk Sensitivity in Playing Hanabi | Robotics and AI](https://www.frontiersin.org/articles/10.3389/frobt.2021.658348/full)
- [MCTS](https://ieee-cog.org/2020/papers2019/paper_17.pdf)
- [The Hanabi Challenge: A New Frontier for AI Research](https://arxiv.org/pdf/1902.00506.pdf)

### Repos

- https://github.com/giove91/hanabi
- https://github.com/bstnfrmry/hanabi
- https://github.com/chikinn/hanabi
- https://github.com/Quuxplusone/Hanabi
- https://github.com/lightvector/fireflower

## Conventions

- [hanabi.github.io/docs at main · hanabi/hanabi.github.io · GitHub](https://github.com/hanabi/hanabi.github.io/tree/main/docs)

- [Tips hanabi &bull; Board Game Arena](https://en.boardgamearena.com/doc/Tips_hanabi#Finesse)
