#!/usr/bin/bash
env PYTHONPATH=. python3 tools/build.py "$@"
notify-send "Build finished!" || true
