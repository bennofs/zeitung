{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let pkgs = nixpkgs.legacyPackages.${system};
      in rec {
        packages = {
          rmapi = pkgs.callPackage ./rmapi.nix {};
          zeitung = pkgs.callPackage ./. { rmapi = packages.rmapi; };
        };
        defaultPackage = packages.zeitung;
        devShell = self.outputs.packages.${system}.zeitung;
      });
}
