from bottle import template, static_file, request, redirect
import bottle

from common import RESOURCES_DIR
from common.bottle import BottleCBVMeta, get, post
from common.wsgi import CustomWSGIRefServer
from common.config import Config


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

    @get("/settings")
    def settings(self):
        return template("settings",
                        # provide the main config
                        config=self.__main_app.config,
                        # except the brightness value should be always actual
                        current_brightness=self.__main_app.display_brightness)

    @post("/settings/<pane>")
    def save_settings(self, pane):
        brightness = request.forms.get("brightness_value")
        enable_rest = request.forms.get("enable_rest")
        enable_tpm2net = request.forms.get("enable_tpm2net")

        # save the settings
        self.__main_app.config.set(Config.MAIN.Brightness, brightness)
        self.__main_app.config.set(Config.MAIN.RestServer, enable_rest)
        self.__main_app.config.set(Config.MAIN.TPM2NetServer, enable_tpm2net)
        self.__main_app.config.save()

        # reload the application
        self.__main_app.reload()

        # reload the page
        redirect("/settings#tab_pane_" + pane)

    @get("/settings/reset/<pane>")
    def reset_settings(self, pane):
        # a simple reload should be sufficient
        redirect("/settings#tab_pane_" + pane)

    @post("/settings/set_brightness")
    def set_brightness(self):
        value = request.forms.get("brightness_value")
        self.__main_app.set_brightness(int(value))

    @get("/js/<file_name:path>")
    def load_js(self, file_name):
        return static_file(file_name, root=self.__js_dir, mimetype="text/javascript")

    @get("/css/<file_name:path>")
    def load_css(self, file_name):
        return static_file(file_name, root=self.__css_dir, mimetype="text/css")

    @get("/fonts/<file_name:path>")
    def load_font(self, file_name):
        return static_file(file_name, root=self.__fonts_dir)
