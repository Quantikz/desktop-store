#!/usr/bin/env python3
"""Build a portable Windows folder: embedded Python + PySide6 + this app."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "DesktopStore"
ZIP_PATH = ROOT / "dist" / "DesktopStore-Windows.zip"
PYTHON_URL = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip"
GET_PIP = "https://bootstrap.pypa.io/get-pip.py"


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {url}")
    with urlopen(url) as src, dest.open("wb") as out:
        shutil.copyfileobj(src, out)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    py_zip = ROOT / "dist" / "python-embed.zip"
    if not py_zip.exists():
        download(PYTHON_URL, py_zip)
    with zipfile.ZipFile(py_zip) as zf:
        zf.extractall(OUT / "python")

    pth = next((OUT / "python").glob("python*._pth"))
    pth.write_text("python312.zip\n.\nLib\\site-packages\nimport site\n", encoding="utf-8")

    import subprocess
    import sys

    wheels = ROOT / "dist" / "wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "PySide6_Essentials",
            "shiboken6",
            "Pillow",
            "-d",
            str(wheels),
            "--platform",
            "win_amd64",
            "--python-version",
            "312",
            "--only-binary=:all:",
        ]
    )
    site = OUT / "python" / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    for wheel in wheels.glob("*.whl"):
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(site)

    dest_pkg = site / "desktop_store"
    if dest_pkg.exists():
        shutil.rmtree(dest_pkg)
    shutil.copytree(ROOT / "desktop_store", dest_pkg)
    shutil.copy2(ROOT / "HOW-TO-INSTALL.txt", OUT / "HOW-TO-INSTALL.txt")
    (OUT / "Start Desktop Store.bat").write_text(
        "@echo off\r\n"
        "cd /d \"%~dp0\"\r\n"
        "start \"\" \"%~dp0python\\pythonw.exe\" -m desktop_store\r\n",
        encoding="utf-8",
    )
    (OUT / "Start Desktop Store.vbs").write_text(
        'Set sh = CreateObject("Wscript.Shell")\r\n'
        'sh.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)\r\n'
        'sh.Run "python\\pythonw.exe -m desktop_store", 0, False\r\n',
        encoding="utf-8",
    )
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    shutil.make_archive(str(ZIP_PATH.with_suffix("")), "zip", OUT.parent, OUT.name)
    print(f"wrote {ZIP_PATH} ({ZIP_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
