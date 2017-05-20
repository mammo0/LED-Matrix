from bottle import run, get, post, request
import threading
import zipfile

class RibbaPiRestServer:
    def __init__(self, ribbapi):
        self.ribbapi = ribbapi

    def start(self):
        # setup routing
        post("/display/brightness")(self.set_brightness)
        post("/mode")(self.set_mode)
        post("/moodlight/mode")(self.set_moodlight_mode)
        post("/gameframe/upload/<name>")(self.upload_gameframe)
        # run server
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
        print(request.body)
        file = request.body
        zip = zipfile.ZipFile(file)
        zip.extractall('resources/animations/gameframe_upload/' + name)








