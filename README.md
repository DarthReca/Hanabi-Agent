<div align="center">
  Hanabi Agent
  <br />
  <a href="#about"><strong>Explore the docs »</strong></a>
  <br />
</div>

<div align="center">
<br />

[![Project license](https://img.shields.io/badge/license-Apache--2.0-blue.svg?style=flat-square)](LICENSE)
[![Project license](https://img.shields.io/badge/license-GPL--2.0-orange.svg?style=flat-square)](GPL-LICENSE)

</div>

<details open="open">
<summary>Table of Contents</summary>

- [About](#about)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Contributing](#contributing)
- [Authors & contributors](#authors--contributors)
- [License](#license)
- [Acknowledgements](#acknowledgements)

</details>

---

## About

This repo contains an agent to play Hanabi card game builded for the course Computational Intelligence at Politecnico di Torino.

There are different type of bots that can be used. Our suggestion is to select **Nexto**, because of its general better performance. To access result for all types of bot look into *Results.md*.

## Getting Started

### Prerequisites

- Python >= 3.0

- Numpy

- Scipy

## Usage

Simply run `server.py` and then run `client.py` with the requested arguments.

Client Arguments:

- --host: server ip

- --port: server listening port

- --player_name: name of the player

- --bot: type of bot to use (Poirot, Canaan, Nexto)

- --evolve: use this to tune parameters

- --epochs: number of games to play

To make life easier you can simply run `starter.ps1` and change here the parameters.

## Contributing

First off, thanks for taking the time to contribute! Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make will benefit everybody else and are **greatly appreciated**.

## Authors & contributors

For a full list of all authors and contributors, see [the contributors page](https://github.com/DarthReca/hanabi-agent/contributors).

## License

This project is licensed partially under the **GNU General Public License v2**. Interested files are *server.py*, *player/human.py* and all files in *game_data* folder.

See [GPL-LICENSE](GPL-LICENSE) for more information.

The remaining files are licensed under **Apache Software License 2.0**-

See [LICENSE](LICENSE) for more information.

## Acknowledgements

- Kato, T., & Osawa, H. (2018). I Know You Better Than You Know Yourself: Estimation of Blind Self Improves Acceptance for an Agent. In *Proceedings of the 6th International Conference on Human-Agent Interaction* (pp. 144–152). Association for Computing Machinery.

- Bouzy, B. (2017). Playing Hanabi Near-Optimally. *ACG*.

- Rodrigo Canaan, Haotian Shen, Ruben Rodriguez Torrado, Julian Togelius, Andy Nealen, & Stefan Menzel. (2018). Evolving Agents for the Hanabi 2018 CIG Competition.
