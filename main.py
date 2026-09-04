"""Railway/Railpack entry point — runs the thavorn-fb-mcp server."""

import runpy
from pathlib import Path

SERVER_PATH = Path(__file__).parent / "thavorn-fb-mcp" / "server.py"

if __name__ == "__main__":
    runpy.run_path(str(SERVER_PATH), run_name="__main__")
