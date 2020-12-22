import glob
import json
import os
import re
import shutil
import threading
import zipfile

from bottle import run, get, post, request, response, static_file, install, route
import imageio


class RibbaPiRestServer:
    def __init__(self, ribbapi):
        self.ribbapi = ribbapi

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
        threading.Thread(target=run, kwargs=dict(host='127.0.0.1', port=8081)).start()

    # POST /display/brightness [float: value]
    def set_brightness(self):
        value = request.json
        if value > 1.0:
            value = 1.0
        elif value < 0.0:
            value = 0.0
        self.ribbapi.display.set_brightness(value)

    # POST /mode [int: mode]
    def set_mode(self):
        value = request.json
        self.ribbapi.disable_animations()
        if value == 1:
            self.ribbapi.moodlight_activated = True
        elif value == 2:
            self.ribbapi.gameframe_activated = True
        elif value == 3:
            self.ribbapi.blm_activated = True
        elif value == 4:
            self.ribbapi.clock_activated = True
            self.ribbapi.clock_last_shown = 0
        elif value == 5:
            self.ribbapi.play_random = True

        self.ribbapi.stop_current_animation()

    # POST /moodlight/mode [int: mode]
    def set_moodlight_mode(self):
        value = request.json
        self.ribbapi.set_moodlight_mode(value)

    # POST /gameframe/upload/<name>
    def upload_gameframe(self, name):
        zip_file = request.body
        zip_archive = zipfile.ZipFile(zip_file)
        zip_archive.extractall('resources/animations/gameframe_upload/' + name)

    # POST /gameframe/next
    def next_gameframe(self):
        self.ribbapi.stop_current_animation()

    # POST /gameframe/current
    def set_next_gameframe(self):
        path = "resources/animations/gameframe_upload/" + request.json
        self.ribbapi.set_next_animation(path)
        self.ribbapi.stop_current_animation()

    # POST /gameframe sets the playlist
    def select_gameframes(self):
        self.ribbapi.refresh_animations()
        gameframes = request.json
        self.ribbapi.gameframe_selected = ["resources/animations/gameframe_upload/" + frame for frame in gameframes]

    # DELETE /gameframe deletes a gameframe
    def delete_gameframe(self):
        name = request.json
        shutil.rmtree('resources/animations/gameframe_upload/' + name)
        self.ribbapi.refresh_animations()

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
        self.ribbapi.text_queue.put(text)

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
