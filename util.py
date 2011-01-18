# Utility functions and classes

import ConfigParser
import copy
import datetime
import logging
import os.path
import platform
import Queue
import threading
import traceback

#import wxversion
#wxversion.select([x for x in wxversion.getInstalled()
#                  if x.find('unicode') != -1])
#import wx

import errors
import events

wx = events.wx
VERSION_NUMBER = "0.1"
SYSTEM_NAME = platform.system()
MAC_NAMES = ["Mac OS X", "Darwin"]
WINDOWS_NAMES = ["Windows"]
FREEBSD_NAMES = ["FreeBSD"]


def plural(count):
    if count == 1:
        return ''
    return 's'


def formatLength(rawLength):
    minutes = rawLength // 60
    seconds = int(rawLength - minutes * 60)
    if seconds not in range(10):
        length = str(int(minutes)) + ":" + str(int(seconds))
    else:
        length = str(int(minutes)) + ":0" + str(int(seconds))
    return length


#def convertToUnicode(string, debugCompletion, logging=True):
#    return unicode(string, "mbcs") # the rest is now possibly unnecessary?
#    try:
#        unicodeString = unicode(string, "cp1252")
#    except UnicodeDecodeError:
#        if logging:
#            debugCompletion("Found bad characters. Attempting to resolve.")
#        unicodeString = u""
#        for char in string:
#            try:
#                unicodeString += unicode(char, "cp1252")
#            except UnicodeDecodeError as err:
#                errStr = str(err)
#                startIndex = errStr.index("0x")
#                endIndex = errStr.index(" ", startIndex)
#                hexStr = ""
#                for i in range(startIndex, endIndex):
#                    hexStr += errStr[i]
#                unicodeString += unichr(int(hexStr, 16))
#        if logging:
#            debugCompletion("Bad characters resolved.")
#    return unicodeString


def doNothing():
    pass


#def extractTraceStack(trace=None):
#    newTrace = traceback.extract_stack()[:-1]
#    if trace is None:
#        return newTrace
##    for index in range(len(trace)):
##        if trace[index] != newTrace[index]:
##            return trace + newTrace[index:]
##    return newTrace
#    return trace + newTrace


def getTrace(maybeTraceCallbackOrList=None):
    if isinstance(maybeTraceCallbackOrList, BaseCallback):
        return maybeTraceCallbackOrList.getTrace()[:-1]
    trace = traceback.extract_stack()[:-1]
    if maybeTraceCallbackOrList is not None:
        return maybeTraceCallbackOrList + trace
    return trace


def validateNumeric(textCtrl):
    text = textCtrl.GetValue()
    for char in text:
        if not char.isdigit():
            wx.MessageBox("Must be numeric only!", "Error")
            textCtrl.SetBackgroundColour("pink")
            textCtrl.SetFocus()
            textCtrl.Refresh()
            return False
    textCtrl.SetBackgroundColour(
        wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
    textCtrl.Refresh()
    return True


def validateDirectory(textCtrl):
    text = textCtrl.GetValue()
    if not os.path.isdir(text):
        wx.MessageBox("Must be existing directory path!", "Error")
        textCtrl.SetBackgroundColour("pink")
        textCtrl.SetFocus()
        textCtrl.Refresh()
        return False
    textCtrl.SetBackgroundColour(
        wx.SystemSettings_GetColour(wx.SYS_COLOUR_WINDOW))
    textCtrl.Refresh()
    return True


def _doRough(time, bigDivider, bigName, littleDivider, littleName):
    big = int((time + littleDivider / 2) / littleDivider / bigDivider)
    little = int(((time + littleDivider / 2) / littleDivider) % bigDivider)
    timeString = ""
    if big != 0:
        timeString = str(big) + " " + bigName + plural(big)
    if little != 0:
        if timeString is not "":
            timeString  += " " + str(little) + " " + littleName + plural(little)
        else:
            timeString = str(little) + " " + littleName + plural(little)
    return timeString


def roughAge(time):
    """
       Return a string roughly describing the time difference handed in.
    """
    if time < 60*60:
        return _doRough(time, 60, "minute", 1, "second")
    if time < 24*60*60:
        return _doRough(time, 60, "hour", 60, "minute")
    if time < 7*24*60*60:
        return _doRough(time, 24, "day", 60*60, "hour")
    if time < 365*24*60*60:
        return _doRough(time, 7, "week", 24*60*60, "day")
    # Yes, this measure of a year is fairly crap :-).
    return _doRough(time, 52, "year", 7*24*60*60, "week")


# FIXME: Implement for other systems (maybe see:
#        www.cyberciti.biz/faq/howto-display-list-of-all-installed-software/).
def getIsInstalled(softwareName):
    if SYSTEM_NAME in WINDOWS_NAMES:
        import wmi
        import _winreg
        
        result, names = wmi.Registry().EnumKey(
            hDefKey=_winreg.HKEY_LOCAL_MACHINE,
            sSubKeyName=r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
        if softwareName in names:
            return True
        return False
    return True


# FIXME: Implement updating.
def getUpdate():
    return None


def doUpdate():
    pass


def postEvent(lock, target, event):
    try:
        if lock is not None:
            with lock:
                wx.PostEvent(target, event)
        elif lock is None:
            wx.PostEvent(target, event)
    except TypeError as err:
        if str(err) != ("in method 'PostEvent', expected argument 1 of type"
                        + " 'wxEvtHandler *'"):
            raise
        raise errors.NoEventHandlerError


def postDebugLog(lock, target, logger, message):
    # TODO: Concurrency issue?
    if logger.isEnabledFor(logging.DEBUG):
        try:
            postEvent(lock, target, events.LogEvent(logger, "debug", message))
        except errors.NoEventHandlerError:
            logger.debug("(post error)" + message)


def postInfoLog(lock, target, logger, message):
    try:
        postEvent(lock, target, events.LogEvent(logger, "info", message))
    except errors.NoEventHandlerError:
        logger.info("(post error)" + message)


def postErrorLog(lock, target, logger, message):
    try:
        postEvent(lock, target, events.LogEvent(logger, "error", message))
    except errors.NoEventHandlerError:
        logger.error("(post error)" + message)


def postWarningLog(lock, target, logger, message):
    try:
        postEvent(lock, target, events.LogEvent(logger, "warning", message))
    except errors.NoEventHandlerError:
        logger.warning("(post error)" + message)


class EventPoster:
    
    def __init__(self, window, logger, lock):
        self._window = window
        self._logger = logger
        self._lock = lock
        
    def postEvent(self, event):
        postEvent(self._lock, self._window, event)

    def postDebugLog(self, message):
        postDebugLog(self._lock, self._window, self._logger, message)

    def postInfoLog(self, message):
        postInfoLog(self._lock, self._window, self._logger, message)

    def postErrorLog(self, message):
        postErrorLog(self._lock, self._window, self._logger, message)
        
    def postWarningLog(self, message):
        postWarningLog(self._lock, self._window, self._logger, message)


class RedirectText:
    
    def __init__(self, out, sysout):
        self._out = sysout
        self._out2 = out
        
    def write(self, string):
        self._out.write(string)
        start, end = self._out2.GetSelection()
        self._out2.AppendText(string)
        if start != end:
            self._out2.SetSelection(start, end)


class RedirectErr(RedirectText):
    
    def __init__(self, textCtrl, stderr):
        RedirectText.__init__(self, textCtrl, stderr)


class RedirectOut(RedirectText):
    
    def __init__(self, textCtrl, stdout):
        RedirectText.__init__(self, textCtrl, stdout)


class BaseCallback:
    # FIXME: Catch all errors and reraise with trace (poss done?).
    
    def __init__(self, completion, traceCallbackOrList=None):
        self._completion = completion
        self._trace = getTrace(traceCallbackOrList)[:-1]
        
    def getTrace(self):
        return getTrace(self._trace)[:-1]
    
    def _complete(self, *args, **kwargs):
        try:
            self._completion(*args, **kwargs)
        except errors.Error as err:
            if err.getTrace() is not None:
                raise
            raise err(trace=self.getTrace())


class Callback(BaseCallback):
    
    def __call__(self, *args, **kwargs):
        self._complete(self, *args, **kwargs)


class MultiCompletion(BaseCallback):
    
    def __init__(self, number, completion, traceCallback=None):
        BaseCallback.__init__(self, completion, traceCallback)
        self._slots = [None] * number
        self._puts = [False] * number
    
    def __call__(self, slot, value):
        if self._puts[slot]:
            raise errors.MultiCompletionPutError(trace=getTrace(self))
        self._slots[slot] = value
        self._puts[slot] = True
        if False not in self._puts:
            self._complete(*self._slots)        


class ErrorCompletion(BaseCallback):
    
    def __init__(self, exceptions, completion, traceCallbackOrList=None):
        BaseCallback.__init__(self, completion, traceCallbackOrList)
        if isinstance(exceptions, list):
            self._exceptions = exceptions
        else:
            self._exceptions = [exceptions]
    
    def __call__(self, err, *args, **kwargs):
        for exception in self._exceptions:
            if isinstance(err, exception) or err is exception:
                self._complete(*args, **kwargs)
                return
        raise err


class BasePrefsPage(wx.Panel):
    
    def __init__(self, parent, configParser, logger, sectionName, *args,
                 **kwargs):
        wx.Panel.__init__(self, parent)
        self._configParser = configParser
        self._logger = logger
        self._sectionName = sectionName
        self._setDefaults(*args, **kwargs)
        self._settings = {}
        try:
            self._configParser.add_section(self._sectionName)
        except ConfigParser.DuplicateSectionError:
            pass
        self._loadSettings()
        
    def savePrefs(self):
        self._logger.debug("Saving \'" + self._sectionName + "\' preferences.")
        for (name, value) in self._settings.items():
            self.setSetting(name, value)

    def setSetting(self, name, value):
        self._configParser.set(self._sectionName, name, str(value))
        
    def _setDefaults(self, *args, **kwargs): # Override me.
        pass
        
    def _loadSettings(self): # Override me.
        pass


class BaseThread(threading.Thread, EventPoster):
    
    def __init__(self, parent, name, logger, errcallback, lock,
                 raiseEmpty=False, doneQueueLength=50):
        """FIXME
        
        Arguments:
        
        - parent: the target for `wx.PostEvent()` if either the track changes
          or the end of the playlist is reached.
          
        - lock: the `threading.Lock()` shared by all threads with the same parent
          to prevent concurrency issues when calling `wx.PostEvent()`.
          
        - db: the database.
        
        - player: the player.
        
        - trackFactory: the track factory.
        
        - loggerFactory: the logger factory.
        
        - trackCheckDelay: the delay in seconds between checks of the player for track
          changes and end of playlist.
        
        """
        threading.Thread.__init__(self, name=name)
        EventPoster.__init__(self, parent, logger, lock)
        self._name = name
        self._errcallback = errcallback
        self._queue = Queue.PriorityQueue()
        self._doneQueue = CircularQueue(doneQueueLength)
        self._eventCount = 0
        self._abortCount = 0
        self._emptyCount = 0
        self._raisedEmpty = raiseEmpty
        self._interrupt = False
        self._runningLock = threading.Lock()
        
    def queue(self, thing, traceCallbackOrList=None, priority=2):
        thing = Callback(thing, traceCallbackOrList)
        self._eventCount += 1
        self._queue.put((priority, self._eventCount, thing))
        if self._raisedEmpty:
            self._raisedEmpty = False
            self._queueEmptyQueueCallback()
            
    def start_(self, trace=None):
        self._trace = getTrace(trace)
        self.start()

    def run(self):
        self.postDebugLog("Starting \'" + self._name + "\' thread.")
        with self._runningLock:
            self._run()
            while True:
                try:
                    self._pop()
                except errors.AbortThreadSignal:
                    if self._abortCount > 20: # FIXME: Make more deterministic.
                        self._abort()
                        break
                    self.abort()
                    self._abortCount += 1
                except errors.EmptyQueueError as err:
                    if self._emptyCount > 20: # FIXME: Make more deterministic.
                        if self._errcallback is not None:
                            self._raise(err, self._errcallback)
                        self._raisedEmpty = True
                    elif not self._raisedEmpty:
                        self._emptyCount += 1
                        self._queueEmptyQueueCallback()
            self.postDebugLog("\'" + self._name + "\' thread stopped.")

    def _run(self):
        pass
    
    def _pop(self):
        got = self._queue.get()
        self._doneQueue.append(got)
        self._queueCallback(got[2])
        self._abortCount = 0
        self._emptyCount = 0

    def _abort(self):
        pass

    def _queueCallback(self, completion, *args, **kwargs):
        completion(*args, **kwargs)
        
    def _raise(self, err, errcompletion=None):
        try:
            errcompletion(err)
        except:
            self.postEvent(events.ExceptionEvent(err))
        
    def _queueEmptyQueueCallback(self):
        self.queue(self._emptyQueueCallback, priority=999)
            
    def _emptyQueueCallback(self, thisCallback, *args, **kwargs):
        raise errors.EmptyQueueError(trace=thisCallback.getTrace())
        
    def setAbortInterrupt(self, interrupt):
        self._interrupt = interrupt
            
    def abort(self, abortMainThread=True):
        self._abortMainThread = abortMainThread
        if self._interrupt:
            priority = 0
        else:
            priority = 1000
        self.queue(self._abortCallback, priority=priority)
        
    def _abortCallback(self, thisCallback, *args, **kwargs):
        raise errors.AbortThreadSignal()
        
    def dumpQueue(self, filename, extraLines=0):
        dump = copy.copy(self._queue.queue)
        file = open(filename, "w")
        for item, time in self._doneQueue:
            if item is not None:
                file.write(self._dumpQueueFormatter(item, extraLines, time))
        file.write(("-" * 100 + "\n\n\n") * 2)
        for item in dump:
            file.write(self._dumpQueueFormatter(item, extraLines))
        file.close()
        
    def _dumpQueueFormatter(self, item, extraLines=0, time=None):
        trace = "\tTraceback (most recent call last):\n" + "".join([
                    line for line in traceback.format_list(
                        getTrace(item[2])[:-(8 + extraLines)])])
        traceHash = str(hash(trace))
        if time is None:
            time = datetime.datetime.now()
        return (time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] +
                "   Priority: "+str(item[0]) +
                "   Event Number: " + str(item[1]) +
                "   Object: " + str(item[2]) +
                "   Trace Hash: " + traceHash + "\n\n" +
                trace + "\n\n\n")
            
    def getRunningLock(self):
        return self._runningLock


class CircularQueue:
    
    def __init__(self, size):
        self._queue = [(None, None)]*size

    def append(self, item):
        self._queue.pop(0)
        self._queue.append((item, datetime.datetime.now()))
        
    def __getitem__(self, index):
        return self._queue[index][0], self._queue[index][1]


class EventLogger:
    
    def __init__(self, length=100):
        self._queue = CircularQueue(length)
        self("---INIT---", None)
        
    def __call__(self, eventString, event):
        self._queue.append((eventString, event))
        
    def done(self):
        self("---DONE---", None)
        
    def dump(self, filename):
        file = open(filename, "w")
        for item, time in self._queue:
            if item is not None:
                file.write(self._dumpFormatter(item, time))
        file.close()
        
    def _dumpFormatter(self, item, time=None):
        if time is None:
            time = datetime.datetime.now()
        return (time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] +
                "   Event: " + item[0] + "\n")
