import os
from pathlib import Path
import sys


BASE_DIR = Path(os.path.dirname(os.path.realpath(__file__))).parent
RESOURCES_DIR = BASE_DIR / "resources"
DEFAULT_CONFIG_FILE = BASE_DIR / "config.ini"


def eprint(msg, file=sys.stderr, **kwargs):
        """
        Print a message.
        All kwargs of regular 'print' are supported.
        @param msg: The message to print.
        @param file: The destination IO stream where the message is printed on (Default: stderr).
        """
        print(msg, file=file, **kwargs)
