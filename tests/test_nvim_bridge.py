#!/usr/bin/env python3
"""Exercise the Lua bridge in real headless Neovim, with a pipe receiver."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def capture(path, exit_after):
    with Path(path).open("a", encoding="utf-8", buffering=1) as output:
        output.write(json.dumps({"capture": "start", "pid": os.getpid(), "argv": sys.argv}) + "\n")
        for line in sys.stdin:
            output.write(json.dumps({"capture": "update", "pid": os.getpid(), "message": json.loads(line)}) + "\n")
            if exit_after:
                print("Deliberate test receiver exit", file=sys.stderr)
                return 7
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture")
    parser.add_argument("--exit-after-update", action="store_true")
    args, _ = parser.parse_known_args()
    if args.capture:
        return capture(args.capture, args.exit_after_update)
    if not shutil.which("nvim"):
        print("Neovim is required for the bridge integration check.", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="md-viewer-nvim-") as temporary:
        # Neovim resolves macOS /var -> /private/var in buffer names.
        directory = Path(temporary).resolve()
        (directory / "saved note.md").write_text("Saved original.\n", encoding="utf-8")
        environment = dict(os.environ)
        environment.update({
            "MD_VIEWER_TEST_DIR": str(directory),
            "MD_VIEWER_TEST_ROOT": str(root),
            "MD_VIEWER_TEST_PYTHON": sys.executable,
            "NVIM_LOG_FILE": str(directory / "nvim.log"),
        })
        with subprocess.Popen(
            ["nvim", "--headless", "-u", "NONE", "-i", "NONE", "-n",
             "-c", "lua dofile(vim.env.MD_VIEWER_TEST_ROOT .. '/tests/nvim_integration.lua')", "-c", "qa!"],
            env=environment, cwd=root, text=True, stdin=subprocess.PIPE,
        ) as process:
            try:
                returncode = process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise
        if returncode:
            return returncode
        assert (directory / "saved note.md").read_text(encoding="utf-8") == "Saved original.\n"
        assert (directory / "reload.md").read_text(encoding="utf-8") == "Reloaded externally.\n"
        print("Neovim bridge integration passed; the original saved note is unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
