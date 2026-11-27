#!/usr/bin/bash
env PYTHONPATH=. python3 tools/build.py "$@"
rc=$?
notify-send "Build finished!" || true
exit $rc
