{ config, lib, pkgs, ... }:

let
  cfg = config.programs.psychopy;
in
{
  options.programs.psychopy = {
    enable = lib.mkEnableOption "PsychoPy timing-priority limits and group";
  };

  config = lib.mkIf cfg.enable {
    users.groups.psychopy = { };

    security.pam.loginLimits = [
      { domain = "@psychopy"; type = "-"; item = "nice"; value = "-20"; }
      { domain = "@psychopy"; type = "-"; item = "rtprio"; value = "50"; }
      { domain = "@psychopy"; type = "-"; item = "memlock"; value = "unlimited"; }
    ];
  };
}
