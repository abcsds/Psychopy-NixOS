# PsychoPy fleet runner

A flake-first launcher that makes PsychoPy run reliably on the Wanderers
fleet (and any other NixOS host).

```
nix run github:abcsds/psychopy#default
```

The first invocation builds an FHS sandbox with all the system libraries
PsychoPy's binary wheels expect (X11, GL, GTK3, gstreamer, portaudio,
libsndfile, ffmpeg, liblsl, …) and creates a Python 3.11 venv at
`$XDG_STATE_HOME/psychopy-flake/<reqs-hash>/venv` (≈ 2-3 min). Subsequent
launches are instant.

## Usage

| Command                                         | What it does                          |
| ----------------------------------------------- | ------------------------------------- |
| `nix run .#default`                             | PsychoPy starter app picker           |
| `nix run .#builder [-- file.psyexp]`            | Open Builder, optionally with a file  |
| `nix run .#coder [-- file.py]`                  | Open Coder                            |
| `nix run .#run -- file.psyexp`                  | Run an experiment to completion       |
| `nix run .#hardware-report`                     | Generate `docs/hardware_<host>_<ts>.html` |
| `nix run .#smoketest`                           | Print psychopy/wx/pylsl versions      |
| `nix develop`                                   | Drop into a shell with everything on PATH |

## NixOS integration (Wanderers)

For low-latency timing, this flake exports a `nixosModules.psychopy` that
sets `nice=-20`, `rtprio=50`, `memlock=unlimited` for members of the
`psychopy` group. Wire it up from a wanderer's device config:

```nix
# devices/<host>/default.nix
{
  imports = [ inputs.psychopy.nixosModules.psychopy ];
  programs.psychopy.enable = true;
  users.users.beto.extraGroups = [ "psychopy" ];
}
```

…and add the input to the fleet flake:

```nix
inputs.psychopy.url = "github:abcsds/psychopy";
```

## Design

See [`docs/superpowers/specs/2026-04-26-psychopy-fleet-runner-design.md`](docs/superpowers/specs/2026-04-26-psychopy-fleet-runner-design.md).

PsychoPy is **not** in nixpkgs, and its dependency closure (wxPython,
pyo, soundfile, ffmpeg-python, …) is not friendly to pure-nix
packaging. This repo does the pragmatic thing: ship a `buildFHSEnv`
that holds the system libraries, ship a launcher that creates a venv
once, accept the small first-run cost in exchange for "it just works"
on the whole fleet.

## Updating the pin

Edit `requirements.txt`. The launcher hashes the file content and uses
the first 12 chars as the venv directory name, so changing any pin
forces a fresh venv on the next launch — no stale-cache footguns.

## Examples

`examples/DualTask/DualTask.psyexp` is a working PsychoPy experiment.
Smoketest the runner with:

```
nix run .#run -- examples/DualTask/DualTask.psyexp
```
