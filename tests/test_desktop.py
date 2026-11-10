#!/usr/bin/env python3
"""Exercise the real Linux WebKitGTK app and Neovim; requires a desktop session.

Uses WebKitWebDriver directly (the same backend as tauri-driver). All notes,
FIFOs, and editor state are disposable. No user configuration is loaded.
"""

import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zlib

ROOT = Path(__file__).resolve().parents[1]


def wait_for(check, description, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.1)
    raise AssertionError(f"Timed out: {description}")


def stop(process):
    if process is not None and process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def png_pixels(encoded):
    """Compare decoded PNG scanline data, ignoring timestamp/metadata chunks."""
    data = base64.b64decode(encoded)
    assert data.startswith(b'\x89PNG\r\n\x1a\n')
    cursor = 8
    chunks = []
    while cursor < len(data):
        size = struct.unpack_from('>I', data, cursor)[0]
        if data[cursor + 4:cursor + 8] == b'IDAT':
            chunks.append(data[cursor + 8:cursor + 8 + size])
        cursor += size + 12
    return zlib.decompress(b''.join(chunks))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, default=ROOT / "target/debug/md-viewer")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts/desktop")
    args = parser.parse_args()
    binary = args.binary.resolve()
    assert binary.is_file(), f"Build the application first: {binary}"
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with socket.socket() as port_socket:
        port_socket.bind(("127.0.0.1", 0))
        port = port_socket.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    session = None
    driver = None
    editor = None
    checks = []

    def request(method, route, data=None):
        payload = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(base + route, payload,
                                     {"Content-Type": "application/json"}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                result = json.load(response)
        except urllib.error.HTTPError as error:
            raise AssertionError(error.read().decode()) from error
        value = result.get("value")
        if isinstance(value, dict) and "error" in value:
            raise AssertionError(value)
        return value

    def js(source):
        return request("POST", f"/session/{session}/execute/sync", {"script": source, "args": []})

    def open_app(executable, arguments):
        nonlocal session
        result = request("POST", "/session", {"capabilities": {"alwaysMatch": {
            "browserName": "wry", "webkitgtk:browserOptions": {
                "binary": str(executable), "args": arguments,
            },
        }}})
        session = result["sessionId"]

    def close_app():
        nonlocal session
        if session:
            request("DELETE", f"/session/{session}")
            session = None

    def screenshot(name):
        # FontFaceSet can report loaded before the next frame paints new glyphs.
        request("POST", f"/session/{session}/execute/async", {"script": """
            const done = arguments[arguments.length - 1];
            Promise.all([document.fonts.load('16px KaTeX_Main'), document.fonts.load('italic 16px KaTeX_Math')])
              .then(() => requestAnimationFrame(() => requestAnimationFrame(() => done(true))));
        """, "args": []})
        encoded = request("GET", f"/session/{session}/screenshot")
        (args.artifacts / name).write_bytes(base64.b64decode(encoded))

    with tempfile.TemporaryDirectory(prefix="md-viewer-native-") as temporary:
        work = Path(temporary)
        with (args.artifacts / "webdriver.log").open("w") as log:
            try:
                environment = dict(os.environ, TAURI_WEBVIEW_AUTOMATION="true")
                driver = subprocess.Popen(["WebKitWebDriver", f"--port={port}", "--host=127.0.0.1"],
                                          env=environment, stdout=log, stderr=log, start_new_session=True)

                def ready():
                    try:
                        return request("GET", "/status")["ready"]
                    except (OSError, urllib.error.URLError):
                        return False

                wait_for(ready, "WebKitWebDriver startup")
                note = work / "notes.md"
                note.write_text((ROOT / "examples/notes.md").read_text(), encoding="utf-8")
                open_app(binary, [str(note)])
                wait_for(lambda: js("return document.querySelectorAll('#document .katex').length >= 4"),
                         "actual KaTeX rendered in WebKitGTK")
                assert js("return !document.querySelector('#error').textContent")
                assert js("return getComputedStyle(document.body).backgroundColor") == "rgba(24, 19, 31, 0.86)"
                assert js("return document.querySelector('.katex-html').getBoundingClientRect().width > 0")
                wait_for(lambda: js("return document.fonts.status === 'loaded'"), "bundled math fonts")
                assert js("return document.fonts.check('16px KaTeX_Main')")
                (args.artifacts / "math-render-state.json").write_text(json.dumps(js("""
                    return [...document.querySelectorAll('.math-inline:first-of-type .katex-html span')].slice(0,24).map(e => {
                      const s=getComputedStyle(e),r=e.getBoundingClientRect();
                      return {text:e.textContent,cls:e.className,color:s.color,font:s.font,visibility:s.visibility,
                        opacity:s.opacity,w:r.width,h:r.height,html:e.outerHTML};
                    });
                """), indent=2))
                screenshot("moonlit.png")
                # E=mc² contains only glyphs, unlike a fraction's drawn rule.
                # Compare its actual pixels against transparent text so a blank
                # custom-font paint cannot pass merely because DOM/boxes exist.
                element = request("POST", f"/session/{session}/element", {
                    "using": "css selector", "value": "#document .math-inline"})
                element_id = element["element-6066-11e4-a52e-4f735466cecf"]
                route = f"/session/{session}/element/{element_id}/screenshot"
                glyphs = png_pixels(request("GET", route))
                js("document.querySelector('#document .math-inline').style.color='transparent'; return true")
                hidden_glyphs = png_pixels(request("GET", route))
                js("document.querySelector('#document .math-inline').style.removeProperty('color'); return true")
                assert sum(a != b for a, b in zip(glyphs, hidden_glyphs)) > 20, "Formula glyphs must actually paint"
                checks.append("Native KaTeX layout, local fonts, and Moonlit alpha .86")

                for theme, color in [("graphite", "rgb(24, 27, 32)"), ("paper", "rgb(247, 243, 236)")]:
                    js(f"const e=document.querySelector('#theme');e.value='{theme}';e.dispatchEvent(new Event('change'));return true")
                    wait_for(lambda: js("return getComputedStyle(document.body).backgroundColor") == color,
                             f"{theme} theme command and render")
                    screenshot(theme + ".png")
                checks.append("All three theme presets through real Tauri commands")

                replacement = work / "replacement.md"
                replacement.write_text("# Saved replacement\n\n$x^2$\n", encoding="utf-8")
                replacement.replace(note)
                wait_for(lambda: js("return document.querySelector('#document').textContent.includes('Saved replacement')"),
                         "atomic file replacement")
                note.unlink()
                wait_for(lambda: js("return !!document.querySelector('#error').textContent"), "missing-file error")
                note.write_text("# Recovered\n\n$x^2$\n", encoding="utf-8")
                wait_for(lambda: js("return document.querySelector('#document').textContent.includes('Recovered') && !document.querySelector('#error').textContent"),
                         "file recovery")
                checks.append("Saved-file replacement, missing-file error, and recovery")
                close_app()

                # Real Neovim buffer -> bundled Lua -> pipe relay -> Rust -> native
                # WebView. The relay connects WebDriver's app launch to Lua's pipe.
                fifo = work / "updates.fifo"
                os.mkfifo(fifo)
                launcher = work / "viewer"
                launcher.write_text(f"#!/bin/sh\nexec {shlex.quote(str(binary))} --stdin < {shlex.quote(str(fifo))}\n")
                launcher.chmod(0o700)
                relay = work / "relay.py"
                relay.write_text("import sys\nwith open(" + repr(str(fifo)) + ", 'w') as out:\n"
                                 "    for line in sys.stdin:\n        out.write(line)\n        out.flush()\n")
                original = "# On disk\n\n$E=mc^2$\n"
                note.write_text(original, encoding="utf-8")
                editor_socket = work / "nvim.sock"
                init = work / "init.lua"
                init.write_text(
                    "vim.opt.runtimepath:append(" + json.dumps(str(ROOT / "nvim")) + ")\n"
                    "require('md_viewer').setup({command={" + json.dumps(sys.executable) + ","
                    + json.dumps(str(relay)) + "},debounce_ms=20})\n"
                    "vim.bo.filetype='markdown'\nvim.cmd('MdViewerStart')\n", encoding="utf-8")
                editor = subprocess.Popen(["nvim", "--headless", "-u", "NONE", "-n", "--listen",
                                           str(editor_socket), str(note), "+lua dofile(" + json.dumps(str(init)) + ")"],
                                          stdout=log, stderr=log, start_new_session=True)
                open_app(launcher, [])
                wait_for(lambda: js("return document.querySelector('#document').textContent.includes('On disk')"),
                         "initial editor snapshot")

                def edit(lines, prelude=""):
                    action = work / "edit.lua"
                    action.write_text(prelude + "vim.api.nvim_buf_set_lines(0,0,-1,false,"
                                      + "{" + ",".join(json.dumps(line, ensure_ascii=False) for line in lines)
                                      + "})\n", encoding="utf-8")
                    expression = "execute('lua dofile(" + json.dumps(str(action)) + ")')"
                    subprocess.run(["nvim", "--server", str(editor_socket), "--remote-expr", expression],
                                   check=True, capture_output=True, timeout=10)

                edit(["# 未保存 · Native preview", "", "实时公式 $\\frac{1}{2} + x^2$。"],
                     "vim.cmd('enew')\nvim.cmd('setfiletype markdown')\n")
                wait_for(lambda: js("return document.querySelector('#document').textContent.includes('未保存') && document.querySelector('#status').textContent.includes('unsaved') && document.querySelectorAll('#document .katex').length===1"),
                         "unsaved Unicode buffer and native formula rendering")
                assert note.read_text(encoding="utf-8") == original
                assert js("return document.querySelector('#document-title').textContent === '[No Name]'")
                screenshot("neovim-unsaved.png")
                checks.append("Real Neovim unsaved Unicode edits reached Rust and native KaTeX; saved bytes unchanged")

                edit(["# Still readable", "", "$\\frac{$", "", "Other text stays visible."])
                wait_for(lambda: js("return document.querySelector('#document').textContent.includes('Still readable') && document.querySelector('#document').textContent.includes('frac{')"), "incomplete formula source fallback")
                assert js("return document.querySelector('#document').textContent.includes('Other text stays visible')")
                edit(["# Corrected", "", "$\\frac{1}{2}$", "", "<script>window.noteExecuted=true</script>",
                      "", "![remote](https://example.com/no-image.png)", "", "[inert link](https://example.com)"])
                wait_for(lambda: js("return document.querySelector('#document').textContent.includes('Corrected') && !!document.querySelector('#document .katex') && !document.querySelector('#document .katex-error')"),
                         "formula correction")
                assert js("return !window.noteExecuted && !document.querySelector('#document img')")
                assert js("return !document.querySelector('#document a[href]')")
                assert js("return performance.getEntriesByType('resource').every(e => !/^https?:/.test(e.name))")
                checks.append("Incomplete formula recovery, inert raw HTML, and no HTTP resource loads")
                assert note.read_text(encoding="utf-8") == original
                close_app()
            except Exception:
                if session:
                    try:
                        (args.artifacts / "failure.html").write_text(js("return document.documentElement.outerHTML"))
                        screenshot("failure.png")
                    except Exception:
                        pass
                raise
            finally:
                if session:
                    try:
                        close_app()
                    except Exception:
                        pass
                stop(editor)
                stop(driver)
    (args.artifacts / "report.json").write_text(json.dumps({"platform": "Linux WebKitGTK",
                                                          "checks": checks, "macOS": "not tested"}, indent=2) + "\n")
    print("Native desktop checks passed:", *checks, sep="\n- ", flush=True)


if __name__ == "__main__":
    main()
