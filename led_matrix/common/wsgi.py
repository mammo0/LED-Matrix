from logging import Logger
from threading import Thread, Event
from typing import Any
from wsgiref.simple_server import WSGIServer

from bottle import WSGIRefServer, run
from led_matrix.common.logging import get_logger


class CustomWSGIRefServer(WSGIRefServer):
    def __init__(self, host: str='127.0.0.1', port: int=8080, **options: Any):
        super().__init__(host=host, port=port, **options)

        self.quiet: bool = options.get("quiet", False)

        self.__log: Logger = get_logger(name=WSGIRefServer.__name__)
        self.__server: WSGIServer | None = None
        self.__server_started: Event = Event()

    # copied from WSGIRefServer.run
    def run(self, app) -> None:
        # pylint: disable=C0415,E0213,C0103,E0102
        #TODO: fixed in bottle 0.13+

        from wsgiref.simple_server import WSGIRequestHandler
        from wsgiref.simple_server import make_server
        import socket

        class FixedHandler(WSGIRequestHandler):
            def address_string(self):  # Prevent reverse DNS lookups please.
                return self.client_address[0]

            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)  # type: ignore

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls = self.options.get('server_class', WSGIServer)

        if ':' in self.host:  # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):  # type: ignore
                    address_family = socket.AF_INET6

        #######################################################################
        # until here, everything is copied
        # add server instance to self (to be able to stop the server later)
        self.__server = make_server(self.host, self.port, app, server_cls, handler_cls)
        self.__server_started.set()
        self.__server.serve_forever()

    def start(self) -> None:
        Thread(target=run, kwargs={"server": self}).start()

    def stop(self, timeout: float | None=None):
        # wait until the server is fully started
        if self.__server_started.wait(timeout=timeout) and self.__server is not None:
            # shut it down
            self.__server.shutdown()
            self.__server.server_close()

            # mark the server as stopped
            self.__server_started.clear()
        else:
            self.__log.error("Failed to shutdown WSGI server! Timeout was reached.")
