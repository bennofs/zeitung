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
          zeitung = pkgs.callPackage ./. {
            rmapi = pkgs.callPackage ./rmapi.nix {};
          };
        };
        defaultPackage = packages.zeitung;
        devShell = self.outputs.packages.${system}.zeitung;
      });
}
