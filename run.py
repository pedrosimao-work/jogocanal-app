"""Run this file in PyCharm to start the website and local update workers."""

import os
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    os.chdir(root)
    if python.exists() and Path(sys.executable).resolve() != python.resolve():
        try:
            raise SystemExit(
                subprocess.call([str(python), "-m", "app.commands.run_local", *sys.argv[1:]])
            )
        except KeyboardInterrupt:
            raise SystemExit(0) from None
    from app.commands.run_local import main

    raise SystemExit(main())
