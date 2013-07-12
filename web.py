#!/usr/local/bin/python

import BaseHTTPServer
import threading

import events
import util
from Crypto.SelfTest import SelfTestError

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    def log_message(self, fmt, *args):
        pass
  
    def do_GET(self):
        #print 'GET', self.path
        if self.path == '/':
            self.mainPage()
        elif self.path == '/jquery':
            self.sendJQuery()
        elif self.path == '/nqr.js':
            self.sendNQrJS()
        elif self.path == '/count':
            self.sendCountAjax()
        elif self.path == '/test':
            self.testPage()
        elif self.path == '/trackInfo':
            self.trackInfo()
        elif self.path == '/prev':
            self.prev()
        elif self.path == '/next':
            self.next()
        elif self.path == '/play':
            self.play()
        elif self.path == '/pause':
            self.pause()
        elif self.path == '/stop':
            self.stop()
        else:
            self.send("no idea what to do with " + self.path, error=400)

    def send(self, page, error=200, mimeType='text/html'):
        self.send_response(error)
        self.send_header('Content-Type', mimeType)
        self.end_headers()
        self.wfile.write(page)

    def sendFile(self, file, mimeType='text/html'):
        self.sendFiles([file], mimeType)

    def sendFiles(self, files, mimeType='text/html'):
        content = ''
        for file in files:
            content += open(file).read()
        self.send(content, mimeType=mimeType)

    def prev(self):
        self.send('preved')
        self.server.postEvent(events.PreviousEvent())

    def next(self):
        self.send('nexted')
        self.server.postEvent(events.NextEvent())

    def play(self):
        self.send('played')
        self.server.postEvent(events.PlayEvent())

    def pause(self):
        self.send('paused')
        self.server.postEvent(events.PauseEvent())

    def stop(self):
        self.send('stopped')
        self.server.postEvent(events.StopEvent())

    def trackInfo(self):
        track = self.server.shared.getTrack(0)
        if track is None:
            self.send('')
            return
        self.send(track.getJson(), mimeType="application/json")

    def mainPage(self):
        self.sendFile('web/main.html')

    def testPage(self):
        self.sendFile('web/test.html')

    def sendJQuery(self):
        # http://ajax.googleapis.com/ajax/libs/jquery/2/jquery.min.js
        self.sendFiles(["web/jquery-2.0.3.min.js", "web/jquery.timers-1.2.js"],
                       mimeType='application/javascript')
    
    def sendNQrJS(self):
        self.sendFile("web/nqr.js", mimeType='application/javascript')

    def sendCountAjax(self):    
        self.send('<count>' + str(self.server.count) + '</count>',
                  mimeType='text/getXml')
        self.server.count += 1

class NQrServer(BaseHTTPServer.HTTPServer, util.EventPoster):
    
    def __init__(self, shared, window):
        BaseHTTPServer.HTTPServer.__init__(self, ('', 8000), RequestHandler)
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