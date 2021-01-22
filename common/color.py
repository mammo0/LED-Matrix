class Color():
    def __init__(self, *args):
        if len(args) == 3:
            self.__red = int(args[0])
            self.__green = int(args[1])
            self.__blue = int(args[2])
        elif len(args) == 1:
            arg = args[0]
            if isinstance(arg, (list, tuple)):
                self.__red = int(arg[0])
                self.__green = int(arg[1])
                self.__blue = int(arg[2])
            elif (isinstance(arg, str) and
                    arg.startswith("#")):
                self.__red = int(arg[1:3], 16)
                self.__green = int(arg[3:5], 16)
                self.__blue = int(arg[5:7], 16)
        else:
            self.__red = 0
            self.__green = 0
            self.__blue = 0

    @property
    def red(self):
        return self.__red

    @property
    def green(self):
        return self.__green

    @property
    def blue(self):
        return self.__blue

    @property
    def pil_tuple(self):
        return (self.__red, self.__green, self.__blue)

    @property
    def hex_value(self):
        return "#%s%s%s" % (
            format(self.__red, "x").zfill(2),
            format(self.__green, "x").zfill(2),
            format(self.__blue, "x").zfill(2)
        )
