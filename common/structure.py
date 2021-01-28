from inspect import isclass
import types


def _is_function(x):
        return isinstance(x, types.FunctionType) \
            or isinstance(x, types.BuiltinFunctionType)


class _StructureMeta(type):
    def __new__(metacls, cls, bases, classdict):
        # do not do this when initializing the main class
        if cls not in ("Structure", "NestedStructure"):
            # get all static defined variables
            params = {k: v for k, v in classdict.items() if not (
                k.startswith("_") or
                _is_function(v) or
                isinstance(v, property)
            )}

            # and remove them from the normal class dictionary
            for key in params.keys():
                classdict.pop(key)
        else:
            params = {}

        # add new attributes
        new_cls = super().__new__(metacls, cls, bases, classdict)
        new_cls._params_map_ = params
        new_cls._params_names_ = list(params)

        # maybe some members of the new class are NestedStructures
        # so set the name property of them
        if cls not in ("Structure", "InitializableStructure", "NestedStructure"):
            _NestedStructureMeta._add_names(metacls, new_cls)

        return new_cls

    def __dir__(cls):
        return (['__class__', '__doc__', '__module__'] +
                cls._params_map_)

    def _check_get(cls, name):
        return name in cls._params_map_

    def __getattr__(cls, name):
        if cls._check_get(name):
            return cls._params_map_[name]
        else:
            return super().__getattr__(name)

    def __getitem__(cls, name):
        return cls.__getattr__(name)

    def _check_set(cls, name):
        params_map = cls.__dict__.get('_params_map_', {})
        if name in params_map:
            raise AttributeError('Cannot reassign members.')

    def __setattr__(cls, name, value):
        cls._check_set(name)
        super().__setattr__(name, value)

    def _check_del(cls, attr):
        if attr in cls._params_map_:
            raise AttributeError("%s: cannot delete member." % cls.__name__)

    def __delattr__(cls, attr):
        cls._check_del(attr)
        super().__delattr__(attr)

    def __iter__(cls):
        return iter(cls._params_map_.items())

    @property
    def names(cls):
        return cls._params_names_


class Structure(metaclass=_StructureMeta):
    def __new__(cls):
        instance = super(Structure, cls).__new__(cls)

        # create a copy of the map in the instance
        # so changing values only affects the instance
        instance.__dict__["_params_map_"] = cls._params_map_.copy()

        return instance

    def __getattr__(self, name):
        if _StructureMeta._check_get(type(self), name):
            return self._params_map_[name]
        else:
            return super().__getattr__(name)

    def __setattr__(self, name, value):
        if isinstance(self, StructureROMixin):
            StructureROMixin.__setattr__(self, name, value)
        else:
            if _StructureMeta._check_get(type(self), name):
                self._params_map_[name] = value
            else:
                super().__setattr__(name, value)

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __iter__(self):
        return iter(self._params_map_.items())

    @property
    def names(self):
        return self._params_names_


class StructureROMixin():
    def __setattr__(self, name, value):
        _StructureMeta._check_set(type(self), name)
        super().__setattr__(name, value)

    def __delattr__(self, attr):
        _StructureMeta._check_del(type(self), attr)
        super().__delattr__(attr)


class InitializableStructure(Structure):
    def __new__(cls, *_, **kwargs):
        instance = super(InitializableStructure, cls).__new__(cls)

        # safe the default types
        cls.__default_types = {
            k: type(v) for k, v in cls._params_map_.items()
        }

        # overwrite values in the instance
        for k, v in kwargs.items():
            if k in cls.names:
                # try to cast values to the default type
                # because not all types are supported by JSON
                if issubclass(cls.__default_types[k], type(None)):
                    instance._params_map_[k] = v
                else:
                    instance._params_map_[k] = cls.__default_types[k](v)

        return instance


class _NestedStructureMeta(_StructureMeta):
    def __new__(metacls, cls, bases, classdict):
        new_cls = _StructureMeta.__new__(metacls, cls, bases, classdict)

        # the names should be already added by _StructureMeta
        # so add only the parent
        metacls._add_parent(metacls, new_cls)

        return new_cls

    def _add_names(cls, iterable):
        # iterate over the structure
        for name, value in iterable:
            if (isinstance(value, NestedStructure) or
                    (isclass(value) and
                     issubclass(value, NestedStructure))):
                # set the name property
                setattr(value, NestedStructure.name_attr_name, name)

    def _add_parent(cls, iterable):
        # iterate over the structure
        for _, child in iterable:
            if (isinstance(child, NestedStructure) or
                    issubclass(child, NestedStructure)):
                # set the parent property
                setattr(child, NestedStructure.parent_attr_name, iterable)

    @property
    def name(cls):
        return getattr(cls, NestedStructure.name_attr_name, None)

    @property
    def parent(cls):
        return getattr(cls, NestedStructure.parent_attr_name, None)


class NestedStructure(Structure, metaclass=_NestedStructureMeta):
    name_attr_name = "_name_"
    parent_attr_name = "_parent_"

    def __new__(cls, *args, **kwargs):
        _NestedStructureMeta._add_names(cls, cls)

        instance = super(NestedStructure, cls).__new__(cls)

        _NestedStructureMeta._add_parent(cls, instance)

        return instance

    @property
    def name(self):
        return getattr(self, NestedStructure.name_attr_name, None)

    @property
    def parent(self):
        return getattr(self, NestedStructure.parent_attr_name, None)
