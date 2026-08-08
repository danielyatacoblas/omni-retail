"""Backend OMNI Retail. Fuerza UTF-8 en stdout/stderr para consolas Windows
(cp1252) y así evitar UnicodeEncodeError con acentos/emoji en los logs."""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass
