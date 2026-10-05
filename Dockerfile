# Live lab backend for Render: FastAPI plus Omnigent, so "Start run" on the website starts the
# real agents. Same tools as a laptop run: tmux holds the interactive `omni run` session, bwrap is
# the Linux sandbox for agents with an os_env block. See docker/render-start.sh for startup.
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
        tmux bubblewrap git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Omnigent with its own Python, as on a laptop (`uv tool install`). Agent tools import `lab`,
# which needs numpy and scipy in that Python. Pinned to the version the lab was tested with.
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
RUN uv tool install --python 3.12 "omnigent[databricks]==0.16.0" --with numpy --with scipy

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt optuna

COPY . .
RUN pip install --no-cache-dir -e . && chmod +x docker/render-start.sh

EXPOSE 8000
CMD ["docker/render-start.sh"]
