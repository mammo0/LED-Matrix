from threading import Thread, Event

from bottle import WSGIRefServer, run
from common import eprint


class CustomWSGIRefServer(WSGIRefServer):
    def __init__(self, host='127.0.0.1', port=8080, **options):
        WSGIRefServer.__init__(self, host=host, port=port, **options)

        self.__server = None
        self.__server_started = Event()

    # copied from WSGIRefServer.run
    def run(self, app):  # pragma: no cover
        from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
        from wsgiref.simple_server import make_server
        import socket

        class FixedHandler(WSGIRequestHandler):
            def address_string(self):  # Prevent reverse DNS lookups please.
                return self.client_address[0]

            def log_request(*args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(*args, **kw)

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls = self.options.get('server_class', WSGIServer)

        if ':' in self.host:  # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        #######################################################################
        # until here, everything is copied
        # add server instance to self (to be able to stop the server later)
        self.__server = make_server(self.host, self.port, app, server_cls, handler_cls)
        self.__server_started.set()
        self.__server.serve_forever()

    def start(self):
        Thread(target=run, kwargs=dict(server=self)).start()

    def stop(self, timeout=None):
        # wait until the server is fully started
        if self.__server_started.wait(timeout=timeout):
            # shut it down
            self.__server.shutdown()
            self.__server.server_close()

            # mark the server as stopped
            self.__server_started.clear()
        else:
            eprint("Failed to shutdown 'WSGIRefServer'! Timeout was reached.")
