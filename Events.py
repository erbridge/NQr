## GUI Events

#from Util import wx
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
        
ID_EVT_DATABASE = wx.NewId()

def EVT_DATABASE(handler, func):
    handler.Connect(-1, -1, ID_EVT_DATABASE, func)

class DatabaseEvent(wx.PyEvent):
    def __init__(self, completion, result=None, returnData=True):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_DATABASE)
        self._result = result
        self._completion = completion
        self._returnData = returnData
        
    def complete(self):
        if self._returnData == True:
            self._completion(self._result)
        else:
            self._completion()
        
ID_EVT_EXCEPTION = wx.NewId()

def EVT_EXCEPTION(handler, func):
    handler.Connect(-1, -1, ID_EVT_EXCEPTION, func)

class ExceptionEvent(wx.PyEvent):
    def __init__(self, err):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_EXCEPTION)
        self._err = err
        
    def getException(self):
        return self._err
    
ID_EVT_LOG = wx.NewId()

def EVT_LOG(handler, func):
    handler.Connect(-1, -1, ID_EVT_LOG, func)

class LogEvent(wx.PyEvent):
    def __init__(self, logger, level, message):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_LOG)
        self._logger = logger
        self._level = level
        self._message = message
        
    def doLog(self):
        if self._level == "debug":
            self._logger.debug(self._message)
        elif self._level == "info":
            self._logger.info(self._message)
        elif self._level == "error":
            self._logger.error(self._message)
        elif self._level == "warning":
            self._logger.warning(self._message)

ID_EVT_ENQUEUE_RANDOM = wx.NewId()

def EVT_ENQUEUE_RANDOM(handler, func):
    handler.Connect(-1, -1, ID_EVT_ENQUEUE_RANDOM, func)

class EnqueueRandomEvent(wx.PyEvent):
    def __init__(self, number, tags=None):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_ENQUEUE_RANDOM)
        self._number = number
        self._tags = tags
        
    def getNumber(self):
        return self._number

    def getTags(self):
        return self._tags

ID_EVT_CHOOSE_TRACKS = wx.NewId()

def EVT_CHOOSE_TRACKS(handler, func):
    handler.Connect(-1, -1, ID_EVT_CHOOSE_TRACKS, func)

class ChooseTracksEvent(wx.PyEvent):
    def __init__(self, number, exclude, completion, tags=None):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_CHOOSE_TRACKS)
        self._number = number
        self._exclude = exclude
        self._completion = completion
        self._tags = tags
        
    def getNumber(self):
        return self._number

    def getExclude(self):
        return self._exclude

    def getCompletion(self):
        return self._completion

    def getTags(self):
        return self._tags
