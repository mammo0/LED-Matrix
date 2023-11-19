import sys
from importlib import resources
from pathlib import Path

STATIC_RESOURCES_DIR: Path
with resources.as_file(resources.files("led_matrix")) as STATIC_RESOURCES_DIR:
    STATIC_RESOURCES_DIR = (STATIC_RESOURCES_DIR / "resources").resolve()


    # the 'alpine_site-packages' directory is part of the Alpine package
    # it contains all site-packages that have no own Alpine package
    apline_site_packages: Path = STATIC_RESOURCES_DIR / "alpine_site-packages"

    # add it to the PYTHONPATH
    sys.path.append(str(apline_site_packages))
