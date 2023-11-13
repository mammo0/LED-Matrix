from argparse import ArgumentParser, Namespace
from pathlib import Path
import sys

from led_matrix.main import MainController


def run() -> None:
    # cli parser
    parser: ArgumentParser = ArgumentParser(description="LED-Matrix main control application.")
    parser.add_argument("config_file", type=Path,
                        metavar="config-file",
                        help="The path of the configuration file.")

    # get config path
    args: Namespace = parser.parse_args(sys.argv[1:])

    # load the main application
    app: MainController = MainController(args.config_file)
    app.mainloop()
