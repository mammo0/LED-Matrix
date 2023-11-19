import ctypes
import os
import shutil
import subprocess
import sys
from configparser import ConfigParser, MissingSectionHeaderError
from ctypes import CDLL, util
from io import TextIOWrapper
from pathlib import Path
from typing import Final

from led_matrix.common.log import eprint

_ETC_DIR: Final[Path] = Path("/") / "etc"
_OS_RELEASE_FILE: Final[Path] = _ETC_DIR / "os-release"
_ALPINE_LBU_CONF_FILE: Final[Path] = _ETC_DIR / "lbu" / "lbu.conf"
_ALPINE_MEDIA_DIR: Final[Path] = Path("/") / "media"


def _read_system_config_file(file_path: Path) -> dict[str, str]:
    if not file_path.exists():
        return {}
    if file_path.exists() and not file_path.is_file():
        return {}

    parser: ConfigParser = ConfigParser()
    parser.optionxform = lambda optionstr: optionstr

    f: TextIOWrapper
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            parser.read_file(f)
        except MissingSectionHeaderError:
            f.seek(0)
            parser.read_string("[TEMP]\n" + f.read())

    d: dict[str, str] = {}
    for section in parser.sections():
        d.update(parser.items(section))

    return d


# load the necessary system files
_OS_RELEASE: Final[dict[str, str]] = _read_system_config_file(_OS_RELEASE_FILE)
_ALPINE_LBU_CONF: Final[dict[str, str]] = _read_system_config_file(_ALPINE_LBU_CONF_FILE)


# use this variable to check if we are in an Alpine Linux environment
IS_ALPINE_LINUX: bool = ("NAME" in _OS_RELEASE and
                         "Alpine" in _OS_RELEASE["NAME"])


LBU_PATH: Path | None = None
if IS_ALPINE_LINUX and "LBU_MEDIA" in _ALPINE_LBU_CONF:
    LBU_PATH = _ALPINE_MEDIA_DIR / _ALPINE_LBU_CONF["LBU_MEDIA"]


def alpine_lbu_commit_d() -> None:
    if not IS_ALPINE_LINUX:
        eprint("Not running on Alpine Linux. So 'lbu' is not available.")
        return

    if shutil.which("lbu") is not None:
        try:
            subprocess.run(["lbu", "commit", "-d"], stdout=sys.stdout, stderr=sys.stderr, check=True)
        except subprocess.CalledProcessError:
            eprint("Failed to commit file changes with 'lbu'! See output above.")
    else:
        eprint("Cannot commit file changes, because 'lbu' tool was not found!")


class AlpineLBU:
    """
    Use this class for writing files on an Alpine Linux diskless installation.
    If no such installation is detected, this class will do nothing.
    """
    def __init__(self) -> None:
        # load system mount command
        self.__libc: CDLL = ctypes.CDLL(util.find_library("c"), use_errno=True)
        self.__libc.mount.argtypes = (ctypes.c_char_p,  # source
                                      ctypes.c_char_p,  # target
                                      ctypes.c_char_p,  # filesystemtype
                                      ctypes.c_ulong,   # mountflags
                                      ctypes.c_char_p)  # data

        self.__mount_target: str | None = None

    def __is_root(self) -> bool:
        return os.geteuid() == 0

    def __remount(self, target: str, ro: bool) -> None:
        # define the mount flags
        mountflags: int = 32  # mount.h: MS_REMOUNT = 32
        if ro:
            mountflags |= 1  # mount.h: MS_RDONLY = 1

        # call mount
        ret: int = self.__libc.mount("".encode(),  # on remount source is ignored
                                     target.encode(),
                                     "".encode(),  # on remount filesystemtype is ignored
                                     mountflags,
                                     "".encode())
        if ret != 0:
            errno: int = ctypes.get_errno()
            raise OSError(errno, f"Error re-mounting '{target}' {'RO' if ro else 'RW'}: {os.strerror(errno)}")

    def remount_rw(self) -> None:
        if not IS_ALPINE_LINUX:
            eprint("Not running on Alpine Linux. So no changes to the filesystem will be made.")
            return

        if LBU_PATH is None:
            eprint("No Alpine Linux diskless installation detected. So no changes to the filesystem will be made.")
            return

        if not self.__is_root():
            raise RuntimeError(
                "To enable disk write access on Alpine Linux in diskless mode root permissions are necessary!"
            )

        self.__mount_target = str(LBU_PATH)

        # remount root filesystem rw
        self.__remount(self.__mount_target, ro=False)

    def remount_ro(self) -> None:
        if self.__mount_target is not None:
            # remount root filesystem ro
            self.__remount(self.__mount_target, ro=True)
