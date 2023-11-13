from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import cast

from astral import LocationInfo
from astral.geocoder import database, lookup
from astral.sun import sun
import tzlocal

from led_matrix.config.types import (
    Hardware,
    LEDColorType,
    LEDOrientation,
    LEDOrigin,
    LEDWireMode,
)


@dataclass(kw_only=True)
class MainSettings:
    hardware: Hardware = Hardware.APA102

    display_width: int = 15
    display_height: int = 12

    day_brightness: int = 85
    night_brightness: int = -1

    http_server: bool = True
    http_server_port: int = 8080
    http_server_listen_ip: IPv4Address | IPv6Address = IPv4Address("127.0.0.1")

    rest_server: bool = True
    rest_server_port: int = 8081
    rest_server_listen_ip: IPv4Address | IPv6Address = IPv4Address("127.0.0.1")

    tpm2net_server: bool = False

    def __post_init__(self) -> None:
        self.__location: LocationInfo = cast(LocationInfo,
                                             lookup(tzlocal.get_localzone_name().split("/")[1], database()))
        self.__sunrise: datetime
        self.__sunset: datetime
        self.__brightness: int

        self.refresh_variable_settings()

        self.__num_of_pxels: int = self.display_width * self.display_height

    def refresh_variable_settings(self) -> None:
        self.__calc_sunset_sunrise()
        self.__calc_brightness()

    def __calc_sunset_sunrise(self) -> None:
        s: dict[str, datetime] = sun(self.__location.observer, date=datetime.now().date())
        if s["sunset"] < datetime.now(tz=tzlocal.get_localzone()):
            # calling after sunset, so calculate for the next day
            s = sun(self.__location.observer, date=datetime.now().date() + timedelta(days=1))

        self.__sunrise = s["sunrise"]
        self.__sunset = s["sunset"]

    def __calc_brightness(self) -> None:
        if (self.night_brightness == -1 or
                self.__sunrise <= datetime.now(tz=tzlocal.get_localzone()) <= self.__sunset):
            self.__brightness = self.day_brightness
        else:
            self.__brightness = self.night_brightness

    @property
    def brightness(self) -> int:
        return self.__brightness

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
    animation_name: str = "dummy"
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
