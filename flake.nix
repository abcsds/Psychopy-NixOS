{
  description = "PsychoPy fleet runner — reliable nix-managed launcher for the Wanderers";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { self, nixpkgs, flake-utils }:
    {
      # NixOS module: enables `programs.psychopy.enable` system-wide.
      # When toggled on, installs the bundled `psychopy` package (binary +
      # .desktop entries + icons) and adds the rtprio/memlock PAM limits +
      # the `psychopy` group used by PTB for low-latency timing.
      nixosModules.psychopy = import ./nix/module.nix;
    }
    // flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        psychopyApp = pkgs.callPackage ./nix/psychopy-app.nix { };
      in
      {
        packages = {
          default = psychopyApp;
          psychopy = psychopyApp;
          fhs = psychopyApp.passthru.fhs;
        };

        apps =
          let
            mkApp = bin: desc: {
              type = "app";
              program = "${psychopyApp}/bin/${bin}";
              meta.description = desc;
            };
          in
          {
            default = mkApp "psychopy" "PsychoPy starter app picker";
            builder = mkApp "psychopy-builder" "PsychoPy Builder";
            coder = mkApp "psychopy-coder" "PsychoPy Coder";
            run = mkApp "psychopy-run" "Run a .psyexp / .py experiment headlessly";
            hardware-report = mkApp "psychopy-hardware-report"
              "Generate a hardware-capability HTML report for this device";
            # Manual sanity check; not in `nix flake check` because the
            # first-run venv install needs network.
            smoketest = mkApp "psychopy-smoketest"
              "Import psychopy/wx/pylsl and print versions";
            # Bash inside the FHS env with the venv on PATH.
            shell = mkApp "psychopy-shell"
              "Diagnostic bash inside the PsychoPy FHS env";
          };

        devShells.default = pkgs.mkShell {
          packages = [ psychopyApp ];
          shellHook = ''
            cat <<'EOF'
            ═══════════════════════════════════════════════════════════════
             PsychoPy fleet runner — devShell
            ═══════════════════════════════════════════════════════════════
              psychopy                  starter app picker
              psychopy-builder [file]   open Builder
              psychopy-coder   [file]   open Coder
              psychopy-run     <file>   run an experiment
              psychopy-hardware-report  generate hardware HTML
              psychopy-shell            FHS diagnostic shell
            ═══════════════════════════════════════════════════════════════
            EOF
          '';
        };

        formatter = pkgs.nixfmt;
      }
    );
}
