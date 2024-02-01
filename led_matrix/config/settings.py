from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv6Address

import tzlocal
from astral import LocationInfo
from astral.geocoder import GroupInfo, database, lookup, lookup_in_group
from astral.sun import sun

from led_matrix.animation import DUMMY_ANIMATION_NAME
from led_matrix.config.types import (ColorTemp, Hardware, LEDColorType,
                                     LEDOrientation, LEDOrigin, LEDWireMode)


@dataclass(kw_only=True)
class MainSettings:
    hardware: Hardware = Hardware.APA102

    display_width: int = 15
    display_height: int = 12

    day_brightness: int = 85
    night_brightness: int = -1

    day_color_temp: ColorTemp = ColorTemp.K_6000
    night_color_temp: ColorTemp = ColorTemp.K_3200

    http_server: bool = True
    http_server_port: int = 8080
    http_server_listen_ip: IPv4Address | IPv6Address = IPv4Address("127.0.0.1")

    tpm2net_server: bool = False

    def __post_init__(self) -> None:
        self.__location: LocationInfo
        region: str
        city: str
        try:
            region, city = tzlocal.get_localzone_name().split("/", maxsplit=1)
        except  ValueError:
            self.__location = LocationInfo()
        else:
            loc: GroupInfo | LocationInfo = lookup(region, database())
            if isinstance(loc, LocationInfo):
                self.__location = loc
            else:
                try:
                    self.__location = lookup_in_group(location=city, group=loc)
                except KeyError:
                    self.__location = LocationInfo()

        self.__sunrise: datetime
        self.__sunset: datetime
        self.refresh_sunset_sunrise()

        self.__num_of_pxels: int = self.display_width * self.display_height

    def refresh_sunset_sunrise(self) -> None:
        s: dict[str, datetime] = sun(self.__location.observer, date=datetime.now().date())
        if s["sunset"] < datetime.now(tz=tzlocal.get_localzone()):
            # calling after sunset, so calculate for the next day
            s = sun(self.__location.observer, date=datetime.now().date() + timedelta(days=1))

        self.__sunrise = s["sunrise"]
        self.__sunset = s["sunset"]

    @property
    def __is_day_time(self) -> bool:
        return (
            self.night_brightness == -1
            or
            self.__sunrise <= datetime.now(tz=tzlocal.get_localzone()) <= self.__sunset
        )

    @property
    def brightness(self) -> int:
        if self.__is_day_time:
            return self.day_brightness

        return self.night_brightness

    @property
    def color_temp(self) -> ColorTemp:
        if self.__is_day_time:
            return self.day_color_temp

        return self.night_color_temp

    @property
    def num_of_pixels(self) -> int:
        return self.__num_of_pxels

    @property
    def sunrise(self) -> datetime:
        return self.__sunrise

    @property
    def sunset(self) -> datetime:
        return self.__sunset


@dataclass(kw_only=True)
class DefaultAnimation:
    animation_name: str = DUMMY_ANIMATION_NAME
    variant_as_str: str = "null"
    parameter_as_json_str: str = "null"
    repeat: int = 0


@dataclass(kw_only=True)
class APA102:
    color_type: LEDColorType = LEDColorType.BGR
    wire_mode: LEDWireMode = LEDWireMode.ZIG_ZAG
    orientation: LEDOrientation = LEDOrientation.HORIZONTALLY
    origin: LEDOrigin = LEDOrigin.TOP_LEFT


@dataclass(kw_only=True)
class Computer:
    margin: int = 5
    led_size: int = 30


@dataclass(kw_only=True)
class ScheduledAnimations:
    schedule_table_json_str: str = "[]"


@dataclass(kw_only=True)
class Settings:
    main: MainSettings = field(default_factory=MainSettings)
    default_animation: DefaultAnimation = field(default_factory=DefaultAnimation)
    apa102: APA102 = field(default_factory=APA102)
    computer: Computer = field(default_factory=Computer)
    scheduled_animations: ScheduledAnimations = field(default_factory=ScheduledAnimations)
