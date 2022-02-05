# Computational Intelligence 2021-2022

This repo contains an agent to play Hanabi card game builded for the course Computational Intelligence at Politecnico di Torino.

Project by Borzi Matteo, Cafaro Macchi Carlo and Rege Cambrin Daniele

## Client

Arguments:

- --host: server ip

- --port: server listening port

- --player_name: name of the player

- --bot: type of bot to use (Poirot, Nexto)

- --evolve: use this to tune parameters

- --epochs: number of games to play

## Bots

There are different type of bots that can be used. Our suggestion is to select **Nexto**, because of its general better performance. To access result for all types of bot look into _Results.md_.

### Nexto

Rule based agent derived from _Canaan_ with a better understanding of next player actions.

### Canaan

Rule based agent derived from _Poirot_ with a better rule-set.

### Poirot

Base version for self-estimations agents. It's a rule based agent.

## Docs

### Researchs

- https://github.com/captn3m0/boardgame-research#hanabi
- [Playing Hanabi Near-Optimally](https://helios2.mi.parisdescartes.fr/~bouzy/publications/bouzy-hanabi-2017.pdf)
- [Evolving Agents for the Hanabi 2018 CIG Competition](https://arxiv.org/pdf/1809.09764.pdf)
- [Osawa](https://aaai.org/ocs/index.php/WS/AAAIW15/paper/view/10167/10193)
- [Advances in Computer Games. Lecture Notes in Computer Science](https://sci-hub.se/10.1007/978-3-030-65883-0)
- [Emergence of Cooperative Impression With Self-Estimation, Thinking Time, and Concordance of Risk Sensitivity in Playing Hanabi](https://www.frontiersin.org/articles/10.3389/frobt.2021.658348/full)
- [Re-determinizing MCTS in Hanabi](https://ieee-cog.org/2020/papers2019/paper_17.pdf)
- [The Hanabi Challenge: A New Frontier for AI Research](https://arxiv.org/pdf/1902.00506.pdf)
- [I Know You Better Than You Know Yourself: Estimation of Blind Self Improves Acceptance for an Agent](https://sci-hub.st/https://dl.acm.org/doi/10.1145/3284432.3284453)

### Repos

- https://github.com/giove91/hanabi
- https://github.com/bstnfrmry/hanabi
- https://github.com/chikinn/hanabi
- https://github.com/Quuxplusone/Hanabi
- https://github.com/lightvector/fireflower

## Conventions

- [hanabi.github.io/docs at main · hanabi/hanabi.github.io · GitHub](https://github.com/hanabi/hanabi.github.io/tree/main/docs)

- [Tips hanabi &bull; Board Game Arena](https://en.boardgamearena.com/doc/Tips_hanabi#Finesse)
