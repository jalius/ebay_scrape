import code
import signal
import sys

"""
Called on SIGINT
"""
def exit_to_repl(*_: None) -> None: 
    # Start the interactive console
    code.interact(local=globals())

def main():
    # Register the signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal.default_int_handler)

    # Your script's main logic goes here
    try:
        while True:
            # Do something
            pass
    except KeyboardInterrupt:
        # This block will not execute because KeyboardInterrupt is caught by the signal handler
        pass

if __name__ == "__main__":
    main()
