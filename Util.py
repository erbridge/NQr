## Utility function and classes

import ConfigParser
from Errors import MultiCompletionPutError
import Events
import os.path
import traceback

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

def plural(count):
    if count == 1:
        return ''
    return 's'

def formatLength(rawLength):
    minutes = rawLength // 60
    seconds = int(rawLength - minutes * 60)
    if seconds not in range(10):
        length = str(int(minutes))+":"+str(int(seconds))
    else:
        length = str(int(minutes))+":0"+str(int(seconds))
    return length

def convertToUnicode(string, logger, logging=True):
    try:
        unicodeString = unicode(string)
    except UnicodeDecodeError:
        if logging == True:
            logger.warning("Found bad characters. Attempting to resolve.")
        unicodeString = u""
        for char in string:
            try:
                unicodeString += unicode(char)
            except UnicodeDecodeError as err:
                errStr = str(err)
                startIndex = errStr.index("0x")
                endIndex = errStr.index(" ", startIndex)
                hexStr = ""
                for i in range(startIndex, endIndex):
                    hexStr += errStr[i]
                
                unicodeString += unichr(int(hexStr, 16))
        
        if logging == True:
            logger.warning("Bad characters resolved.")
    return unicodeString
        
def doNothing():
    pass

def extractTraceStack(trace):
    newTrace = traceback.extract_stack()[:-1]
    if trace == None:
        return newTrace
    for index in range(len(trace)):
        if trace[index] != newTrace[index]:
            return trace + newTrace[index:]
    return trace

def validateNumeric(textCtrl):
    text = textCtrl.GetValue()
    for char in text:
        if char.isdigit() == False:
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
    if os.path.isdir(text) == False:
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
        timeString = str(big)+" "+bigName+plural(big)
    if little != 0:
        if timeString != "":
            timeString += " "+str(little)+" "+littleName+plural(little)
        else:
            timeString = str(little)+" "+littleName+plural(little)
    return timeString

# Return a string roughly describing the time difference handed in.
def roughAge(time):
    if time < 60*60:
        return _doRough(time, 60, "minute", 1, "second")
    if time < 24*60*60:
        return _doRough(time, 60, "hour", 60, "minute")
    if time < 7*24*60*60:
        return _doRough(time, 24, "day", 60*60, "hour")
    if time < 365*24*60*60:
        return _doRough(time, 7, "week", 24*60*60, "day")
    # yes, this measure of a year is fairly crap :-)
    return _doRough(time, 52, "year", 7*24*60*60, "week")

def postEvent(lock, target, event):
    if lock != None and lock.acquire():
        wx.PostEvent(target, event)
        lock.release()
    elif lock == None:
        wx.PostEvent(target, event)
        
def postDebugLog(lock, target, logger, message):
    postEvent(lock, target, Events.LogEvent(logger, "debug", message))
    
def postInfoLog(lock, target, logger, message):
    postEvent(lock, target, Events.LogEvent(logger, "info", message))
    
def postErrorLog(lock, target, logger, message):
    postEvent(lock, target, Events.LogEvent(logger, "error", message))
    
class RedirectErr:
    def __init__(self, textCtrl, stderr):
        self._out = textCtrl
        self._out2 = stderr

    def write(self, string):
        self._out.WriteText(string)
        self._out2.write(string)
        
class RedirectOut:
    def __init__(self, textCtrl, stdout):
        self._out = textCtrl
        self._out2 = stdout

    def write(self, string):
        self._out.WriteText(string)
        self._out2.write(string)
        
class MultiCompletion:
    def __init__(self, number, completion):
        self._completion = completion
        self._slots = [None] * number
        self._puts = [False] * number
    
    def put(self, slot, value):
        if self._puts[slot] == True:
            raise MultiCompletionPutError
        self._slots[slot] = value
        self._puts[slot] = True
        if False not in self._puts:
            self._complete()
        
    def _complete(self):
        self._completion(*self._slots)
        
class ErrorCompletion:
    def __init__(self, exceptions, completion):
        if isinstance(exceptions, list):
            self._exceptions = exceptions
        else:
            self._exceptions = [exceptions]
        self._completion = completion
    
    def __call__(self, err, *args, **kwargs):
        for exception in self._exceptions:
            if isinstance(err, exception) or err == exception:
                self._completion(*args, **kwargs)
                return
        raise err
    
class BasePrefsPage(wx.Panel):
    def __init__(self, parent, system, configParser, logger, sectionName, *args,
                 **kwargs):
        wx.Panel.__init__(self, parent)
        self._system = system
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
        self._logger.debug("Saving \'"+self._sectionName+"\' preferences.")
        for (name, value) in self._settings.items():
            self.setSetting(name, value)

    def setSetting(self, name, value):
        self._configParser.set(self._sectionName, name, str(value))
        
    def _setDefaults(self, *args, **kwargs): # override me
        pass
        
    def _loadSettings(self): # override me
        pass