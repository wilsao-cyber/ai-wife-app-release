"""Launcher script that sets cwd to server/ then runs main.py."""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

from main import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn
    from config import config
    uvicorn.run("main:app", host=config.host, port=config.port, reload=config.debug)
