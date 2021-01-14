import sys


def eprint(self, msg, file=sys.stderr, **kwargs):
        """
        Print a message.
        All kwargs of regular 'print' are supported.
        @param msg: The message to print.
        @param file: The destination IO stream where the message is printed on (Default: stderr).
        """
        print(msg, out=file, **kwargs)
