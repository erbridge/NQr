import math

def plural(count):
    if count == 1:
        return ''
    return 's'

def formatLength(rawLength):
    minutes = math.floor(rawLength / 60)
    seconds = math.floor(rawLength - math.floor(rawLength / 60) * 60)
    if seconds not in range(10):
        length = str(int(minutes))+":"+str(int(seconds))
    else:
        length = str(int(minutes))+":0"+str(int(seconds))
    return length

def convertToUnicode(string, logger, logging=True):
    unicodeString = u""
    try:
        unicodeString = unicode(string)
    except UnicodeDecodeError:
        if logging == True:
            logger.warning("Found bad characters. Attempting to resolve.")
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
    
    def put(self, slot, value):
        self._slots[slot] = value
        if None not in self._slots:
            self._complete()
        
    def _complete(self):
        self._completion(*self._slots)
        