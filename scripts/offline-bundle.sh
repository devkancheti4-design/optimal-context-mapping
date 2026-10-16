#!/usr/bin/env bash
# Build an offline install bundle of Model D for machines with no internet access.
# Run it on a connected machine with the same operating system, CPU type and Python version as the target.
#   scripts/offline-bundle.sh [out-folder]          (default: modeld-offline)
#   MODELD_SPEC=dist/model_d-0.4.0-py3-none-any.whl scripts/offline-bundle.sh   (bundle a local build)
set -euo pipefail
OUT="${1:-modeld-offline}"
SPEC="${MODELD_SPEC:-model-d}"
PY="${PYTHON:-python3}"
mkdir -p "$OUT/wheels"

if [ "$(uname -s)" = "Linux" ]; then          # the CPU build of PyTorch is far smaller than the default on Linux
  "$PY" -m pip download --dest "$OUT/wheels" --index-url https://download.pytorch.org/whl/cpu torch
fi
"$PY" -m pip download --dest "$OUT/wheels" "$SPEC"

# The embedding model, fetched once with a throwaway install of Model D.
VENV="$(mktemp -d)/venv"
"$PY" -m venv "$VENV"
"$VENV/bin/pip" install --quiet --no-index --find-links "$OUT/wheels" model-d
"$VENV/bin/modeld" fetch-model --to "$OUT/hf"
rm -rf "$(dirname "$VENV")"

cat > "$OUT/install.sh" <<'INSTALL'
#!/usr/bin/env bash
# Install Model D from this bundle, with no network access.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
"${PYTHON:-python3}" -m pip install --no-index --find-links "$HERE/wheels" model-d
echo
echo "Add to your shell profile, so Model D finds its model and never reaches the network:"
echo "  export HF_HOME=\"$HERE/hf\" OCM_OFFLINE=1"
INSTALL
chmod +x "$OUT/install.sh"
echo "bundle ready: $OUT (copy it to the offline machine and run $OUT/install.sh)"
