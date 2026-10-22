#!/usr/bin/env python3
"""Screenshot an HTML file with headless Chrome / Edge / Chromium, with a hard timeout.

  python shot.py page.html out.png [--width 500] [--height 1200] [--browser PATH] [--timeout 30]

Headless browsers sometimes never exit and block the shell. This stops the browser (and its child
processes) after --timeout seconds and tries the next installed browser. Works on Windows, macOS and
Linux. Order: --browser, $ODC_BROWSER, then the usual install locations and PATH.

No third-party dependencies. Python 3.9+.
"""
import argparse
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time

__version__ = '0.1.1'

CANDIDATES = [
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
]
ON_PATH = ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge', 'msedge', 'chrome']


def browsers(explicit=None):
    found = []
    for c in [explicit, os.environ.get('ODC_BROWSER')] + CANDIDATES + [shutil.which(n) for n in ON_PATH]:
        if c and (c in (explicit, os.environ.get('ODC_BROWSER')) or os.path.exists(c)) and c not in found:
            found.append(c)
    return found


def stop(proc):
    """Stop the browser and every child it started."""
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        proc.kill()


def shoot(browser, page, out, width, height, timeout):
    profile = tempfile.mkdtemp(prefix='odc-shot-')  # a fresh profile keeps an open browser window out of it
    cmd = [browser, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--virtual-time-budget=3000',
           f'--user-data-dir={profile}', f'--window-size={width},{height}', f'--screenshot={out}', page]
    kw = {} if os.name == 'nt' else {'start_new_session': True}
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    deadline, last_size, ok = time.monotonic() + timeout, -1, False
    # Some browsers write the PNG and then never exit: accept the file once its size stops changing.
    while time.monotonic() < deadline:
        size = os.path.getsize(out) if os.path.exists(out) else -1
        if size > 0 and size == last_size:
            ok = True
            break
        if proc.poll() is not None:
            ok = os.path.exists(out) and os.path.getsize(out) > 0
            break
        last_size = size
        time.sleep(0.5)
    if proc.poll() is None:
        stop(proc)
    if not ok:
        print(f'{browser}: no screenshot within {timeout}s', file=sys.stderr)
    shutil.rmtree(profile, ignore_errors=True)
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description='Screenshot an HTML file with a headless browser and a timeout.')
    ap.add_argument('page', help='HTML file path or URL (a #fragment is allowed)')
    ap.add_argument('out', help='PNG file to write')
    ap.add_argument('--width', type=int, default=500)
    ap.add_argument('--height', type=int, default=1200)
    ap.add_argument('--browser', help='browser executable to try first')
    ap.add_argument('--timeout', type=int, default=30, help='seconds per browser (default 30)')
    ap.add_argument('--version', action='version', version=__version__)
    a = ap.parse_args(argv)
    page = a.page
    if '://' not in page:
        path, _, frag = page.partition('#')
        page = pathlib.Path(path).resolve().as_uri() + ('#' + frag if frag else '')
    out = str(pathlib.Path(a.out).resolve())
    if os.path.exists(out):
        os.remove(out)
    candidates = browsers(a.browser)
    if not candidates:
        print('error: no Chrome / Edge / Chromium found; pass --browser or set ODC_BROWSER', file=sys.stderr)
        return 2
    for b in candidates:
        if shoot(b, page, out, a.width, a.height, a.timeout):
            print('wrote', out, 'with', b)
            return 0
    print('error: no browser produced a screenshot', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
