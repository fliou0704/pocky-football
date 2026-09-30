"""Generate the selected football league's site data."""

import argparse
import sys

from football_exporter import generate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", required=True, help="League slug from leagues.json")
    args = parser.parse_args()
    try:
        destination = generate(args.league)
    except Exception as exc:
        # ESPN/network exceptions can include request details; never echo them.
        print(f"Generation failed ({type(exc).__name__}). Check configuration, access, and ESPN availability.", file=sys.stderr)
        return 1
    print(f"Generated {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
