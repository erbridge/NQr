## GUI Events

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

ID_EVT_TRACK_CHANGE = wx.NewId()

def EVT_TRACK_CHANGE(window, func):
    window.Connect(-1, -1, ID_EVT_TRACK_CHANGE, func)

class TrackChangeEvent(wx.PyEvent):
    def __init__(self, db, trackFactory, path):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_TRACK_CHANGE)
        self._db = db
        self._trackFactory = trackFactory
        self._path = path

    def getTrack(self):
        return self._trackFactory.getTrackFromPath(self._db, self._path)
    
ID_EVT_NO_NEXT_TRACK = wx.NewId()

def EVT_NO_NEXT_TRACK(window, func):
    window.Connect(-1, -1, ID_EVT_NO_NEXT_TRACK, func)

class NoNextTrackEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_NO_NEXT_TRACK)
        
ID_EVT_REQUEST_ATTENTION = wx.NewId()

def EVT_REQUEST_ATTENTION(window, func):
    window.Connect(-1, -1, ID_EVT_REQUEST_ATTENTION, func)

class RequestAttentionEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_REQUEST_ATTENTION)
        
ID_EVT_PAUSE = wx.NewId()

def EVT_PAUSE(window, func):
    window.Connect(-1, -1, ID_EVT_PAUSE, func)

class PauseEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_PAUSE)

ID_EVT_PLAY = wx.NewId()

def EVT_PLAY(window, func):
    window.Connect(-1, -1, ID_EVT_PLAY, func)

class PlayEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_PLAY)
        
ID_EVT_STOP = wx.NewId()

def EVT_STOP(window, func):
    window.Connect(-1, -1, ID_EVT_STOP, func)

class StopEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_STOP)
        
ID_EVT_NEXT = wx.NewId()

def EVT_NEXT(window, func):
    window.Connect(-1, -1, ID_EVT_NEXT, func)

class NextEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_NEXT)
        
ID_EVT_PREV = wx.NewId()

def EVT_PREV(window, func):
    window.Connect(-1, -1, ID_EVT_PREV, func)

class PreviousEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_PREV)
        
ID_EVT_RATE_UP = wx.NewId()

def EVT_RATE_UP(window, func):
    window.Connect(-1, -1, ID_EVT_RATE_UP, func)

class RateUpEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_RATE_UP)
        
ID_EVT_RATE_DOWN = wx.NewId()

def EVT_RATE_DOWN(window, func):
    window.Connect(-1, -1, ID_EVT_RATE_DOWN, func)

class RateDownEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_RATE_DOWN)