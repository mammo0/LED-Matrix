from typing import Final


class _Meta:
    SECTION_NAME: str


class _MainSettingsMeta(_Meta):
    SECTION_NAME = "MAIN"

    HARDWARE: Final[str] = "Hardware"

    DISPLAY_WITH: Final[str] = "DisplayWidth"
    DISPLAY_HEIGHT: Final[str] = "DisplayHeight"

    DAY_BRIGHTNESS: Final[str] = "DayBrightness"
    NIGHT_BRIGHTNESS: Final[str] = "NightBrightness"

    HTTP_SERVER: Final[str] = "HttpServer"
    HTTP_SERVER_PORT: Final[str] = "HttpServerPort"
    HTTP_SERVER_LISTEN_IP: Final[str] = "HttpServerListenIP"

    REST_SERVER: Final[str] = "RestServer"
    REST_SERVER_PORT: Final[str] = "RestServerPort"
    REST_SERVER_LISTEN_IP: Final[str] = "RestServerListenIP"

    TPM2NET_SERVER: Final[str] = "TPM2NetServer"


class _DefaultAnimationMeta(_Meta):
    SECTION_NAME = "DEFAULTANIMATION"

    ANIMATION: Final[str] = "Animation"
    VARIANT: Final[str] = "Variant"
    PARAMETER: Final[str] = "Parameter"
    REPEAT: Final[str] = "Repeat"


class _APA102Meta(_Meta):
    SECTION_NAME = "APA102"

    COLOR_TYPE: Final[str] = "ColorType"
    WIRE_MODE: Final[str] = "WireMode"
    ORIENTATION: Final[str] = "Orientation"
    ORIGIN: Final[str] = "Origin"


class _ComputerMeta(_Meta):
    SECTION_NAME = "COMPUTER"

    MARGIN: Final[str] = "Margin"
    LED_SIZE: Final[str] = "LEDSize"


class _ScheduledAnimationsMeta(_Meta):
    SECTION_NAME = "SCHEDULEDANIMATIONS"

    SCHEDULE_TABLE: Final[str] = "ScheduleTable"
