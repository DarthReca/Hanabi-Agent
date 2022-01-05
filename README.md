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
- https://arxiv.org/pdf/1809.09764.pdf
- [Osawa](https://aaai.org/ocs/index.php/WS/AAAIW15/paper/view/10167/10193)

### Repos

- https://github.com/giove91/hanabi
- https://github.com/bstnfrmry/hanabi
- https://github.com/chikinn/hanabi
