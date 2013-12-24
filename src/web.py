#!/usr/local/bin/python

import BaseHTTPServer
import json
import mimetypes
import os.path
import threading

import events
import util


class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    webDir = os.path.join("..", "web")

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/":
            self.mainPage()
        elif self.path == "/test":
            self.testPage()
        elif self.path == "/trackInfo":
            self.trackInfo()
        elif self.path == "/prev":
            self.prev()
        elif self.path == "/next":
            self.next()
        elif self.path == "/play":
            self.play()
        elif self.path == "/pause":
            self.pause()
        elif self.path == "/stop":
            self.stop()
        else:
            self.sendFile(
                os.path.join(self.webDir, *self.path.split("/")))

    def do_POST(self):
        if self.path == "/changeScore":
            self.changeScore()

    def receiveJson(self):
        contentLength = int(self.headers.getheader('content-length'))
        return json.loads(self.rfile.read(contentLength))

    def send(self, page, error=200, mimeType=None):
        self.send_response(error)
        self.send_header("Content-Type", mimeType)
        self.end_headers()
        self.wfile.write(page)

    def sendFile(self, file, mimeType=None):
        if os.path.exists(file):
            content = open(file).read()
            error = 200
            mimeType = mimeType or mimetypes.guess_type(file)[0]
        else:
            content = "Unknown path: " + file
            error = 404
            mimeType = "text/plain"
        self.send(content, error=error, mimeType=mimeType)

    def prev(self):
        self.send("preved")
        self.server.postEvent(events.PreviousEvent())

    def next(self):
        self.send("nexted")
        self.server.postEvent(events.NextEvent())

    def play(self):
        self.send("played")
        self.server.postEvent(events.PlayEvent())

    def pause(self):
        self.send("paused")
        self.server.postEvent(events.PauseEvent())

    def stop(self):
        self.send("stopped")
        self.server.postEvent(events.StopEvent())

    def trackInfo(self):
        track = self.server.shared.getTrack(0)
        if track is None:
            self.send("")
            return
        self.send(track.getJson(), mimeType="application/json")

    def mainPage(self):
        self.sendFile(os.path.join(self.webDir, "main.html"))

    def testPage(self):
        self.sendFile(os.path.join(self.webDir, "test.html"))

    def changeScore(self):
        score = self.receiveJson()["score"]
        print score


class NQrServer(BaseHTTPServer.HTTPServer, util.EventPoster):

    def __init__(self, shared, window):
        BaseHTTPServer.HTTPServer.__init__(self, ("", 8000), RequestHandler)
        util.EventPoster.__init__(self, window, None, None)
        self.shared = shared
        self.count = 0


class WebThread(threading.Thread):

    def __init__(self, shared, window):
        threading.Thread.__init__(self)
        self._shared = shared
        self._eventWindow = window

    def run(self):
        httpd = NQrServer(self._shared, self._eventWindow)
        httpd.serve_forever()
