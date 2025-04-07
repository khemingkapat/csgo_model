{
  description = "Nix-based JupyterLab with Python for CSGO Modelling";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };
  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          # Allow insecure packages for development environment only
          config = {
            permittedInsecurePackages = [
              "python-2.7.18.8"
            ];
          };
        };
        python = pkgs.python311;
        # Just include the core packages from Nix
        pythonEnv = python.withPackages (ps: with ps; [
          numpy
          pandas
          matplotlib
          scipy
          nbconvert
          jupyterlab
          ipykernel
          plotly
          seaborn
          scikit-learn
          graphviz
          pip # Include pip for installing problematic packages
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [ jupyter pandoc texlive.combined.scheme-full ];
          buildInputs = [ pythonEnv pkgs.nodejs ];
          shellHook = ''
                        echo "Γëí╞Æ├╢┬║ Activating JupyterLab environment..."
                        export PATH="$pythonEnv/bin:$PATH"
            
                        # Create virtual environment to avoid polluting system
                        if [ ! -d ".venv" ]; then
                          echo "Creating Python virtual environment..."
                          ${pythonEnv}/bin/python -m venv .venv
                        fi
                        source .venv/bin/activate
            
                        # Install packages that are problematic with Nix
                        echo "Installing additional Python packages with pip..."
                        pip install jupyterlab-vim==4.1.4 awpy==2.0.2
            	    export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.zlib}/lib:${pkgs.libffi}/lib:$LD_LIBRARY_PATH
            
                        # Register the kernel
                        python -m ipykernel install --user --name "nix-python" --display-name "Python (Nix)"
                        echo "╬ô┬ú├á Jupyter Kernel Registered: Python (Nix)"
          '';
        };
      }
    );
}
