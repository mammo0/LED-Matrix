from bottle import template, static_file, request, redirect
import bottle

from common import RESOURCES_DIR
from common.bottle import BottleCBVMeta, get, post
from common.wsgi import CustomWSGIRefServer


# change bottle template path
HTTP_RESOURCES_DIR = RESOURCES_DIR / "http"
bottle.TEMPLATE_PATH = [(HTTP_RESOURCES_DIR / "templates").resolve()]


class HttpServer(metaclass=BottleCBVMeta):
    def __init__(self, main_app, port=8080):
        self.__main_app = main_app
        self.__port = port

        self.__js_dir = HTTP_RESOURCES_DIR / "js"
        self.__css_dir = HTTP_RESOURCES_DIR / "css"
        self.__fonts_dir = HTTP_RESOURCES_DIR / "fonts"

        self.__wsgi_server = CustomWSGIRefServer(port=8080, quiet=True)

    def start(self):
        self.__wsgi_server.start()

    def stop(self):
        self.__wsgi_server.stop()

    @get("/")
    def index(self):
        return template("index")

    @get("/basic_settings")
    def basic_settings(self):
        return template("basic_settings", current_brightness=self.__main_app.display_brightness)

    @post("/basic_settings/set_brightness")
    def set_brightness(self):
        value = request.forms.get("brightness_value")
        self.__main_app.set_brightness(int(value))
        # go back to the settings page
        redirect("/basic_settings")

    @get("/js/<file_name:path>")
    def load_js(self, file_name):
        return static_file(file_name, root=self.__js_dir, mimetype="text/javascript")

    @get("/css/<file_name:path>")
    def load_css(self, file_name):
        return static_file(file_name, root=self.__css_dir, mimetype="text/css")

    @get("/fonts/<file_name:path>")
    def load_font(self, file_name):
        return static_file(file_name, root=self.__fonts_dir)
