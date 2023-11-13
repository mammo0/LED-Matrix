import jsons

from led_matrix.common.color import Color


def register_serializers() -> None:
    jsons.set_serializer(color_serializer, Color)


def color_serializer(obj: Color, **_) -> str:
    return obj.hex_value
