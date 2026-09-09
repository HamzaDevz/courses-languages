#!/usr/bin/env python3
"""Convertit les fiches de print/ en PDF avec Chrome/Chromium en mode headless.

Optionnel : sans Chromium, il suffit d'ouvrir les fichiers de print/ dans un
navigateur et de faire Ctrl+P → « Enregistrer au format PDF ». La mise en page
A4 est déjà définie dans le CSS d'impression.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRINT = ROOT / "print"
PDF = ROOT / "pdf"

CANDIDATES = [
    "/opt/pw-browsers/chromium",
    "chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def find_chrome() -> str | None:
    for c in CANDIDATES:
        p = shutil.which(c) or (c if Path(c).exists() else None)
        if p:
            return p
    return None


def main() -> None:
    chrome = find_chrome()
    if not chrome:
        sys.exit("Chrome/Chromium introuvable. Ouvrez print/<langue>/cahier-complet.html "
                 "dans un navigateur et utilisez Ctrl+P → Enregistrer en PDF.")
    if not PRINT.exists():
        sys.exit("Lancez d'abord : python3 scripts/build.py")

    for src in sorted(PRINT.rglob("*.html")):
        rel = src.relative_to(PRINT)
        out = PDF / rel.with_suffix(".pdf")
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [chrome, "--headless", "--disable-gpu", "--no-sandbox",
             "--no-pdf-header-footer", f"--print-to-pdf={out}", src.as_uri()],
            check=True, capture_output=True,
        )
        print(f"  {out.relative_to(ROOT)}")

    # Le site liste les PDF disponibles : il faut le regénérer une fois qu'ils existent.
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True,
                   capture_output=True)
    print("\nPDF prêts dans pdf/ et liés depuis le site")


if __name__ == "__main__":
    main()
