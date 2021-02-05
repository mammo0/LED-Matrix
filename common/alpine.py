from configparser import ConfigParser, MissingSectionHeaderError
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import sys

from common import eprint


__ETC_DIR = Path("/") / "etc"
__OS_RELEASE_FILE = __ETC_DIR / "os-release"
__ALPINE_LBU_CONF_FILE = __ETC_DIR / "lbu" / "lbu.conf"
__ALPINE_MEDIA_DIR = Path("/") / "media"


def __read_system_config_file(file_path):
    if not file_path.exists():
        return {}
    elif file_path.exists() and not file_path.is_file():
        return {}

    parser = ConfigParser()
    parser.optionxform = str
    with open(file_path, "r") as f:
        try:
            parser.read_file(f)
        except MissingSectionHeaderError:
            f.seek(0)
            parser.read_string(f"[TEMP]\n" + f.read())

    d = {}
    for section in parser.sections():
        d.update(parser.items(section))

    return d


# load the necessary system files
__OS_RELEASE = __read_system_config_file(__OS_RELEASE_FILE)
__ALPINE_LBU_CONF = __read_system_config_file(__ALPINE_LBU_CONF_FILE)


def is_alpine_linux():
    """
    This method checks if the current OS is Alpine Linux.
    @return: True if it's Alpine Linux. False for any other OS.
    """
    if ("NAME" in __OS_RELEASE and
            "Alpine" in __OS_RELEASE["NAME"]):
        return True
    else:
        return False


def alpine_lbu_commit_d():
    if not is_alpine_linux():
        eprint("Not running on Alpine Linux. So 'lbu' is not available.")
        return

    if shutil.which("lbu") is not None:
        lbu_process = subprocess.run(["lbu", "commit", "-d"], stdout=sys.stdout, stderr=sys.stderr)
        if lbu_process.returncode != 0:
            eprint("Failed to commit file changes with 'lbu'! See output above.")
    else:
        eprint("Cannot commit file changes, because 'lbu' tool was not found!")


class alpine_rw():
    """
    Use this context for writing files on an Alpine Linux diskless installation.
    If no such installation is detected, this context will do nothing.
    """
    def __init__(self):
        # load system mount command
        self.__libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        self.__libc.mount.argtypes = (ctypes.c_char_p,  # source
                                      ctypes.c_char_p,  # target
                                      ctypes.c_char_p,  # filesystemtype
                                      ctypes.c_ulong,   # mountflags
                                      ctypes.c_char_p)  # data

    def __is_root(self):
        return os.geteuid() == 0

    def __remount(self, target, ro):
        # define the mount flags
        mountflags = 32  # mount.h: MS_REMOUNT = 32
        if ro:
            mountflags |= 1  # mount.h: MS_RDONLY = 1

        # call mount
        ret = self.__libc.mount("".encode(),  # on remount source is ignored
                                target.encode(),
                                "".encode(),  # on remount filesystemtype is ignored
                                mountflags,
                                "".encode())
        if ret != 0:
            errno = ctypes.get_errno()
            raise OSError(errno, f"Error re-mounting '{target}' {'RO' if ro else 'RW'}: {os.strerror(errno)}")

    def __enter__(self):
        if not is_alpine_linux():
            eprint("Not running on Alpine Linux. So no changes to the filesystem will be made.")
            return

        if "LBU_MEDIA" not in __ALPINE_LBU_CONF:
            eprint("No Alpine Linux diskless installation detected. So no changes to the filesystem will be made.")

        if not self.__is_root():
            raise RuntimeError(
                "To enable disk write access on Alpine Linux in diskless mode root permissions are necessary!"
            )

        self.__mount_target = str(__ALPINE_MEDIA_DIR / __ALPINE_LBU_CONF["LBU_MEDIA"])

        # remount root filesystem rw
        self.__remount(self.__mount_target, ro=False)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "_%s__mount_target" % self.__class__.__name__):
            # remount root filesystem ro
            self.__remount(self.__mount_target, ro=True)
