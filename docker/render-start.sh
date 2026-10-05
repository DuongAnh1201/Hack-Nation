#!/bin/sh
# Container startup for the live lab (see Dockerfile). Deterministic setup only: it decides nothing
# about the research.
set -eu
cd /app

# Runs and Omnigent's state live on the persistent disk when there is one (render.yaml mounts
# /data), so a redeploy keeps finished runs and their session history.
DATA="${LAB_DATA_DIR:-/data}"
if [ -d "$DATA" ] && [ -w "$DATA" ]; then
  mkdir -p "$DATA/runs" "$DATA/omnigent"
  cp -Rn /app/runs/example "$DATA/runs/" 2>/dev/null || true  # template the Experiment Runner follows
  rm -rf /app/runs "$HOME/.omnigent"
  ln -s "$DATA/runs" /app/runs
  ln -s "$DATA/omnigent" "$HOME/.omnigent"
else
  echo "render-start: no writable $DATA, runs are lost on redeploy" >&2
  mkdir -p /app/runs "$HOME/.omnigent"
fi

# Omnigent drops shell secrets from agent processes, so the Claude key is a provider entry that
# Omnigent's server reads from its own environment, and read_paper reads Bright Data's token
# from the repo's .env (as on a laptop).
if [ -n "${ANTHROPIC_API_KEY:-}" ] && [ ! -f "$HOME/.omnigent/config.yaml" ]; then
  cat > "$HOME/.omnigent/config.yaml" <<EOF
providers:
  anthropic:
    anthropic:
      api_key_ref: env:ANTHROPIC_API_KEY
      base_url: https://api.anthropic.com
      models:
        default: ${LAB_MODEL:-claude-sonnet-5-5}
    default: true
    kind: key
EOF
fi
if [ -n "${BRIGHTDATA_API_TOKEN:-}" ]; then
  printf 'BRIGHTDATA_API_TOKEN=%s\n' "$BRIGHTDATA_API_TOKEN" > /app/.env
fi

omni start || echo "render-start: omni start failed; /api/lab/status will say why runs cannot start" >&2

cd /app/backend
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
