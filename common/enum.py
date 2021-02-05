from enum import EnumMeta, Enum


class DynamicEnumMeta(EnumMeta):
    empty_attr = "_empty"

    @property
    def dynamic_enum_dict(cls):
        """
        This method should be overwritten by subclasses.
        @return: A dict with the enum attributes and their values.
        """
        return {}

    def __get_dynamic_enum_class(cls, enum_dict):
        # avoid enum extension error if accessing via the _empty attribute
        if (len(cls._member_names_) == 1 and
                cls._member_names_[0] == DynamicEnumMeta.empty_attr):
            cls._member_names_.clear()
        return EnumMeta.__call__(cls, cls.__name__, names=enum_dict)

    def __getattr__(cls, name):
        # this avoids recursion
        enum_dict = cls.dynamic_enum_dict
        if name in enum_dict:
            return EnumMeta.__getattr__(cls.__get_dynamic_enum_class(enum_dict), name)
        elif name == DynamicEnumMeta.empty_attr:
            return EnumMeta.__getattr__(cls.__get_dynamic_enum_class({DynamicEnumMeta.empty_attr: object()}),
                                        DynamicEnumMeta.empty_attr)
        else:
            return EnumMeta.__getattr__(cls, name)

    # override all magic methods of EnumMeta to use the dynamic enum as class

    def __call__(cls, value, names=None, *, module=None, qualname=None, type=None, start=1):  # noqa
        return EnumMeta.__call__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict),
                                 value, names=names, module=module, qualname=qualname, type=type, start=start)

    def __contains__(cls, member):
        return EnumMeta.__contains__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict), member)

    def __dir__(cls):
        return EnumMeta.__dir__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict))

    def __delattr__(cls, attr):
        EnumMeta.__delattr__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict), attr)

    def __getitem__(cls, name):
        return EnumMeta.__getitem__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict), name)

    def __iter__(cls):
        return EnumMeta.__iter__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict))

    def __len__(cls):
        return EnumMeta.__len__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict))

    @property
    def __members__(cls):
        return EnumMeta.__members__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict))

    def __reversed__(cls):
        return EnumMeta.__reversed__(cls.__get_dynamic_enum_class(cls.dynamic_enum_dict))


class DynamicEnum(Enum, metaclass=DynamicEnumMeta):
    def __eq__(self, other):
        if (isinstance(other, DynamicEnum) and
                # compare dynamic enums by name and value identity
                other.name == self.name and
                other.value == self.value):
            return True

        return Enum.__eq__(self, other)
