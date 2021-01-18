from common.wsgi import CustomWSGIRefServer


class HttpServer():
    def __init__(self, main_app, port=8080):
        self.__main_app = main_app
        self.__port = port

        self.__wsgi_server = CustomWSGIRefServer(port=8080, quiet=True)

    def start(self):
        self.__wsgi_server.start()

    def stop(self):
        self.__wsgi_server.stop()
