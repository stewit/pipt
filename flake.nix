{
    description = "Pipt is a small (KISS) Bash-based convenience wrapper around uv / pip-tools providing deterministic venv handling for Python application development.";

    # Selected nixpkgs branch, something like
    #   "nixpkgs/nixos-unstable"
    # or 
    #   "nixpkgs/nixos-23.11"
    inputs.nixpkgs-selected.url = "nixpkgs/nixos-26.05";

    inputs.flake-utils.url = "github:numtide/flake-utils";
    
    nixConfig.bash-prompt-suffix = "(nix-develop)";
    
    outputs = { self, nixpkgs-selected, flake-utils }:
        flake-utils.lib.eachDefaultSystem
        (system:
            let
                pkgs = import nixpkgs-selected { 
                    inherit system; 
                    config= {
                        # allowUnfree = true;
                    };
                };

                app_command_name = "pipt";

                runtime_dependencies = with pkgs; [coreutils];

                # symlink join the runtime dependencies. This later allows
                # to provide them to the script via modifying PATH by adding
                # only a single path
                symlink_joined_runtime_cli_tools = pkgs.symlinkJoin {
                    name = "command_line_tools_used_in_" + app_command_name;
                    paths = runtime_dependencies;
                };

                pipt_script_wrapped = (pkgs.writeScriptBin 
                    app_command_name (builtins.readFile ./pipt)).overrideAttrs(old: {

                        # this patches/wraps the script to 
                        # * point to the bash from pkgs in its shebang
                        # * prefix PATH to point to the runtime dependencies
                        #
                        # Note: Since pipt relies on accessing a "possibly-nix-externally"
                        # instaled python, we only prefix and do not set the path here!

                        buildCommand = ''
                            ${old.buildCommand}

                            # patch shebang
                            patchShebangs $out

                            # make wrapProgram available
                            source ${pkgs.makeWrapper}/nix-support/setup-hook

                            # prefix PATH with runtime dependencies
                            wrapProgram $out/bin/${app_command_name} --prefix PATH : ${symlink_joined_runtime_cli_tools}/bin

                        ''; 
                });            
            
            in
            rec {
                # run
                #     nix develop -i
                # to get an isolated dev shell which includes a python installation
                # with home directory set to ./testhome. Then run
                #     ./pipt ...
                # for development testing: It will store the venv in testhome.
                #
                # The shell also provides the nix-wrapped script as the plain
                # command
                #     pipt ...
                # Note the difference: `pipt` is the built derivation and thus a
                # snapshot taken when the shell was entered, while `./pipt` is
                # the live working copy. Use `./pipt` while editing the script.
                devShell = pkgs.mkShell {
                    buildInputs = runtime_dependencies ++ [
                        pipt_script_wrapped
                        pkgs.python314
                        pkgs.bashInteractive
                    ];
                    shellHook = ''
                        # Absolute, so that it survives cd'ing into
                        # subdirectories like ./tests. With a relative path
                        # pipt's `-d "$HOME"` check fails there and the venv
                        # path degrades to /venv.
                        export HOME="$PWD/testhome"
                        mkdir -p "$HOME"

                        # tests/conftest.py falls back to /usr/bin/python3.14,
                        # which does not exist inside the isolated shell
                        export FULL_PYTHON_PATH="${pkgs.python314}/bin/python3.14"
                    '';
                };

                defaultPackage = packages.app_script;
                packages.app_script = pipt_script_wrapped;
            }
        );
}