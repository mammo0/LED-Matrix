import builtins
import functools
import os
import sys
from importlib import resources
from io import IOBase
from os import PathLike
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, cast

from led_matrix.common.alpine import (IS_ALPINE_LINUX, LBU_PATH, AlpineLBU,
                                      alpine_lbu_commit_d)

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

            # execute the wrapped method
            r: R = func(*args, **kwargs)

            if not writing_requested:
                # we can exit here if the file is opened just for reading
                return r

            # save the close() method of the IO stream object
            r_close: Callable[[], None]  = r.close

            # wrapper method for the close() method
            @functools.wraps(r_close)
            def c_wrapper() -> None:
                if is_lbu_path:
                    # disable wirting on the LBU directory again
                    alpine_lbu.remount_ro()
                else:
                    # this normally means that the config file was altered
                    # use 'lbu commit -d' to save the /etc directory
                    alpine_lbu_commit_d()

                # now finally close the IO stream
                r_close()

            # replace the close() method with the wrapper method
            r.close = c_wrapper

            # before doing anything with the file, enable writing on the LBU directory
            if is_lbu_path:
                alpine_lbu.remount_rw()

            return r

        return wrapper


    builtins.open = alpine_open(builtins.open)


if IS_ALPINE_LINUX:
    # the 'alpine_site-packages' directory is part of the Alpine package
    # it contains all site-packages that have no own Alpine package
    apline_site_packages: Path = STATIC_RESOURCES_DIR / "alpine_site-packages"

    # add it to the PYTHONPATH
    sys.path.append(str(apline_site_packages))

    # patch open() method
    _patch_open_function()
