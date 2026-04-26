{ pkgs, reqs, reqsHash, srcDir }:

# A single launcher invoked by the FHS env's runScript.
#
# argv[1] selects which PsychoPy entry point to dispatch to:
#   default          → python -m psychopy           (starter app picker)
#   builder          → psychopyApp main, builder mode
#   coder            → psychopyApp main, coder mode
#   run              → psychopyApp main, run mode (expects an experiment file)
#   hardware-report  → src/hardware_report.py
#
# The venv is created on first run at:
#   $XDG_STATE_HOME/psychopy-flake/<reqsHash>/venv
# and reused indefinitely. Changing requirements.txt → new hash → new venv.

pkgs.writeShellScript "psychopy-launcher" ''
  set -euo pipefail

  if [ $# -lt 1 ]; then
    echo "psychopy-launcher: missing subcommand" >&2
    exit 64
  fi

  SUBCMD="$1"
  shift

  REQS="${reqs}"
  REQS_HASH="${reqsHash}"
  SRC_DIR="${srcDir}"
  STATE_DIR="''${XDG_STATE_HOME:-$HOME/.local/state}/psychopy-flake"
  VENV="$STATE_DIR/$REQS_HASH/venv"

  if [ ! -x "$VENV/bin/python" ]; then
    echo "" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    echo " PsychoPy first-run setup (this may take 2–3 minutes)" >&2
    echo " venv → $VENV" >&2
    echo "═══════════════════════════════════════════════════════════════" >&2
    mkdir -p "$STATE_DIR/$REQS_HASH"
    python3.11 -m venv --copies "$VENV"
    "$VENV/bin/pip" install --upgrade --quiet pip setuptools wheel
    # wxPython has no manylinux wheel on PyPI — its prebuilt Linux wheels
    # live on the project's own index, tagged `linux_x86_64` (not
    # manylinux). Pip rejects that platform tag from a remote index, so
    # we install the wheel by direct URL instead. The ubuntu-22.04 wheel
    # set is ABI-compatible with this FHS env.
    "$VENV/bin/pip" install --quiet \
      https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-24.04/wxPython-4.2.2-cp311-cp311-linux_x86_64.whl
    "$VENV/bin/pip" install --quiet -r "$REQS"
    echo " ✓ venv ready" >&2
    echo "" >&2
  fi

  export PYTHONWARNINGS="''${PYTHONWARNINGS:-ignore::RuntimeWarning}"

  # PsychoPy ≥ 2026 takes flags, not subcommands:
  #   --builder/-b   open Builder
  #   --coder/-c     open Coder
  #   --runner/-r    open Runner
  #   --direct/-x    run a .py / .psyexp without opening the app
  # The `psychopy` console script is what we exec; its argv parser is
  # `psychopyApp.main`'s argparse setup.
  case "$SUBCMD" in
    default)
      exec "$VENV/bin/psychopy" "$@"
      ;;
    hardware-report)
      exec "$VENV/bin/python" "$SRC_DIR/hardware_report.py" "$@"
      ;;
    builder)
      # `--no-splash` works around a 2026.1.x bug where the splash screen
      # closing before Builder is fully realised causes wx's MainLoop to
      # exit immediately (~0.7 s after launch). Verified on Saturn —
      # without `--no-splash`, `psychopy --builder` quits at 0.69 s.
      exec "$VENV/bin/psychopy" --builder --no-splash "$@"
      ;;
    coder)
      exec "$VENV/bin/psychopy" --coder --no-splash "$@"
      ;;
    run)
      # `--direct` runs the experiment without opening the GUI shell.
      exec "$VENV/bin/psychopy" --direct "$@"
      ;;
    smoketest)
      exec "$VENV/bin/python" -c "
import psychopy, wx, pylsl
print(f'psychopy={psychopy.__version__}')
print(f'wxpython={wx.version()}')
print(f'pylsl={pylsl.__version__}')
"
      ;;
    shell)
      # Diagnostic shell inside the FHS env with the venv on PATH.
      export PATH="$VENV/bin:$PATH"
      exec bash "$@"
      ;;
    *)
      echo "psychopy-launcher: unknown subcommand '$SUBCMD'" >&2
      echo "  expected one of: default builder coder run hardware-report smoketest shell" >&2
      exit 64
      ;;
  esac
''
