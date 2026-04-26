{
  description = "PsychoPy fleet runner — reliable nix-managed launcher for the Wanderers";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    {
      nixosModules.psychopy = import ./nix/module.nix;
    }
    // flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        reqs = ./requirements.txt;
        reqsHash = builtins.substring 0 12
          (builtins.hashFile "sha256" reqs);

        srcDir = ./src;

        launcher = import ./nix/launcher.nix {
          inherit pkgs reqs reqsHash srcDir;
        };

        psychopyFhs = import ./nix/fhs.nix {
          inherit pkgs;
          runScript = "${launcher}";
        };

        # Per-subcommand wrapper. The visible binary name shows up in
        # `ps`, error messages, and shells — keep it user-friendly.
        mkApp = subcmd: binName:
          pkgs.writeShellScriptBin binName ''
            exec ${psychopyFhs}/bin/psychopy-fhs ${subcmd} "$@"
          '';

        defaultBin = mkApp "default" "psychopy";
        builderBin = mkApp "builder" "psychopy-builder";
        coderBin = mkApp "coder" "psychopy-coder";
        runBin = mkApp "run" "psychopy-run";
        hwBin = mkApp "hardware-report" "psychopy-hardware-report";
        smoketestBin = mkApp "smoketest" "psychopy-smoketest";
        shellBin = mkApp "shell" "psychopy-shell";

      in
      {
        packages = {
          default = defaultBin;
          psychopy = defaultBin;
          psychopy-builder = builderBin;
          psychopy-coder = coderBin;
          psychopy-run = runBin;
          hardware-report = hwBin;
          fhs = psychopyFhs;
        };

        apps =
          let
            mkAppOut = bin: progName: desc: {
              type = "app";
              program = "${bin}/bin/${progName}";
              meta.description = desc;
            };
          in
          {
            default = mkAppOut defaultBin "psychopy" "PsychoPy starter app picker";
            builder = mkAppOut builderBin "psychopy-builder" "PsychoPy Builder";
            coder = mkAppOut coderBin "psychopy-coder" "PsychoPy Coder";
            run = mkAppOut runBin "psychopy-run" "Run a .psyexp / .py experiment";
            hardware-report = mkAppOut hwBin "psychopy-hardware-report"
              "Generate hardware-capability HTML report for this device";
            # Run manually: `nix run .#smoketest`
            # (Not wired into `nix flake check` — first-run venv install
            # needs network, which the build sandbox doesn't have.)
            smoketest = mkAppOut smoketestBin "psychopy-smoketest"
              "Import psychopy/wx/pylsl and print versions";
            # Bash shell inside the FHS env with the venv on PATH.
            # Useful for debugging "ImportError: lib*.so" issues.
            shell = mkAppOut shellBin "psychopy-shell"
              "Diagnostic bash inside the PsychoPy FHS env";
          };

        devShells.default = pkgs.mkShell {
          packages = [ defaultBin builderBin coderBin runBin hwBin ];
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
            ═══════════════════════════════════════════════════════════════
            EOF
          '';
        };

        formatter = pkgs.nixfmt;
      });
}
