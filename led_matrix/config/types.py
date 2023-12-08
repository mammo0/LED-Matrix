from enum import Enum


class Hardware(Enum):
    APA102 = "APA102"
    COMPUTER = "COMPUTER"


class LEDColorType(Enum):
    RGB = 1
    RBG = 2
    GRB = 3
    GBR = 4
    BGR = 5
    BRG = 6


class LEDWireMode(Enum):
    LINE_BY_LINE = 1
    ZIG_ZAG = 2


class LEDOrientation(Enum):
    HORIZONTALLY = 1
    VERTICALLY = 2


class LEDOrigin(Enum):
    TOP_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_LEFT = 3
    BOTTOM_RIGHT = 4


class ColorTemp(Enum):
    K_1900 = (1., 147 / 255,  41 / 255)
    K_2600 = (1., 197 / 255, 143 / 255)
    K_2850 = (1., 214 / 255, 170 / 255)
    K_3200 = (1., 241 / 255, 224 / 255)
    K_5200 = (1., 250 / 255, 244 / 255)
    K_6000 = (1.,        1.,        1.)

    @property
    def title(self) -> str:
        kelvin: int
        title: str
        if self == ColorTemp.K_1900:
            kelvin = 1900
            title = "Candle"
        elif self == ColorTemp.K_2600:
            kelvin = 2600
            title = "40W Bulb"
        elif self == ColorTemp.K_2850:
            kelvin = 2850
            title = "100W Bulb"
        elif self == ColorTemp.K_3200:
            kelvin = 3200
            title = "Halogen"
        elif self == ColorTemp.K_5200:
            kelvin = 5200
            title = "Carbon Arc"
        else:
            kelvin = 6000
            title = "Unchanged"

        return f"{kelvin}K - {title}"
