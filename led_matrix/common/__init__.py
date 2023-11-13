from importlib import resources
from pathlib import Path

RESOURCES_DIR: Path
with resources.as_file(resources.files("led_matrix")) as RESOURCES_DIR:
    RESOURCES_DIR = (RESOURCES_DIR / "resources").resolve()
