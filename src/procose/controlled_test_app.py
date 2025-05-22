"""
A controlled test app for testing procose.

This app reads commands from stdin and produces output accordingly,
which makes it useful for testing procose in a controlled way.
"""
import sys
import time

def main():
    """Read commands from stdin and produce output accordingly."""
    try:
        # Write initial output
        print("Test app started", flush=True)
        
        # Command processing loop
        while True:
            # Read a command from stdin
            command = sys.stdin.readline().strip()
            
            # Process the command
            if command == "exit":
                print("Exiting test app", flush=True)
                return 0
            elif command == "stdout":
                print("This is stdout output", flush=True)
            elif command == "stderr":
                print("This is stderr output", file=sys.stderr, flush=True)
            elif command.startswith("echo "):
                # Echo the text after "echo "
                print(command[5:], flush=True)
            elif command.startswith("error "):
                # Print to stderr
                print(command[6:], file=sys.stderr, flush=True)
            elif command == "":
                # Ignore empty lines
                pass
            else:
                print(f"Unknown command: {command}", file=sys.stderr, flush=True)
                
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr, flush=True)
        return 130
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr, flush=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
