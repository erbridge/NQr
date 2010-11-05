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

class RedirectText:
    def __init__(self, textCtrl):
        self._out = textCtrl

    def write(self, string):
        self._out.WriteText(string)
