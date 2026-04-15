[![Python](https://img.shields.io/badge/Python-3.13-3776AB.svg?style=flat&logo=python&logoColor=ffd343)](https://docs.python.org/3.13/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![CI](https://img.shields.io/github/actions/workflow/status/javidahmed64592/psarc-library/ci.yml?branch=main&style=flat-square&label=CI&logo=github)](https://github.com/javidahmed64592/psarc-library/actions/workflows/ci.yml)
[![Build](https://img.shields.io/github/actions/workflow/status/javidahmed64592/psarc-library/build.yml?branch=main&style=flat-square&label=Build&logo=github)](https://github.com/javidahmed64592/psarc-library/actions/workflows/build.yml)
[![Docs](https://img.shields.io/github/actions/workflow/status/javidahmed64592/psarc-library/docs.yml?branch=main&style=flat-square&label=Docs&logo=github)](https://github.com/javidahmed64592/psarc-library/actions/workflows/docs.yml)
[![Docker](https://img.shields.io/github/actions/workflow/status/javidahmed64592/psarc-library/docker.yml?branch=main&style=flat-square&label=Docker&logo=github)](https://github.com/javidahmed64592/psarc-library/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- omit from toc -->
# Psarc Library

A web interface for parsing and exploring Rocksmith psarc files.

<!-- omit from toc -->
## Table of Contents
- [Quick Start](#quick-start)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Managing the Container](#managing-the-container)
- [License](#license)

### Installation

Download the latest release from [GitHub Releases](https://github.com/javidahmed64592/psarc-library/releases).

### Configuration

Rename `.env.example` to `.env` and edit it to configure the server.

- `HOST`: Server host address (default: localhost)
- `PORT`: Server port (default: 443)
- `API_TOKEN_HASH`: Leave blank to auto-generate on first run, or provide your own token hash

### Managing the Container

```sh
# Start the container
docker compose up -d

# Stop the container
docker compose down

# Update to the latest version
docker compose pull && docker compose up -d

# View the logs
docker compose logs -f psarc-library
```

**Note:** You may need to add your user to the Docker group and log out/in for permission changes to take effect:
```sh
sudo usermod -aG docker ${USER}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
