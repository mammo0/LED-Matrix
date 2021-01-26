from collections import namedtuple
import functools

import bottle


METHOD_ATTR_PREFIX = "__bottle__"


# helper namedtupel
_ArgumentWrapper = namedtuple('_ArgumentWrapper', ['args', 'kwargs'])


# function name copied from 'bottle' module
def make_default_app_wrapper(name):
    ''' Return a callable that relays calls to the current default app. '''
    @functools.wraps(getattr(bottle.Bottle, name))
    def wrapper(*a, **ka):
        def decorator(f):
            # mark the methods, so they can later be used
            setattr(f, METHOD_ATTR_PREFIX + name, _ArgumentWrapper(args=a, kwargs=ka))
            return f
        return decorator
    return wrapper


class BottleCBVMeta(type):
    def __call__(self, *args, **kwargs):
        # first create instance
        instance = type.__call__(self, *args, **kwargs)

        # search for marked methods
        for instance_attr_name in dir(instance):
            instance_method = getattr(instance, instance_attr_name)
            if callable(instance_method):
                for method_attr_name in dir(instance_method):
                    if method_attr_name.startswith(METHOD_ATTR_PREFIX):
                        decorator_name = method_attr_name[len(METHOD_ATTR_PREFIX):]
                        bottle_decorator = getattr(bottle, decorator_name)
                        bottle_decorator(*getattr(instance_method, method_attr_name).args,
                                         **getattr(instance_method, method_attr_name).kwargs)(instance_method)

        return instance


route = make_default_app_wrapper('route')
get = make_default_app_wrapper('get')
post = make_default_app_wrapper('post')
put = make_default_app_wrapper('put')
delete = make_default_app_wrapper('delete')
error = make_default_app_wrapper('error')
mount = make_default_app_wrapper('mount')
hook = make_default_app_wrapper('hook')
install = make_default_app_wrapper('install')
uninstall = make_default_app_wrapper('uninstall')
url = make_default_app_wrapper('get_url')
