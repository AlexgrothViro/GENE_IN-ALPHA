#!/usr/bin/env python3
from __future__ import annotations

import argparse

try:
    from .common import load_yaml_config
except ImportError:
    from common import load_yaml_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Read one validated evidence config value")
    parser.add_argument("--config", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()
    value = load_yaml_config(args.config)
    for part in args.key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(args.key)
        value = value[part]
    if isinstance(value, bool):
        print("true" if value else "false")
    elif isinstance(value, (str, int, float)):
        print(value)
    else:
        raise ValueError("requested config key is not scalar")


if __name__ == "__main__":
    main()
