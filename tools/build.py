import json
import logging
import sys

from features.util import build_debs, repo_state_hash

if __name__ == "__main__":
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)
    if len(sys.argv) < 2 or not sys.argv[1]:
        print("required arg: series")
        sys.exit(1)
    series = sys.argv[1]
    print(
        json.dumps(
            {"state_hash": repo_state_hash(), "debs": build_debs(series)}
        )
    )
