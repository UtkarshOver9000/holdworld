"""Download the real call-centre data (Technion SEE Lab, 'Anonymous Bank', 1999).

Terms (from the dataset's documentation): "The data is free for use. If used,
please notify Avi Mandelbaum ... and do acknowledge the data source in any of
your work." The raw files are not redistributed in this repository.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from .anonbank import RAW_DIR, URL


def fetch() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rar = RAW_DIR / "AnonymousBank.rar"
    if not rar.exists():
        print(f"downloading {URL} (10.6 MB)")
        urllib.request.urlretrieve(URL, rar)
    if any(RAW_DIR.glob("*1999.txt")):
        print("already extracted")
        return
    # bsdtar (Windows 10+ tar.exe, macOS tar) and 7z/unrar can read RAR archives
    for cmd in (["tar", "-xf", str(rar)], ["bsdtar", "-xf", str(rar)], ["7z", "x", "-y", str(rar)],
                ["unrar", "x", "-o+", str(rar)]):
        exe = shutil.which(cmd[0])
        if exe is None:
            continue
        r = subprocess.run([exe] + cmd[1:], cwd=RAW_DIR, capture_output=True)
        if r.returncode == 0 and any(RAW_DIR.glob("*1999.txt")):
            print(f"extracted with {cmd[0]}")
            return
    if sys.platform == "win32" and Path(r"C:\Windows\System32\tar.exe").exists():
        subprocess.run([r"C:\Windows\System32\tar.exe", "-xf", str(rar)], cwd=RAW_DIR, check=True)
        print("extracted with Windows tar")
        return
    raise SystemExit("Could not extract the RAR archive: install bsdtar, 7z or unrar and run again.")
