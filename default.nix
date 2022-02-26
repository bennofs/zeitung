{ stdenv, lib, makeWrapper, python3, firefox, geckodriver, rmapi, rclone }:

let
  pyenv = python3.withPackages (p: [geckodriver p.selenium p.requests]);
in stdenv.mkDerivation {
  name = "zeitung-0.1";
  src = ./.;
  buildInputs = [ pyenv makeWrapper geckodriver rmapi rclone ];
  installPhase = ''
    mkdir -p $out/bin

    cp "$src"/*.py "$out/bin"
    cp "$src"/*.sh "$out/bin"

    patchShebangs "$out/bin"
    for script in "$out/bin/"*.py; do
      wrapProgram "$script" \
        --prefix "PATH" : "${lib.makeBinPath [geckodriver firefox]}"
    done

    for script in "$out/bin/"*.sh; do
      wrapProgram "$script" \
        --prefix "PATH" : "$out/bin:${lib.makeBinPath [rmapi rclone]}"
    done
  '';
}
