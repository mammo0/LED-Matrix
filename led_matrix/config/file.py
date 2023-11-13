from collections.abc import Generator
from contextlib import contextmanager
from ipaddress import IPv4Address, IPv6Address, ip_address
from logging import Logger
from pathlib import Path
from typing import Any, Final, Literal, TypeVar

from python_ini.ini_file import IniFile
from python_ini.ini_writer import IniWriter

from led_matrix.common.logging import get_logger
from led_matrix.config.meta import (
    _APA102Meta,
    _ComputerMeta,
    _DefaultAnimationMeta,
    _MainSettingsMeta,
    _ScheduledAnimationsMeta,
)
from led_matrix.config.settings import (
    APA102,
    Computer,
    DefaultAnimation,
    MainSettings,
    ScheduledAnimations,
    Settings,
)
from led_matrix.config.types import (
    Hardware,
    LEDColorType,
    LEDOrientation,
    LEDOrigin,
    LEDWireMode,
)


V = TypeVar("V", str, int, bool)


class _ConfigReader:
    VALUE_NOT_FOUND: Final[object] = object()

    def __init__(self, file_path: Path) -> None:
        self.__log: Logger = get_logger(__name__)

        self.__r: IniFile = IniFile()
        self.__r.parse(file_path)
        if self.__r.errors:
            self.__log.error("Config file ERRORS")
            self.__log.error(self.__r.display_errors())
            raise ValueError

        self.__current_section: str | None = None

    @contextmanager
    def __section(self, section: str) -> Generator[None, None, None]:
        # apply the current section
        self.__current_section = section

        # return to execution
        yield

        # reset it
        self.__current_section = None

    def __get_value(self, key: str, target_type: type[V], default_value: V) -> V:
        if self.__current_section is None:
            raise RuntimeError("The __get_value method was not called inside __section context manager.")

        value: Any | list[bool] | Literal[True] | None = self.__r.get_section_values(
            section=self.__current_section,
            key=key,
            default=_ConfigReader.VALUE_NOT_FOUND
        )

        if (
                value is None or
                value == _ConfigReader.VALUE_NOT_FOUND or (
                    target_type != bool and
                    value is True
                ) or
                isinstance(value, list)
            ):
            self.__log.warning("Setting '%s' in section '%s' not found. Using default value '%s'",
                               key, self.__current_section, str(default_value))
            return default_value

        try:
            r_val: V = target_type(value)
        except (ValueError, TypeError) as e:
            self.__log.error("Setting '%s' in section '%s' is invalid.",
                             key, self.__current_section)
            raise e

        return r_val

    def __read_main(self) -> MainSettings:
        with self.__section(_MainSettingsMeta.SECTION_NAME):
            hardware: Hardware = Hardware(self.__get_value(_MainSettingsMeta.HARDWARE,
                                                           target_type=str,
                                                           default_value=MainSettings.hardware.value))
            display_width: int = self.__get_value(_MainSettingsMeta.DISPLAY_WITH,
                                                  target_type=int,
                                                  default_value=MainSettings.display_width)
            display_height: int = self.__get_value(_MainSettingsMeta.DISPLAY_HEIGHT,
                                                   target_type=int,
                                                   default_value=MainSettings.display_height)
            day_brightness: int = self.__get_value(_MainSettingsMeta.DAY_BRIGHTNESS,
                                                   target_type=int,
                                                   default_value=MainSettings.day_brightness)
            night_brightness: int = self.__get_value(_MainSettingsMeta.NIGHT_BRIGHTNESS,
                                                     target_type=int,
                                                     default_value=MainSettings.night_brightness)
            http_server: bool = self.__get_value(_MainSettingsMeta.HTTP_SERVER,
                                                 target_type=bool,
                                                 default_value=MainSettings.http_server)
            http_server_port: int = self.__get_value(_MainSettingsMeta.HTTP_SERVER_PORT,
                                                     target_type=int,
                                                     default_value=MainSettings.http_server_port)
            http_server_listen_ip: IPv4Address | IPv6Address = ip_address(
                self.__get_value(_MainSettingsMeta.HTTP_SERVER_LISTEN_IP,
                                 target_type=str,
                                 default_value=str(MainSettings.http_server_listen_ip))
            )
            tpm2net_server: bool = self.__get_value(_MainSettingsMeta.TPM2NET_SERVER,
                                                    target_type=bool,
                                                    default_value=MainSettings.tpm2net_server)

        return MainSettings(hardware=hardware,
                            display_width=display_width,
                            display_height=display_height,
                            day_brightness=day_brightness,
                            night_brightness=night_brightness,
                            http_server=http_server,
                            http_server_port=http_server_port,
                            http_server_listen_ip=http_server_listen_ip,
                            tpm2net_server=tpm2net_server)

    def __read_default_animation(self) -> DefaultAnimation:
        with self.__section(_DefaultAnimationMeta.SECTION_NAME):
            animation_name: str = self.__get_value(_DefaultAnimationMeta.ANIMATION,
                                                   target_type=str,
                                                   default_value=DefaultAnimation.animation_name)
            variant: str = self.__get_value(_DefaultAnimationMeta.VARIANT,
                                            target_type=str,
                                            default_value=DefaultAnimation.variant_as_str)
            parameter: str = self.__get_value(_DefaultAnimationMeta.PARAMETER,
                                              target_type=str,
                                              default_value=DefaultAnimation.parameter_as_json_str)
            repeat: int = self.__get_value(_DefaultAnimationMeta.REPEAT,
                                           target_type=int,
                                           default_value=DefaultAnimation.repeat)

        return DefaultAnimation(animation_name=animation_name,
                                variant_as_str=variant,
                                parameter_as_json_str=parameter,
                                repeat=repeat)

    def __read_apa102(self) -> APA102:
        with self.__section(_APA102Meta.SECTION_NAME):
            color_type: LEDColorType = LEDColorType(self.__get_value(_APA102Meta.COLOR_TYPE,
                                                                     target_type=int,
                                                                     default_value=APA102.color_type.value))
            wire_mode: LEDWireMode = LEDWireMode(self.__get_value(_APA102Meta.WIRE_MODE,
                                                                  target_type=int,
                                                                  default_value=APA102.wire_mode.value))
            orientation: LEDOrientation = LEDOrientation(self.__get_value(_APA102Meta.ORIENTATION,
                                                                          target_type=int,
                                                                          default_value=APA102.orientation.value))
            origin: LEDOrigin = LEDOrigin(self.__get_value(_APA102Meta.ORIGIN,
                                                           target_type=int,
                                                           default_value=APA102.origin.value))

        return APA102(color_type=color_type,
                      wire_mode=wire_mode,
                      orientation=orientation,
                      origin=origin)


    def __read_computer(self) -> Computer:
        with self.__section(_ComputerMeta.SECTION_NAME):
            margin: int = self.__get_value(_ComputerMeta.MARGIN,
                                           target_type=int,
                                           default_value=Computer.margin)
            led_size: int = self.__get_value(_ComputerMeta.LED_SIZE,
                                             target_type=int,
                                             default_value=Computer.led_size)

        return Computer(margin=margin,
                        led_size=led_size)

    def __read_scheduled_animations(self) -> ScheduledAnimations:
        with self.__section(_ScheduledAnimationsMeta.SECTION_NAME):
            schedule_table: str = self.__get_value(_ScheduledAnimationsMeta.SCHEDULE_TABLE,
                                                   target_type=str,
                                                   default_value=ScheduledAnimations.schedule_table_json_str)

        return ScheduledAnimations(schedule_table_json_str=schedule_table)

    def read(self) -> Settings:
        try:
            main_settings: MainSettings = self.__read_main()
            default_animation: DefaultAnimation = self.__read_default_animation()
            apa102: APA102 = self.__read_apa102()
            computer: Computer = self.__read_computer()
            scheduled_animations: ScheduledAnimations = self.__read_scheduled_animations()
        except ValueError as e:
            self.__log.error(e)
            raise e

        return Settings(main=main_settings,
                        default_animation=default_animation,
                        apa102=apa102,
                        computer=computer,
                        scheduled_animations=scheduled_animations)

class _ConfigWriter:
    def __init__(self, file_path: Path) -> None:
        self.__log: Logger = get_logger(__name__)

        self.__file_path: Path = file_path

        self.__w: IniWriter = IniWriter()
        self.__w.delimiters(comment="#",  # type: ignore
                                 key="=",      # type: ignore
                                 value=",")    # type: ignore
        self.__w.booleans(true="True",    # type: ignore
                               false="False",  # type: ignore
                               none="None")    # type: ignore

    def __write_main(self, main_config: MainSettings) -> None:
        self.__w.section(name=_MainSettingsMeta.SECTION_NAME)
        self.__w.comment("The display defines where the animations should be showed.")
        self.__w.comment("There are two possible values here:")
        self.__w.comment("    - 'APA102'   [Default]")
        self.__w.comment("      The actual LED hardware addressed via SPI.")
        self.__w.comment("    - 'COMPUTER'")
        self.__w.comment("      This is for developing on a PC. It opens a virtual LED matrix via 'pygame'.")
        self.__w.key(name="Hardware", varg=main_config.hardware.value)

        self.__w.comment()
        self.__w.comment("Set the number of LEDs for width and height of your matrix")
        self.__w.key(name=_MainSettingsMeta.DISPLAY_WITH, varg=main_config.display_width)
        self.__w.key(name=_MainSettingsMeta.DISPLAY_HEIGHT, varg=main_config.display_height)

        self.__w.comment()
        self.__w.comment("Set the brightness in percent [Default: 85]")
        self.__w.comment("Possible values: 0 < = x <= 100")
        self.__w.key(name=_MainSettingsMeta.DAY_BRIGHTNESS, varg=main_config.day_brightness)

        self.__w.comment()
        self.__w.comment("Set a brightness value that gets set on night times [Default: -1]")
        self.__w.comment("Possible values: 0 < = x <= 100")
        self.__w.comment("                -1: disable")
        self.__w.key(name=_MainSettingsMeta.NIGHT_BRIGHTNESS, varg=main_config.night_brightness)

        self.__w.comment()
        self.__w.comment("(De-)Activate the server interfaces that control the matrix.")
        self.__w.comment("Available servers:")
        self.__w.comment("    - HttpServer [Default: true]")
        self.__w.comment("    - TPM2NetServer [Default: false]: UDP 65506")
        self.__w.key(name=_MainSettingsMeta.HTTP_SERVER, varg=main_config.http_server)
        self.__w.comment("The port on which the HTTP server listens [Default: 8080].")
        self.__w.key(name=_MainSettingsMeta.HTTP_SERVER_PORT, varg=main_config.http_server_port)
        self.__w.comment("The IP address of the interface on which the HTTP server should listen [Default: '127.0.0.1'].")
        self.__w.comment("Use '0.0.0.0' to listen on all available interfaces.")
        self.__w.key(name=_MainSettingsMeta.HTTP_SERVER_LISTEN_IP, varg=str(main_config.http_server_listen_ip))

        self.__w.comment()
        self.__w.key(name=_MainSettingsMeta.TPM2NET_SERVER, varg=main_config.tpm2net_server)

    def __write_default_animation(self, animation_config: DefaultAnimation) -> None:
        self.__w.section(name=_DefaultAnimationMeta.SECTION_NAME)
        self.__w.comment("Default animation that is displayed on start/idle.")
        self.__w.comment("The value is equal to the name of the Python module in the 'animation' directory.")
        self.__w.comment("Default start animation is 'dummy' (blank display).")
        self.__w.key(name=_DefaultAnimationMeta.ANIMATION, varg=animation_config.animation_name)

        self.__w.comment()
        self.__w.comment("The possible variants can be checked in the Python module of the corresponding animation.")
        self.__w.key(name=_DefaultAnimationMeta.VARIANT, varg=animation_config.variant_as_str)

        self.__w.comment()
        self.__w.comment("The possible parameters can be checked in the Python module of the corresponding animation.")
        self.__w.comment("They are serialized in a JSON string.")
        self.__w.key(name=_DefaultAnimationMeta.PARAMETER, varg=animation_config.parameter_as_json_str)

        self.__w.comment()
        self.__w.comment("This integer defines, how many times an animation gets repeated.")
        self.__w.comment("    0: no repeat [Default]")
        self.__w.comment("   -1: forever")
        self.__w.comment("x > 0: x-times")
        self.__w.key(name=_DefaultAnimationMeta.REPEAT, varg=animation_config.repeat)

    def __write_apa102(self, apa102_config: APA102) -> None:
        self.__w.section(name=_APA102Meta.SECTION_NAME)
        self.__w.comment("This section contains variables that describe how the LED matrix is built up.")
        self.__w.comment("Specify the color type of the used LEDs:")
        self.__w.comment("    - '1': RGB")
        self.__w.comment("    - '2': RBG")
        self.__w.comment("    - '3': GRB")
        self.__w.comment("    - '4': GBR")
        self.__w.comment("    - '5': BGR [Default]")
        self.__w.comment("    - '6': BRG")
        self.__w.key(name=_APA102Meta.COLOR_TYPE, varg=apa102_config.color_type.value)

        self.__w.comment()
        self.__w.comment("Specify how the LED strip is wired to form a matrix:")
        self.__w.comment("    - '1': line by line")
        self.__w.comment("    - '2': zig zag      [Default]")
        self.__w.key(name=_APA102Meta.WIRE_MODE, varg=apa102_config.wire_mode.value)

        self.__w.comment()
        self.__w.comment("Specify how the matrix dimensions (form [MAIN] section) should be interpreted:")
        self.__w.comment("    - '1': horizontally [Default]")
        self.__w.comment("    - '2': vertically")
        self.__w.key(name=_APA102Meta.ORIENTATION, varg=apa102_config.orientation.value)

        self.__w.comment()
        self.__w.comment("The position of the first controlled LED on the matrix:")
        self.__w.comment("    - '1': top left     [Default]")
        self.__w.comment("    - '2': top right")
        self.__w.comment("    - '3': bottom left")
        self.__w.comment("    - '4': bottom right")
        self.__w.key(name=_APA102Meta.ORIGIN, varg=apa102_config.origin.value)

    def __write_computer(self, computer_config: Computer) -> None:
        self.__w.section(name=_ComputerMeta.SECTION_NAME)
        self.__w.comment("This section contains variables for the computer display.")
        self.__w.comment("Number of pixels that defines the space between single (virtual) LEDs.")
        self.__w.key(name=_ComputerMeta.MARGIN, varg=computer_config.margin)

        self.__w.comment()
        self.__w.comment("Size of the square in pixels that represents a (virtual) LED on the matrix.")
        self.__w.key(name=_ComputerMeta.LED_SIZE, varg=computer_config.led_size)

    def __write_scheduled_animations(self, scheduled_config: ScheduledAnimations) -> None:
        self.__w.section(name=_ScheduledAnimationsMeta.SECTION_NAME)
        self.__w.comment("This parameter contains the schedule table for animations.")
        self.__w.comment("It is encoded in a JSON string.")
        self.__w.comment("This value must not be edited by hand!")
        self.__w.key(name=_ScheduledAnimationsMeta.SCHEDULE_TABLE, varg=scheduled_config.schedule_table_json_str)

    def write(self, config: Settings) -> None:
        self.__write_main(main_config=config.main)

        self.__w.comment()
        self.__w.comment()
        self.__w.comment()
        self.__write_default_animation(animation_config=config.default_animation)

        self.__w.comment()
        self.__w.comment()
        self.__w.comment()
        self.__write_apa102(apa102_config=config.apa102)

        self.__w.comment()
        self.__w.comment()
        self.__w.comment()
        self.__write_computer(computer_config=config.computer)

        self.__w.comment()
        self.__w.comment()
        self.__w.comment()
        self.__write_scheduled_animations(scheduled_config=config.scheduled_animations)

        try:
            self.__w.write(str(self.__file_path))
        except OSError as e:
            self.__log.error(e)
            raise e
