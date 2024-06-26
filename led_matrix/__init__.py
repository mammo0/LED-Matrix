import builtins
import functools
import logging
import os
import sys
from importlib import resources
from io import IOBase
from os import PathLike
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, cast

from led_matrix.common.alpine import (IS_ALPINE_LINUX, LBU_PATH, AlpineLBU,
                                      alpine_lbu_commit_d)
from led_matrix.common.log import LOG

# apply custom handler to apscheduler
logging.getLogger("apscheduler").addHandler(LOG.handler)


STATIC_RESOURCES_DIR: Path
with resources.as_file(resources.files("led_matrix")) as STATIC_RESOURCES_DIR:
    STATIC_RESOURCES_DIR = (STATIC_RESOURCES_DIR / "static_res").resolve()


def _patch_open_function() -> None:
    # this class managees rw access to the LBU directory
    alpine_lbu: AlpineLBU = AlpineLBU()

    P = ParamSpec("P")
    R = TypeVar("R", bound=IOBase)
    def alpine_open(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            file: str | bytes | PathLike
            if len(args) >= 1:
                file = args[0]  # type: ignore
            else:
                file = getattr(kwargs, "file")
            file_obj: PathLike = Path(os.fsdecode(file)).resolve()


            mode: str = getattr(kwargs, "mode", "")
            if not mode and len(args) >= 2:
                mode = cast(str, args[1])

            writing_requested: bool = ("w" in mode or
                                        "x" in mode or
                                        "a" in mode or
                                        "+" in mode)
            is_lbu_path: bool = LBU_PATH in file_obj.parents

            # before doing anything with the file, enable writing on the LBU directory
            if writing_requested and is_lbu_path:
                alpine_lbu.remount_rw()

            # open the file
            r: R = func(*args, **kwargs)

            if not writing_requested:
                # we can exit here if the file is opened just for reading
                return r

            def alpine_close(func: Callable[[], None]) -> Callable[[], None]:
                @functools.wraps(func)
                def wrapper() -> None:
                    # first close the IO stream
                    func()

                    # make the changes persistent
                    if is_lbu_path:
                        # disable writing on the LBU directory again
                        alpine_lbu.remount_ro()
                    else:
                        # this normally means that the config file was altered
                        # use 'lbu commit -d' to save the /etc directory
                        alpine_lbu_commit_d()

                return wrapper

            # wrap the default IO close() method
            r.close = alpine_close(r.close)

            return r

        return wrapper

    # wrap the default open() method
    builtins.open = alpine_open(builtins.open)


def _patch_pathlib() -> None:
    P = ParamSpec("P")
    R = TypeVar("R")
    def alpine_path_write_operation(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # the first argument is self
            path_self: Path = args[0]  # type: ignore

            if LBU_PATH in path_self.parents:
                with AlpineLBU():
                    return func(*args, **kwargs)

            r: R = func(*args, **kwargs)
            alpine_lbu_commit_d()
            return r

        return wrapper

    # pathlib functions that perform write operations
    Path.chmod = alpine_path_write_operation(Path.chmod)
    Path.lchmod = alpine_path_write_operation(Path.lchmod)
    Path.mkdir = alpine_path_write_operation(Path.mkdir)
    Path.rename = alpine_path_write_operation(Path.rename)
    Path.replace = alpine_path_write_operation(Path.replace)
    Path.rmdir = alpine_path_write_operation(Path.rmdir)
    Path.symlink_to = alpine_path_write_operation(Path.symlink_to)
    Path.hardlink_to = alpine_path_write_operation(Path.hardlink_to)
    Path.touch = alpine_path_write_operation(Path.touch)
    Path.unlink = alpine_path_write_operation(Path.unlink)
    Path.write_bytes = alpine_path_write_operation(Path.write_bytes)
    Path.write_text = alpine_path_write_operation(Path.write_text)


if IS_ALPINE_LINUX:
    # the 'alpine_site-packages' directory is part of the Alpine package
    # it contains all site-packages that have no own Alpine package
    apline_site_packages: Path = STATIC_RESOURCES_DIR / "alpine_site-packages"

    # add it to the PYTHONPATH
    sys.path.append(str(apline_site_packages))

    # patch open() method
    _patch_open_function()

    # patch pthlib functions that perform write operations
    _patch_pathlib()
