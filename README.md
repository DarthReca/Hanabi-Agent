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
