# PsychoPy on NixOS — Design

## Goal

A small repo whose **single job** is to make `nix run .#default` reliably
launch PsychoPy on any NixOS host. Verified on Saturn (Framework 13, AMD,
NixOS-unstable).

## Why this exists

PsychoPy is not in nixpkgs, and its dependency closure (wxPython, pyo,
soundfile, ffmpeg-python, …) is not friendly to pure-nix packaging. A
naive `pythonEnv` + shellHook venv approach breaks `nix run` because
`python -m psychopy` resolves to the empty pythonEnv rather than the
on-demand venv.

The design problem is "PsychoPy-via-pip on NixOS without an
`LD_LIBRARY_PATH` dance and without first-run state coupled to
`nix develop`".

## Approach: FHS env + venv (`buildFHSEnv`)

`pkgs.buildFHSEnv` produces a chroot-like environment with a
normal-Linux library layout (`/usr/lib`, `/lib64`, etc.) so PyPI's
binary wheels work without `LD_LIBRARY_PATH` patching. The flake
stores all system libraries PsychoPy needs (X11, GL, GTK3, gstreamer,
portaudio, libsndfile, ffmpeg, liblsl, …) inside that env.

A launcher script enters the FHS env, ensures a venv exists at a
deterministic path, dispatches to PsychoPy.

**Venv location:**
```
${XDG_STATE_HOME:-$HOME/.local/state}/psychopy-flake/<sha-12-of-requirements.txt>/venv
```

The 12-char sha prefix means changing `requirements.txt` automatically
forces a fresh venv on next launch — no cache invalidation logic
needed. Old venvs sit unused until the user `rm`s them.

**First-run cost:** ~2-3 minutes (`pip install psychopy==2026.1.3` plus
~30 transitive deps). Subsequent launches: ~0s overhead.

## Repo layout

```
.
├── flake.nix
├── flake.lock
├── requirements.txt              # psychopy==2026.1.3 + pinned deps
├── README.md
├── .gitignore
├── nix/
│   ├── module.nix                # nixosModules.psychopy
│   ├── fhs.nix                   # buildFHSEnv definition
│   └── launcher.nix              # writeShellScript launcher + per-subcmd wrappers
├── src/
│   ├── hardware_report.py
│   └── distance_analysis.py
├── bin/
│   └── psychopy-run              # non-nix fallback (kept lightweight)
├── examples/
│   └── DualTask/
└── docs/
    ├── index.html
    ├── reports_index.json        # used by hardware-report
    └── specs/design.md           # this file
```

## Flake outputs

```
packages.x86_64-linux.{default, psychopy-builder, psychopy-coder, psychopy-run, hardware-report}
apps.x86_64-linux.{default, builder, coder, run, hardware-report}
devShells.x86_64-linux.default
nixosModules.psychopy
formatter.x86_64-linux               # nixfmt-rfc-style
checks.x86_64-linux.import-smoketest # builds venv, imports psychopy + wx + pylsl
```

| Command                                      | Behavior                                              |
| -------------------------------------------- | ----------------------------------------------------- |
| `nix run .#default`                          | `python -m psychopy` — starter app picker (Builder/Coder/Runner) |
| `nix run .#builder [-- file.psyexp]`         | PsychoPy Builder, optionally opening a file           |
| `nix run .#coder [-- file.py]`               | PsychoPy Coder                                        |
| `nix run .#run -- file.psyexp`               | Runs the experiment (compiles & executes)             |
| `nix run .#hardware-report`                  | Generates `docs/hardware_<host>_<ts>.html` + index    |
| `nix develop`                                | Drops into a shell with `psychopy` on PATH            |

## NixOS module

```nix
options.programs.psychopy.enable = lib.mkEnableOption "PsychoPy timing-priority limits";
config = lib.mkIf cfg.enable {
  users.groups.psychopy = {};
  security.pam.loginLimits = [
    { domain = "@psychopy"; type = "-"; item = "nice";    value = "-20"; }
    { domain = "@psychopy"; type = "-"; item = "rtprio";  value = "50"; }
    { domain = "@psychopy"; type = "-"; item = "memlock"; value = "unlimited"; }
  ];
};
```

A host adopts it via:
```nix
imports = [ inputs.psychopy.nixosModules.psychopy ];
programs.psychopy.enable = true;
users.users.<your-user>.extraGroups = [ "psychopy" ];
```

## Key decisions

| Decision                | Choice          | Rationale                                                            |
| ----------------------- | --------------- | -------------------------------------------------------------------- |
| Default `nix run`       | starter app     | Matches `python -m psychopy`                                         |
| Packaging strategy      | FHS env + venv  | Pure-nix would be a yak-shave for binary wheels                      |
| PsychoPy version        | **2026.1.3**    | Latest stable on PyPI at the time of writing                         |
| Python version          | 3.11            | PsychoPy `requires_python = "<3.12,>=3.9"`                           |
| Docker assets           | dropped         | Out of scope for a nix-first repo                                    |
| Hardware report         | kept            | Useful for verifying timing-relevant hardware on a new host          |
| NixOS module            | kept            | Timing accuracy needs rtprio/memlock                                 |
| Venv state path         | `$XDG_STATE_HOME/psychopy-flake/<sha>/` | Deterministic, requirements-aware       |

## Verification

1. `nix flake check --impure`             → exits 0
2. `nix build .#default`                  → builds; result symlink ok
3. `nix run .#hardware-report`            → produces dated HTML in `docs/`
4. `nix run .#default`                    → opens PsychoPy starter window
5. `nix develop -c psychopy --version`    → prints `2026.1.3`

Reliability claim is satisfied when **(1)+(2)+(5)** pass headless and
**(3)+(4)** pass on a session with display.

## What this repo explicitly does not build

- pure-nix python derivations for psychopy/wx/pylsl
- Docker / docker-compose / docker-entrypoint
- Auto-create-venv shell hook on `nix develop` — replaced by the launcher
