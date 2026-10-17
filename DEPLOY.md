# Installing Model D: one developer, a team, an enterprise

Model D runs on your own machines. It maps your code with a small embedding model that runs locally, and nothing
leaves the machine. The one exception is the first download of that model (about 420 MB), and you can fetch it in
advance (see Enterprise).

## One developer

```bash
uv tool install model-d          # or: pipx install model-d   /   pip install model-d
modeld install                   # registers Model D with Claude Code, Codex, Gemini CLI and Kiro, if found
modeld build .                   # maps this repository into ./modeld-out
```

Then, in Claude Code, `/modeld .` maps a repository, and the agent asks Model D before it searches. From a terminal:

```bash
modeld ask "why does login fail after a password reset?" --scope code
modeld teach "why does login fail after a password reset?" app/auth/reset.py:88
```

`--scope code` leaves documentation out, which is the setting for bug reports. `modeld mcp` (or `modeld-mcp`) serves
the same tools over MCP to any client. With no server set, it serves the nearest `modeld-out` in-process.

## A team

One shared workspace server holds the map. When one engineer's agent learns where something is, everyone's agent
knows it.

**With Docker** (from a clone of this repository):

```bash
mkdir repos && git clone <your repository> repos/app      # one folder per repository to map
docker compose up -d                                      # maps ./repos on first start, serves on port 7700
```

**Without Docker**, on any machine the team can reach:

```bash
uv tool install model-d
modeld build /srv/code/app --out /srv/modeld
modeld serve /srv/modeld --host 0.0.0.0 --port 7700
```

**Each engineer**, once:

```bash
uv tool install model-d
modeld install --team http://<server>:7700
```

To wire a repository's hooks and MCP for everyone who clones it, run this once and commit the files it writes:

```bash
modeld init all --url http://<server>:7700
```

**After large code changes**, refresh the map. The rebuild keeps everything the team taught, and it re-finds each
lesson's line even after the code moves. With `--cache`, it embeds only the code that changed: a rebuild that took
ten minutes takes seconds, with the same result bit for bit. Then restart the server:

```bash
docker compose exec modeld modeld build /repos --out /workspace --cache /workspace-cache/embed.sqlite && docker compose restart
```

## An enterprise, including machines with no internet

- **The Docker image needs no network once it is built.** The embedding model is baked in at build time, and the server
  runs with `OCM_OFFLINE=1`. To move it into a closed network:

  ```bash
  docker compose build
  docker save model-d:0.4.0 | gzip > model-d-0.4.0.tar.gz   # copy this file across, then:
  docker load < model-d-0.4.0.tar.gz
  ```

- **Without Docker,** build an offline bundle on a connected machine with the same OS, CPU type and Python version.
  It holds the wheels, PyTorch and the embedding model:

  ```bash
  scripts/offline-bundle.sh modeld-offline
  # on the offline machine:
  modeld-offline/install.sh
  export HF_HOME=$PWD/modeld-offline/hf OCM_OFFLINE=1
  ```

- **What leaves your network:** nothing, in map, ask and teach. The hybrid mode (`modeld hybrid`) calls the model API
  you configure (Claude, OpenAI or Gemini) with the question and the code Model D selected. Without it, no model API is
  called.
- **What it stores:** the map (vectors of your code and docs), the questions it was taught, attached as vectors to code
  lines, and a log of calls (`calls.jsonl`). It stores no answers and no prose. Everything lives in the workspace
  folder you choose.
- **Licence:** Apache-2.0, so you can run, modify and redistribute it internally.

## Upgrading

```bash
uv tool upgrade model-d
modeld build . --out modeld-out --cache ~/.cache/modeld/embed.sqlite   # carries what was taught; embeds only changes
```
