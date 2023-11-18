import sys
from argparse import ArgumentParser, Namespace
from dataclasses import InitVar, dataclass
from logging import Logger
from pathlib import Path
from typing import Any, cast

import jsons

from led_matrix.animation.abstract import (AbstractAnimationController,
                                           AnimationParameter,
                                           AnimationVariant)
from led_matrix.common.logging import get_logger
from led_matrix.common.schedule import ScheduleEntry
from led_matrix.config.file import _ConfigReader, _ConfigWriter
from led_matrix.config.json import json_serialize
from led_matrix.config.json.deserializer import register_deserializers
from led_matrix.config.json.serializer import register_serializers
from led_matrix.config.settings import Settings


@dataclass(kw_only=True)
class Configuration(Settings):
    config_file_path: InitVar[Path]

    def __post_init__(self, config_file_path: Path) -> None:
        log: Logger = get_logger(__name__)

        # register jsons (de-)serializers
        self.__schedule_deserializer_fork: type = jsons.fork()
        register_serializers()
        register_deserializers(self.__schedule_deserializer_fork)

        self.__writer: _ConfigWriter = _ConfigWriter(config_file_path)

        if not config_file_path.exists():
            log.warning("No configuration file found. Using the default settings.")
        else:
            # load the configuration
            reader: _ConfigReader = _ConfigReader(config_file_path)
            saved_settings: Settings = reader.read()
            self.main = saved_settings.main
            self.default_animation = saved_settings.default_animation
            self.apa102 = saved_settings.apa102
            self.computer = saved_settings.computer
            self.scheduled_animations = saved_settings.scheduled_animations

    def save(self) -> None:
        self.__writer.write(config=self)

    def get_default_animation_parameter(self,
                                        parameter_cls: type[AnimationParameter] | None) -> AnimationParameter | None:
        if parameter_cls is None:
            return None

        return jsons.loads(self.default_animation.parameter_as_json_str, cls=parameter_cls)

    def set_default_animation_parameter(self, parameter: AnimationParameter | None) -> None:
        self.default_animation.parameter_as_json_str = json_serialize(parameter)

    def get_default_animation_variant(self, variant_cls: type[AnimationVariant] | None) -> AnimationVariant | None:
        if variant_cls is None:
            return None

        return cast(AnimationVariant,
                    jsons.default_enum_deserializer(self.default_animation.variant_as_str, cls=variant_cls))

    def set_default_animation_variant(self, variant: AnimationVariant | None) -> None:
        if variant is None:
            self.default_animation.variant_as_str = json_serialize(variant)
        else:
            self.default_animation.variant_as_str = jsons.default_enum_serializer(variant,  # type: ignore
                                                                                  use_enum_name=True)

    def get_scheduled_animations_table(
            self,
            animation_controllers: dict[str, AbstractAnimationController]
    ) -> list[ScheduleEntry]:
        working_table: list[ScheduleEntry] = jsons.loads(self.scheduled_animations.schedule_table_json_str,
                                                         cls=list[ScheduleEntry],
                                                         fork_inst=self.__schedule_deserializer_fork)

        return_table: list[ScheduleEntry] = []

        entry: ScheduleEntry
        for entry in working_table:
            try:
                animation_controller: AbstractAnimationController = animation_controllers[entry.animation_name]
            except KeyError:
                # skip this entry
                continue

            # because of the custom deserializer 'animation_parameter_deserializer',
            # the entry.animation_settings.parameter is actually a json string
            if animation_controller.parameter_class is None:
                entry.animation_settings.parameter = None
            else:
                entry.animation_settings.parameter = jsons.loads(cast(str, entry.animation_settings.parameter),
                                                                 cls=animation_controller.parameter_class)

            # because of the custom deserializer 'animation_variant_deserializer',
            # the entry.animation_settings.variant is actually a string
            if animation_controller.variant_enum is None:
                entry.animation_settings.variant = None
            else:
                entry.animation_settings.variant = jsons.default_enum_deserializer(
                    cast(str, entry.animation_settings.variant),  # type: ignore
                    cls=animation_controller.variant_enum
                )

            return_table.append(entry)

        return return_table


    def set_scheduled_animations_table(self, schedule_table: list[ScheduleEntry]) -> None:
        self.scheduled_animations.schedule_table_json_str = json_serialize(schedule_table)


def create_initial_config() -> None:
     # cli parser
    parser: ArgumentParser = ArgumentParser(description="Create or Update the configuration file.")
    parser.add_argument("CONFIG_FILE_PATH", type=Path,
                        help="The path of the configuration file.")

    # get config path
    args: Namespace = parser.parse_args(sys.argv[1:])
    config_file_path = args.CONFIG_FILE_PATH

    if config_file_path.exists() and not config_file_path.is_file():
        raise ValueError(f"'{config_file_path}' is not the path of a file!")

    # from config import Configuration
    config: Configuration = Configuration(config_file_path=config_file_path)
    config.save()
