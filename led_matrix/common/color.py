class Color:
    def __init__(self, red_or_hex: int | str, green: int=0, blue: int=0) -> None:
        self.__red: int
        self.__green: int
        self.__blue: int

        if isinstance(red_or_hex, int):
            self.__red = red_or_hex
            self.__green = green
            self.__blue = blue
        elif isinstance(red_or_hex, str) and red_or_hex.startswith("#"):
            self.__red = int(red_or_hex[1:3], 16)
            self.__green = int(red_or_hex[3:5], 16)
            self.__blue = int(red_or_hex[5:7], 16)
        else:
            self.__red = 0
            self.__green = 0
            self.__blue = 0

        self.__hex_value: str = (
            f"#{format(self.__red, 'x').zfill(2)}"
            f"{format(self.__green, 'x').zfill(2)}"
            f"{format(self.__blue, 'x').zfill(2)}"
        )

    @property
    def red(self) -> int:
        return self.__red

    @property
    def green(self) -> int:
        return self.__green

    @property
    def blue(self) -> int:
        return self.__blue

    @property
    def pil_tuple(self) -> tuple[int, int, int]:
        return (self.__red, self.__green, self.__blue)

    @property
    def hex_value(self) -> str:
        return self.__hex_value
