import jsons

from led_matrix.animation.abstract import (AnimationParameter,
                                           AnimationParameterTypes,
                                           AnimationVariant)
from led_matrix.common.color import Color
from led_matrix.config.json import json_serialize


def register_deserializers(schedule_deserializer_fork: type) -> None:
    jsons.set_deserializer(color_deserializer, Color)

    # these deserializers are only needed to load the schedules table
    # therefore, they run in a separate fork
    jsons.set_deserializer(animation_variant_deserializer, AnimationVariant,
                           fork_inst=schedule_deserializer_fork)
    jsons.set_deserializer(animation_parameter_deserializer, AnimationParameter,
                           fork_inst=schedule_deserializer_fork)


def color_deserializer(obj: str, cls: type[Color], **_) -> Color:
    return cls(obj)


# helper deserializers to parse strings of unknown AnimationVariant and AnimationParameter objects
# these are needed during loading of the table with the scheduled animations
def animation_variant_deserializer(obj: str, *_, **__) -> str:
    # return the variant enum unchanged
    return obj

def animation_parameter_deserializer(obj: dict[str, AnimationParameterTypes],
                                     *_, **__) -> str:
    # return the AnimationParameter as json string
    # -> it gets processed in Conifguration.get_scheduled_animations_table
    return json_serialize(obj=obj)
