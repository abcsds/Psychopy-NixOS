{
  pkgs,
  lib ? pkgs.lib,
  stdenvNoCC ? pkgs.stdenvNoCC,
  copyDesktopItems ? pkgs.copyDesktopItems,
  makeDesktopItem ? pkgs.makeDesktopItem,
}:

# A single, drop-in PsychoPy package that NixOS hosts can install via
# `environment.systemPackages` (or via the flake's NixOS module). It
# bundles:
#
#   - bin/psychopy             — starter app picker
#   - bin/psychopy-builder     — Builder
#   - bin/psychopy-coder       — Coder
#   - bin/psychopy-run         — `--direct` runner
#   - bin/psychopy-hardware-report
#   - bin/psychopy-smoketest
#   - bin/psychopy-shell       — diagnostic FHS shell
#   - share/applications/PsychoPy{,-builder,-coder}.desktop
#   - share/icons/hicolor/{256,512}x{256,512}/apps/psychopy.png
#   - share/pixmaps/psychopy.png   (legacy fallback)
#
# All of the wrappers exec into the same `psychopy-fhs` env. The FHS env
# carries every system library wxPython's prebuilt Linux wheel needs so
# this works on any NixOS host without distro-specific tweaks.

let
  reqs = ../requirements.txt;
  reqsHash = builtins.substring 0 12 (builtins.hashFile "sha256" reqs);
  srcDir = ../src;
  iconLarge = ../assets/psychopy-512.png;
  iconMed = ../assets/psychopy-256.png;

  launcher = import ./launcher.nix {
    inherit pkgs reqs reqsHash srcDir;
  };

  psychopyFhs = import ./fhs.nix {
    inherit pkgs;
    runScript = "${launcher}";
  };

  desktopBase = {
    icon = "psychopy";
    terminal = false;
    type = "Application";
    categories = [
      "Science"
      "Education"
    ];
    keywords = [
      "psychology"
      "experiment"
      "psychophysics"
      "neuroscience"
      "wxPython"
    ];
  };
in
stdenvNoCC.mkDerivation {
  pname = "psychopy";
  version = "2026.1.3";

  # No upstream `src` to unpack — we generate everything from the FHS env
  # and the icons in this repo.
  dontUnpack = true;

  nativeBuildInputs = [ copyDesktopItems ];

  desktopItems = [
    (makeDesktopItem (
      desktopBase
      // {
        name = "PsychoPy";
        desktopName = "PsychoPy";
        comment = "Visual experiment design and runtime for psychology research";
        exec = "psychopy";
      }
    ))
    (makeDesktopItem (
      desktopBase
      // {
        name = "PsychoPy-Builder";
        desktopName = "PsychoPy Builder";
        comment = "Design PsychoPy experiments visually";
        exec = "psychopy-builder %F";
        mimeTypes = [ "application/x-psyexp" ];
        categories = desktopBase.categories ++ [ "Development" ];
      }
    ))
    (makeDesktopItem (
      desktopBase
      // {
        name = "PsychoPy-Coder";
        desktopName = "PsychoPy Coder";
        comment = "Edit and run PsychoPy Python scripts";
        exec = "psychopy-coder %F";
        categories = desktopBase.categories ++ [ "Development" ];
      }
    ))
  ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin

    install_wrapper() {
      local subcmd=$1
      local binname=$2
      cat > "$out/bin/$binname" <<EOF
    #!${pkgs.runtimeShell}
    exec ${psychopyFhs}/bin/psychopy-fhs $subcmd "\$@"
    EOF
      chmod 0555 "$out/bin/$binname"
    }

    install_wrapper default          psychopy
    install_wrapper builder          psychopy-builder
    install_wrapper coder            psychopy-coder
    install_wrapper run              psychopy-run
    install_wrapper hardware-report  psychopy-hardware-report
    install_wrapper smoketest        psychopy-smoketest
    install_wrapper shell            psychopy-shell

    # Icons: hicolor at the two sizes PsychoPy ships, plus the legacy
    # /share/pixmaps fallback (read by older theme stacks).
    install -Dm0644 ${iconMed}   $out/share/icons/hicolor/256x256/apps/psychopy.png
    install -Dm0644 ${iconLarge} $out/share/icons/hicolor/512x512/apps/psychopy.png
    install -Dm0644 ${iconMed}   $out/share/pixmaps/psychopy.png

    runHook postInstall
  '';

  passthru = {
    fhs = psychopyFhs;
    inherit launcher;
  };

  meta = {
    description = "PsychoPy fleet runner — reliable nix-managed launcher (PsychoPy 2026.1.3)";
    homepage = "https://github.com/abcsds/Psychopy-NixOS";
    license = lib.licenses.gpl3Plus;
    platforms = lib.platforms.linux;
    mainProgram = "psychopy";
  };
}
