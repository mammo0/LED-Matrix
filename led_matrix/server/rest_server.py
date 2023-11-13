from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, cast

from bottle import Route, install, request, response, route

from led_matrix.common.wsgi import CustomWSGIRefServer

if TYPE_CHECKING:
    from led_matrix.main import Main


class RestServer:
    def __init__(self, main_app: Main):
        self.__main_app: Main = main_app

        self.__wsgi_server: CustomWSGIRefServer = CustomWSGIRefServer(
            host=str(self.__main_app.config.main.rest_server_listen_ip),
            port=self.__main_app.config.main.rest_server_port,
            quiet=True
        )

    def start(self):
        # setup routing
        route("/display/brightness", method=['OPTIONS', 'POST'])(self.set_brightness)

        # run server
        install(EnableCors())
        self.__wsgi_server.start()

    def stop(self):
        self.__wsgi_server.stop()

    # POST /display/brightness [float: value]
    def set_brightness(self) -> None:
        brightness: int = cast(int, request.json)

        if brightness > 100:
            brightness = 100
        elif brightness < 0:
            brightness = 0

        self.__main_app.config.main.day_brightness = brightness
        self.__main_app.config.save()
        self.__main_app.apply_brightness()


class EnableCors:
    name: str = 'enable_cors'
    api: int = 2

    def apply(self, callback: Callable[..., Any], _route: Route) -> Callable[..., Any]:
        def _enable_cors(*args, **kwargs) -> Any:
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = ('Origin, Accept, Content-Type, X-Requested-With, '
                                                                'X-CSRF-Token')

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return callback(*args, **kwargs)

        return _enable_cors
