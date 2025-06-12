# Bundled htutil package with ht binary included (wrapper approach)
{ inputs, pkgs, ... }:

let
  inherit (pkgs.stdenv.hostPlatform) system;
  
  # Get the ht package from the flake input
  htPackage = inputs.ht.packages.${system}.ht;
  
  # Get the base htutil package
  htutilBase = import ./htutil-dist-simple.nix { inherit inputs pkgs; };
  
  # Create a wrapper that includes ht and supports HTUTIL_HT_BIN
  htutilBundled = pkgs.symlinkJoin {
    name = "htutil-bundled-${htutilBase.version}";
    paths = [ htutilBase ];
    buildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      # Remove the original htutil binary
      rm $out/bin/htutil
      
      # Create a new wrapper that handles ht binary location
      makeWrapper ${htutilBase}/bin/htutil $out/bin/htutil \
        --run 'if [ -n "$HTUTIL_HT_BIN" ] && [ -x "$HTUTIL_HT_BIN" ]; then export PATH="$(dirname "$HTUTIL_HT_BIN"):$PATH"; fi' \
        --prefix PATH : ${htPackage}/bin \
        --set-default HTUTIL_BUNDLED_HT ${htPackage}/bin/ht
    '';
    
    meta = htutilBase.meta // {
      description = "A python wrapper around ht (with ht bundled, respects HTUTIL_HT_BIN env var)";
    };
  };
  
in
htutilBundled
