{ config, lib, pkgs, ... }:

let
  cfg = config.programs.psychopy;
  psychopyApp = pkgs.callPackage ./psychopy-app.nix { };
in
{
  options.programs.psychopy = {
    enable = lib.mkEnableOption "the PsychoPy fleet runner (binary + .desktop + timing-priority limits)";

    package = lib.mkOption {
      type = lib.types.package;
      default = psychopyApp;
      defaultText = lib.literalExpression "pkgs.callPackage ./psychopy-app.nix { }";
      description = ''
        The PsychoPy package to install. Override if you maintain a fork
        with different pins. The default ships PsychoPy 2026.1.3 with
        wxPython 4.2.2 inside an FHS env; the venv is created on first
        run at $XDG_STATE_HOME/psychopy-flake/<reqs-hash>/venv.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    # The bundled package: binaries on PATH + .desktop entries +
    # hicolor icons. After enabling, PsychoPy shows up in the Plasma /
    # GNOME app dashboard and as a `psychopy` command in any shell.
    environment.systemPackages = [ cfg.package ];

    # Group + PAM limits: PsychoPy's PTB audio backend and high-rate
    # visual stims need elevated rt priority + locked memory to hit
    # their timing budgets. Without these the app prints "Setup does
    # not appear to be complete" on every launch.
    users.groups.psychopy = { };

    security.pam.loginLimits = [
      { domain = "@psychopy"; type = "-"; item = "nice"; value = "-20"; }
      { domain = "@psychopy"; type = "-"; item = "rtprio"; value = "50"; }
      { domain = "@psychopy"; type = "-"; item = "memlock"; value = "unlimited"; }
    ];
  };
}
