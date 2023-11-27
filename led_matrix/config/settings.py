from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Any

import tzlocal
from astral import LocationInfo
from astral.geocoder import GroupInfo, database, lookup, lookup_in_group
from astral.sun import sun

from led_matrix.config.types import (Hardware, LEDColorType, LEDOrientation,
                                     LEDOrigin, LEDWireMode)


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

    tpm2net_server: bool = False

    # this is required for the variable settings (see __setattr__ method)
    __initialized: bool = field(default=False, init=False, repr=False, hash=False, compare=False)

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
        self.__brightness: int

        self.refresh_variable_settings()

        # mark the class as initialized
        self.__initialized = True

    def refresh_variable_settings(self) -> None:
        self.__calc_sunset_sunrise()
        self.__calc_brightness()

        self.__num_of_pxels: int = self.display_width * self.display_height

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

    def __setattr__(self, name: str, val: Any) -> None:
        super().__setattr__(name, val)

        # recalculate variable settings
        if (
            # only if the class is initialized
            self.__initialized and
            # and the variable settings are affected
            name in ("day_brightness", "night_brightness", "display_width", "display_height")
        ):
            self.refresh_variable_settings()

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
