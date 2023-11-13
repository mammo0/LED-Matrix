import sys
from pathlib import Path

from led_matrix.common import RESOURCES_DIR
from led_matrix.common.alpine import is_alpine_linux

if is_alpine_linux():
    # the 'alpine_site-packages' directory is part of the Alpine package
    # it contains all site-packages that have no own Alpine package
    apline_site_packages: Path = RESOURCES_DIR / "alpine_site-packages"

    # add it to the PYTHONPATH
    sys.path.append(str(apline_site_packages))
