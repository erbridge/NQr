#!/usr/local/bin/python

import BaseHTTPServer
import threading

import events
import util

class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  def log_message(self, fmt, *args):
    pass
  
  def do_GET(self):
    #print 'GET', self.path
    if self.path == '/':
      self.mainPage()
    elif self.path == '/jquery':
      self.sendJQuery()
    elif self.path == '/count':
      self.sendCountAjax()
    elif self.path == '/test':
      self.testPage()
    elif self.path == '/trackInfo':
      self.trackInfo()
    elif self.path == '/pause':
      self.pause()
    else:
      self.send("no idea what to do with " + self.path, error=400)

  def send(self, page, error=200, type='text/html'):
    self.send_response(error)
    self.send_header('Content-Type', type)
    self.end_headers()
    self.wfile.write(page)

  def sendFile(self, file, type='text/html'):
    self.sendFiles([file], type)

  def sendFiles(self, files, type='text/html'):
    content = ''
    for file in files:
      content += open(file).read()
    self.send(content, type=type)

  def pause(self):
    self.send('paused')
    self.server.postEvent(events.PauseEvent())

  def trackInfo(self):
    track = self.server.shared.getTrack(0)
    if track is None:
      self.send('')
      return
    self.send(track.xml().encode('utf-8'), type='text/xml')

  def mainPage(self):
    self.sendFile('web/main')

  def testPage(self):
    self.sendFile('web/test')

  def sendJQuery(self):
    self.sendFiles([ 'web/jquery-1.6.3.min.js', 'web/jquery.timers-1.2.js' ],
                   type='application/javascript')

  def sendCountAjax(self):    
    self.send('<count>' + str(self.server.count) + '</count>', type='text/xml')
    self.server.count += 1

class NQRServer(BaseHTTPServer.HTTPServer, util.EventPoster):
  def __init__(self, shared, window):
    BaseHTTPServer.HTTPServer.__init__(self, ('', 8000), RequestHandler)
    util.EventPoster.__init__(self, window, None, None)
    self.shared = shared
    self.count = 0

def web():
  httpd = NQRServer()
  httpd.serve_forever()

class WebThread(threading.Thread):
  def __init__(self, shared, window):
    threading.Thread.__init__(self)
    self._shared = shared
    self._eventWindow = window

  def run(self):
    httpd = NQRServer(self._shared, self._eventWindow)
    httpd.serve_forever()

if __name__ == '__main__':
  web()
