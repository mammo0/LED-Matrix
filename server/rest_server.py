from bottle import route, run
import threading

class RibbaPiRestServer:
    def __init__(self, ribbapi):
        self.ribbapi = ribbapi

    def start(self):
        # setup routing
        route("/hello")(self.index)
        # run server
        threading.Thread(target=run, kwargs=dict(host='127.0.0.1', port=8081)).start()

    # /hello
    def index(self):
        return '<b>Hello {{name}}</b>!';
