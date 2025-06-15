# Main lib entry point - combines all lib modules
{ inputs, ... }:
{
  inherit inputs;

  htutil-lib =
    pkgs:
    let
      # Import all the separate lib modules
      checks = import ./checks.nix { inherit inputs; } pkgs;
      pypkg = import ./pypkg.nix { inherit inputs; } pkgs;
      testcfg = import ./testcfg.nix { inherit inputs; } pkgs;

    in
    # Combine all modules into a single attribute set
    checks // pypkg // testcfg // {
      # Expose checkDefs as a nested attribute for backward compatibility
      checkDefs = checks;
    };

} 