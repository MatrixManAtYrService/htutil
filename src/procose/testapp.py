"""
A test script that writes to stdout and stderr with delays.

This is used to test the procose command-line tool.
"""
import sys
import time

def main():
    """Write alternating output to stdout and stderr with delays."""
    try:
        # Ensure stderr is unbuffered
        sys.stderr = open(sys.stderr.fileno(), mode='w', buffering=1)
        
        print("Starting test output", flush=True)
        for i in range(1, 6):  # Generate 5 outputs
            # Write to stdout
            print(f"foo {i}", flush=True)
            
            # Write to stderr for the 2nd and 4th iterations
            if i == 2 or i == 4:
                print(f"bar {i}", file=sys.stderr, flush=True)
                sys.stderr.flush()  # Extra flush to be sure
            
            # Wait for 1 second before the next output
            time.sleep(1)
            
        print("Test completed successfully", flush=True)
        return 0
    except Exception as e:
        print(f"Error in testapp: {str(e)}", file=sys.stderr, flush=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())

