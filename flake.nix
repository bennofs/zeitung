{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-24.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in rec {
        packages = {
          zeitung = pkgs.callPackage ./. {};
          # Python environment with necessary packages for the scripts
          pythonEnv = pkgs.python3.withPackages (p: [
            p.selenium
            p.requests
            # geckodriver is also needed directly below for PATH
          ]);
        };
        defaultPackage = packages.zeitung;
        devShell = pkgs.mkShell {
          # Include the Python env, browser, driver, and other tools
          buildInputs = [
            packages.pythonEnv
            pkgs.geckodriver
            pkgs.firefox-esr
            pkgs.rmapi
            pkgs.rclone
            pkgs.makeWrapper # Useful for testing script wrapping
          ];
        };
      });
}
