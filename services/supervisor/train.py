import argparse
import json

from services.supervisor.model import train
from services.supervisor.store import connect, ingest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    args = parser.parse_args()
    with connect() as db:
        ingest(db)
        print(json.dumps(train(db, args.start, args.end), indent=2))
