from configparser import ConfigParser
import configparser
from distutils.util import strtobool
from io import StringIO
import json
import shutil
import subprocess
import sys

from common import eprint
from common.structure import NestedStructure, Structure, StructureROMixin


class ConfigSection(NestedStructure, StructureROMixin):
    def __init__(self, description=None):
        if description is None:
            self.__description = ""
        elif isinstance(description, list):
            self.__description = "\n".join(["# %s" % d for d in description])
        else:
            self.__description = "# %s" % description

    @property
    def description(self):
        return self.__description


class ConfigValue(ConfigSection):
    def __init__(self, value_type, default_value=configparser._UNSET, description=None):
        ConfigSection.__init__(self, description=description)

        if (default_value != configparser._UNSET and
                not isinstance(default_value, value_type)):
            raise ValueError("The default value '%s' is not of type '%s'!" % (str(default_value), str(value_type)))

        self.__value_type = value_type
        self.__default_value = default_value

    @property
    def value_type(self):
        return self.__value_type

    @property
    def default_value(self):
        return self.__default_value

    def parse_value(self, value):
        if isinstance(value, self.value_type):
            return value
        elif (isinstance(value, (dict, list)) and
                self.value_type == str):
            # convert it to a JSON string
            return json.dumps(value)
        elif (isinstance(value, str) and
                self.value_type in (dict, list)):
            # load it from JSON string
            try:
                parsed_v = json.loads(value)
            except ValueError:
                eprint("Parameter '%s' could not be parsed! Is it valid JSON?" % self.name)
                parsed_v = self.value_type()
            return parsed_v
        elif self.value_type == bool:
            return bool(strtobool(value))
        else:
            try:
                return self.value_type(value)
            except ValueError:
                raise ValueError("The value '%s' is not of type '%s'!" % (str(value), str(self.value_type)))


class Config(Structure, StructureROMixin):
    class __Main(ConfigSection):
        Hardware = ConfigValue(value_type=str, default_value="APA102", description=[
            "The display defines where the animations should be showed.",
            "There are two possible values here:",
            "    - 'APA102'   [Default]",
            "      The actual LED hardware addressed via SPI.",
            "    - 'COMPUTER'",
            "      This is for developing on a PC. It opens a virtual LED matrix via 'pygame'.",
        ])
        DisplayWidth = ConfigValue(value_type=int, default_value=15,
                                   description="Set the number of LEDs for width and height of your matrix")
        DisplayHeight = ConfigValue(value_type=int, default_value=12)
        Brightness = ConfigValue(value_type=int, default_value=85, description=[
            "Set the brightness in percent [Default: 85]",
            "Possible values: 0 < = x <= 100"
        ])
        HttpServer = ConfigValue(value_type=bool, default_value=True, description=[
            "(De-)Activate the server interfaces that control the matrix.",
            "Available servers:",
            "    - HttpServer [Default: true]",
            "    - RestServer [Default: true]",
            "    - TPM2NetServer [Default: false]: UDP 65506"
        ])
        HttpServerPort = ConfigValue(value_type=int, default_value=8080,
                                     description="The port on which the HTTP server listens [Default: 8080].")
        HttpServerInterfaceIP = ConfigValue(value_type=str, default_value="127.0.0.1", description=[
            "The IP address of the interface on which the HTTP server should listen [Default: '127.0.0.1'].",
            "Use '0.0.0.0' to listen on all available interfaces."
        ])
        RestServer = ConfigValue(value_type=bool, default_value=True)
        RestServerPort = ConfigValue(value_type=int, default_value=8081,
                                     description="The port on which the REST server listens [Default: 8081].")
        RestServerInterfaceIP = ConfigValue(value_type=str, default_value="127.0.0.1", description=[
            "The IP address of the interface on which the REST server should listen [Default: '127.0.0.1'].",
            "Use '0.0.0.0' to listen on all available interfaces."
        ])
        TPM2NetServer = ConfigValue(value_type=bool, default_value=False)

    class __DefaultAnimation(ConfigSection):
        Animation = ConfigValue(value_type=str, default_value="clock", description=[
            "The value is equal to the name of the Python module in the 'animation' directory.",
            "Default start animation is 'clock'."
        ])
        Variant = ConfigValue(value_type=str, default_value="digital", description=[
            "The possible variants can be checked in the Python module of the corresponding animation.",
            "Default for animation 'clock' is variant 'digital'."
        ])
        Parameter = ConfigValue(value_type=dict, default_value={
                                                                   "background_color": [0, 0, 0],
                                                                   "divider_color": [255, 255, 255],
                                                                   "hour_color": [255, 0, 0],
                                                                   "minute_color": [255, 255, 255],
                                                                   "blinking_seconds": True
                                                                },
                                description=[
            "Sometimes a variant needs a parameter.",
            "If multiple parameters are needed, a JSON-like dictionary can be entered after the equal sign.",
            "Multiline is supported but every line must have an indention."
        ])
        Repeat = ConfigValue(value_type=int, default_value=0, description=[
            "This integer defines, how many times an animation gets repeated.",
            "    0: no repeat [Default]",
            "   -1: forever",
            "x > 0: x-times"
        ])

    class __Apa102(ConfigSection):
        ColorType = ConfigValue(value_type=int, default_value=5, description=[
            "This section contains variables that describe how the LED matrix is built up.",
            "Specify the color type of the used LEDs:",
            "    - '1': RGB",
            "    - '2': RBG",
            "    - '3': GRB",
            "    - '4': GBR",
            "    - '5': BGR [Default]",
            "    - '6': BRG"
        ])
        WireMode = ConfigValue(value_type=int, default_value=2, description=[
            "Specify how the LED strip is wired to form a matrix:",
            "    - '1': line by line",
            "    - '2': zig zag      [Default]"
        ])
        Orientation = ConfigValue(value_type=int, default_value=1, description=[
            "Specify how the matrix dimensions (form [MAIN] section) should be interpreted:",
            "    - '1': horizontally [Default]",
            "    - '2': vertically"
        ])
        Origin = ConfigValue(value_type=int, default_value=1, description=[
            "The position of the first controlled LED on the matrix:",
            "    - '1': top left     [Default]",
            "    - '2': top right",
            "    - '3': bottom left",
            "    - '4': bottom right"
        ])

    class __Computer(ConfigSection):
        Margin = ConfigValue(value_type=int, default_value=5,
                             description="Number of pixels that defines the space between single (virtual) LEDs.")
        LEDSize = ConfigValue(value_type=int, default_value=30,
                              description="Size of the square that represents a (virtual) LED on the matrix.")

    class __ScheduledAnimations(ConfigSection):
        ScheduleTable = ConfigValue(value_type=list, default_value=[],
                                    description=["This parameter contains the schedule table for animations.",
                                                 "It is encoded in a JSON string.",
                                                 "This value must not be edited by hand!"])

    MAIN = __Main()
    DEFAULTANIMATION = __DefaultAnimation("Default animation that is displayed on start/idle")
    APA102 = __Apa102("This section contains variables that describe how the LED matrix is built up.")
    COMPUTER = __Computer("This section contains variables for the computer display.")
    SCHEDULEDANIMATIONS = __ScheduledAnimations()


class Configuration():
    def __init__(self, *args, config_file_path=None, commit_changes=False, **kwargs):
        self.__config_parser = ConfigParser(*args, **kwargs)
        self.__config_parser.optionxform = lambda option: option

        self.__config = {}

        self.__config_file_path = config_file_path
        self.__commit_changes = commit_changes

        use_default_config = False
        # check if a path is supplied
        if self.__config_file_path is None:
            print("No configuration file provided. Using default configuration. Saving is not possible!")
            use_default_config = True
        # check if the path exists and if it's a file
        elif self.__config_file_path.exists() and not self.__config_file_path.is_file():
            # if not
            eprint(("The location '%s' is not a file! "
                    "Using default configuration. Saving is not possible!") % str(self.__config_file_path))
            use_default_config = True
            # prevent saving
            self.__config_file_path = None
        # otherwise check if the file exists
        elif not self.__config_file_path.exists():
            eprint(("The location '%s' does not exist! "
                    "Using default configuration.") % str(self.__config_file_path))
            use_default_config = True

        # load the config if a file was found
        if not use_default_config:
            with open(self.__config_file_path, "r") as f:
                self.__config_parser.read_file(f)

        for section_name, section in Config:
            self.__config[section_name] = {}

            for option_name, option in section:
                if use_default_config:
                    # just use the default value
                    value = option.default_value
                else:
                    try:
                        value = option.parse_value(self.__config_parser[section_name][option_name])
                    except KeyError:
                        eprint("The option '%s.%s' was not found in the configuration file '%s'!" % (
                            section_name,
                            option_name,
                            str(self.__config_file_path)
                        ))
                        if option.default_value == configparser._UNSET:
                            def_val = ""
                        else:
                            def_val = str(option.default_value)
                        eprint("Using the default value '%s'." % def_val)
                        value = option.default_value

                self.__config[section_name][option_name] = value

    def get(self, option):
        return self.__config[option.parent.name][option.name]

    def set(self, option, value):
        value = option.parse_value(value)
        self.__config[option.parent.name][option.name] = value

    def save(self):
        if self.__config_file_path is not None:
            output = StringIO()

            for section_name, section in Config:
                # section heading
                print("[%s]" % section_name, file=output)
                # section description
                if section.description:
                    print(section.description, file=output)

                for option_name, option in section:
                    # option description
                    if option.description:
                        print(option.description, file=output)

                    # option value
                    value = self.get(option)

                    # check for a unset value
                    if value == configparser._UNSET:
                        print("{} =".format(option_name), file=output)
                    else:
                        # dicts and lists must be converted to JSON
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        # preserve multiline strings -> starting from the second line indention is needed
                        if (option.value_type == str and
                                "\n" in value):
                            value = "\n    ".join(value.split("\n"))
                        print("{} = {}".format(option_name, value), file=output)

                    print(file=output)

                print(file=output)
                print(file=output)

            with open(self.__config_file_path, "w+") as f:
                output.seek(0)
                shutil.copyfileobj(output, f)

            # now check if the changes should be commited
            if self.__commit_changes:
                # also check if the 'lbu' tool is available
                if shutil.which("lbu") is not None:
                    lbu_process = subprocess.run(["lbu", "commit", "-d"], stdout=sys.stdout, stderr=sys.stderr)
                    if lbu_process.returncode != 0:
                        eprint("Failed to commit file changes with 'lbu'! See output above.")
                else:
                    eprint("Cannot commit file changes, because 'lbu' tool was not found!")
        else:
            eprint("This configuration object can't be saved!")
