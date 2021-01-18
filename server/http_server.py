from bottle import template
import bottle

from common import RESOURCES_DIR
from common.bottle import BottleCBVMeta, get
from common.wsgi import CustomWSGIRefServer


# change bottle template path
HTTP_RESOURCES_DIR = RESOURCES_DIR / "http"
bottle.TEMPLATE_PATH = [(HTTP_RESOURCES_DIR / "templates").resolve()]


class HttpServer(metaclass=BottleCBVMeta):
    def __init__(self, main_app, port=8080):
        self.__main_app = main_app
        self.__port = port

        self.__wsgi_server = CustomWSGIRefServer(port=8080, quiet=True)

    def start(self):
        self.__wsgi_server.start()

    def stop(self):
        self.__wsgi_server.stop()

    @get("/")
    def index(self):
        return template("index")
