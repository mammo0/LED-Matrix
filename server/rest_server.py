import glob
import json
import os
import re
import shutil
import threading
import zipfile

from bottle import run, get, post, request, response, static_file, install, route, \
    WSGIRefServer
import imageio


class RestServer:
    def __init__(self, main_app):
        self.main_app = main_app

    def start(self):
        # setup routing
        route("/display/brightness", method=['OPTIONS', 'POST'])(self.set_brightness)
        route("/mode", method=['OPTIONS', 'POST'])(self.set_mode)
        route("/moodlight/mode", method=['OPTIONS', 'POST'])(self.set_moodlight_mode)

        route("/text", method=['OPTIONS', 'POST'])(self.set_text)

        route("/gameframe", method=['OPTIONS', 'GET'])(self.get_gameframes)
        route("/gameframe", method=['OPTIONS', 'DELETE'])(self.delete_gameframe)
        route("/gameframe/next", method=['OPTIONS', 'POST'])(self.next_gameframe)
        route("/gameframe/current", method=['OPTIONS', 'POST'])(self.set_next_gameframe)

        get("/gameframe/<gameframe>")(self.get_gameframe)
        post("/gameframe/upload/<name>")(self.upload_gameframe)
        post("/gameframe")(self.select_gameframes)

        # run server
        install(EnableCors())
        threading.Thread(target=run, kwargs=dict(host='127.0.0.1',
                                                 port=8081,
                                                 server=CustomWSGIRefServer,
                                                 quiet=True)).start()

    def stop(self):
        # stop all instances
        while len(CustomWSGIRefServer.instances) > 0:
            CustomWSGIRefServer.instances[0].stop()
            CustomWSGIRefServer.instances.pop(0)

    # POST /display/brightness [float: value]
    def set_brightness(self):
        value = request.json
        if value > 1.0:
            value = 1.0
        elif value < 0.0:
            value = 0.0
        self.main_app.display.set_brightness(value)

    # POST /mode [int: mode]
    def set_mode(self):
        value = request.json
        self.main_app.disable_animations()
        if value == 1:
            self.main_app.moodlight_activated = True
        elif value == 2:
            self.main_app.gameframe_activated = True
        elif value == 3:
            self.main_app.blm_activated = True
        elif value == 4:
            self.main_app.clock_activated = True
            self.main_app.clock_last_shown = 0
        elif value == 5:
            self.main_app.play_random = True

        self.main_app.stop_current_animation()

    # POST /moodlight/mode [int: mode]
    def set_moodlight_mode(self):
        value = request.json
        self.main_app.set_moodlight_mode(value)

    # POST /gameframe/upload/<name>
    def upload_gameframe(self, name):
        zip_file = request.body
        zip_archive = zipfile.ZipFile(zip_file)
        zip_archive.extractall('resources/animations/gameframe_upload/' + name)

    # POST /gameframe/next
    def next_gameframe(self):
        self.main_app.stop_current_animation()

    # POST /gameframe/current
    def set_next_gameframe(self):
        path = "resources/animations/gameframe_upload/" + request.json
        self.main_app.set_next_animation(path)
        self.main_app.stop_current_animation()

    # POST /gameframe sets the playlist
    def select_gameframes(self):
        self.main_app.refresh_animations()
        gameframes = request.json
        self.main_app.gameframe_selected = ["resources/animations/gameframe_upload/" + frame for frame in gameframes]

    # DELETE /gameframe deletes a gameframe
    def delete_gameframe(self):
        name = request.json
        shutil.rmtree('resources/animations/gameframe_upload/' + name)
        self.main_app.refresh_animations()

    # GET /gameframe
    def get_gameframes(self):
        response.set_header('Content-type', 'application/json')
        return json.dumps(self.get_folder_names('resources/animations/gameframe_upload/'))

    # GET /gameframe/<gameframe>
    def get_gameframe(self, gameframe):
        file_names = sorted(glob.glob('resources/animations/gameframe_upload/' + gameframe + '/*.bmp'),
                            key=alphanum_key)
        print(file_names)
        images = [imageio.imread(filename) for filename in file_names]
        imageio.mimwrite('resources/animations/gameframe_temp.gif', images)
        return static_file('resources/animations/gameframe_temp.gif',  root=".", mimetype='image/gif')

    # POST /text
    def set_text(self):
        text = request.json[:100]
        self.main_app.text_queue.put(text)

    def get_folder_names(self, directory):
        return [name for name in os.listdir(directory)]


def tryint(s):
    try:
        return int(s)
    except ValueError:
        return s


def alphanum_key(s):
    return [tryint(c) for c in re.split('([0-9]+)', s)]


class EnableCors(object):
    name = 'enable_cors'
    api = 2

    def apply(self, fn, context):
        def _enable_cors(*args, **kwargs):
            # set CORS headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = ('Origin, Accept, Content-Type, X-Requested-With, '
                                                                'X-CSRF-Token')

            if request.method != 'OPTIONS':
                # actual request; reply with the actual response
                return fn(*args, **kwargs)

        return _enable_cors


class CustomWSGIRefServer(WSGIRefServer):
    instances = []

    def __init__(self, host='127.0.0.1', port=8080, **options):
        WSGIRefServer.__init__(self, host=host, port=port, **options)
        self.srv = None
        CustomWSGIRefServer.instances.append(self)

    def run(self, app):  # pragma: no cover
        from wsgiref.simple_server import WSGIRequestHandler, WSGIServer
        from wsgiref.simple_server import make_server
        import socket

        class FixedHandler(WSGIRequestHandler):
            def address_string(self):  # Prevent reverse DNS lookups please.
                return self.client_address[0]

            def log_request(self, *args, **kw):
                if not self.quiet:
                    return WSGIRequestHandler.log_request(self, *args, **kw)

        handler_cls = self.options.get('handler_class', FixedHandler)
        server_cls = self.options.get('server_class', WSGIServer)

        if ':' in self.host:  # Fix wsgiref for IPv6 addresses.
            if getattr(server_cls, 'address_family') == socket.AF_INET:
                class server_cls(server_cls):
                    address_family = socket.AF_INET6

        self.srv = make_server(self.host, self.port, app, server_cls, handler_cls)
        self.srv.serve_forever()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()
