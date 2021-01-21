#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys


if __name__ == '__main__':
    # cli parser
    parser = argparse.ArgumentParser(description="Create or Update the configuration file.")
    parser.add_argument("CONFIG_FILE_PATH", type=Path,
                        help="The path of the configuration file.")

    # get config path
    args = parser.parse_args(sys.argv[1:])
    config_file_path = args.CONFIG_FILE_PATH

    if config_file_path.exists() and not config_file_path.is_file():
        raise ValueError("'%s' is not the path of a file!" % str(config_file_path))
    else:
        # sys.path hack for relative import
        path = Path(__file__).parent.parent
        sys.path.append(str(path))

        from common.config import Configuration
        config = Configuration(config_file_path=config_file_path, allow_no_value=True)
        config.save()
