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
