"""Entry point for the windowed `wowfish-gui` executable: `wowfish gui`, no console."""

import sys

from wowfish.cli import main

if __name__ == "__main__":
    if "--version" not in sys.argv[1:]:
        sys.argv = [sys.argv[0], "gui", *sys.argv[1:]]
    main()
