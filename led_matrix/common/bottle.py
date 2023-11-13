from collections.abc import Callable
import functools
import inspect
from typing import Any, Final, Generic, Literal, NamedTuple, ParamSpec, TypeVar

import bottle


DP = ParamSpec("DP")
DR = TypeVar("DR")

MT = TypeVar("MT")

BottleDecorators = Literal["route",
                           "get",
                           "post",
                           "put",
                           "delete",
                           "error",
                           "mount",
                           "hook",
                           "install",
                           "uninstall",
                           "get_url"]


_METHOD_ATTR_PREFIX: Final[str] = "__bottle__"


# helper namedtupel
class _ArgumentWrapper(NamedTuple):
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


def _create_cbv_decorator(fuction_name_to_wrap: BottleDecorators) -> Callable[..., Callable[[Callable[DP, DR]],
                                                                                            Callable[DP, DR]]]:
    # original function from Bottle class
    bottle_orig_func: Callable[..., Any] = getattr(bottle.Bottle, fuction_name_to_wrap)

    @functools.wraps(bottle_orig_func)
    def wrapper(*decorator_args: Any, **decorator_kwargs: Any) -> Callable[[Callable[DP, DR]], Callable[DP, DR]]:
        def decorator(decorated_cbv_method: Callable[DP, DR]) -> Callable[DP, DR]:
            # add an extra attribute to the decorated class method with
            #   the name of the function that should be wrapped as attribute name
            #   and the arguments of the decorator as attribute value
            #
            # this attribute is needed later in the metaclass for implementing class based views
            setattr(decorated_cbv_method,
                    _METHOD_ATTR_PREFIX + fuction_name_to_wrap,
                    _ArgumentWrapper(args=decorator_args,
                                     kwargs=decorator_kwargs))
            return decorated_cbv_method
        return decorator
    return wrapper


class BottleCBVMeta(type, Generic[MT]):
    __PREFIX_LENGTH: Final[int] = len(_METHOD_ATTR_PREFIX)

    def __call__(cls, *args: Any, **kwargs: Any) -> MT:
        # first create instance
        instance: MT = type.__call__(cls, *args, **kwargs)

        # search for marked methods
        instance_method: Callable[..., Any]
        for _, instance_method in inspect.getmembers(instance, predicate=inspect.ismethod):
            method_attr_name: str
            for method_attr_name in dir(instance_method):
                if method_attr_name.startswith(_METHOD_ATTR_PREFIX):
                    # load the previously saved name of the wrapped function
                    bottle_decorator_name: str = method_attr_name[BottleCBVMeta.__PREFIX_LENGTH:]
                    # load the previously saved arguments of the decorator
                    instance_decorator_args: _ArgumentWrapper = getattr(instance_method, method_attr_name)

                    # this is the original decorator from the bottle module
                    bottle_decorator: Callable[..., Callable[..., Any]] = getattr(bottle, bottle_decorator_name)

                    # use the original decorator to add the decorated method of the instance as class based view
                    bottle_decorator(*instance_decorator_args.args,
                                     **instance_decorator_args.kwargs)(instance_method)

        return instance


route = _create_cbv_decorator("route")
get = _create_cbv_decorator("get")
post = _create_cbv_decorator("post")
put = _create_cbv_decorator("put")
delete = _create_cbv_decorator("delete")
error = _create_cbv_decorator("error")
mount = _create_cbv_decorator("mount")
hook = _create_cbv_decorator("hook")
install = _create_cbv_decorator("install")
uninstall = _create_cbv_decorator("uninstall")
url = _create_cbv_decorator("get_url")
