from importlib import resources
from pathlib import Path

from led_matrix.common.alpine import LBU_PATH

ANIMATION_RESOURCES_DIR: Path
if LBU_PATH is not None:
    # on Alpine Linux save the resources on the persistent storage
    ANIMATION_RESOURCES_DIR = (LBU_PATH / "led-matrix" / "animation_res").resolve()
else:
    with resources.as_file(resources.files("led_matrix.animations")) as ANIMATION_RESOURCES_DIR:
        ANIMATION_RESOURCES_DIR = (ANIMATION_RESOURCES_DIR / "res").resolve()
# mkdir -p
ANIMATION_RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
