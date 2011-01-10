## Logger

import datetime
import logging
import os.path

class LoggerFactory:
    def __init__(self, logAge, debugMode):
        self._debugMode = debugMode

        dateString = str(
            datetime.datetime.strftime(datetime.datetime.utcnow(),
                                       '%Y%m%d_%H%M%S'))
        
        self.cleanDirectory(logAge) # removes logs older than logAge days

        debugLogFilename = "logs/debug_"+dateString+".log"
        infoLogFilename = "logs/info_"+dateString+".log"
        errorLogFilename = "logs/error_"+dateString+".log"

        self._formatter = logging.Formatter(
            "%(asctime)s.%(msecs)03d   %(name)-17s %(levelname)-10s "\
            +"%(message)s", "%Y-%m-%d %H:%M:%S")

        self._commandLineHandler = logging.StreamHandler()
        if self._debugMode == True:
            self._commandLineHandler.setLevel(logging.DEBUG)
        else:
            self._commandLineHandler.setLevel(logging.INFO)
        self._commandLineHandler.setFormatter(self._formatter)
        logging.getLogger("NQr").addHandler(self._commandLineHandler)

        if self._debugMode == True:
            debugFileHandler = logging.FileHandler(debugLogFilename, delay=True)
            debugFileHandler.setLevel(logging.DEBUG)
            debugFileHandler.setFormatter(self._formatter)
            logging.getLogger("NQr").addHandler(debugFileHandler)

        infoFileHandler = logging.FileHandler(infoLogFilename, delay=True)
        infoFileHandler.setLevel(logging.INFO)
        infoFileHandler.setFormatter(self._formatter)
        logging.getLogger("NQr").addHandler(infoFileHandler)

        errorFileHandler = logging.FileHandler(errorLogFilename, delay=True)
        errorFileHandler.setLevel(logging.ERROR)
        errorFileHandler.setFormatter(self._formatter)
        logging.getLogger("NQr").addHandler(errorFileHandler)

        self._logger = self.getLogger("NQr.Logger", "debug")
        
    def cleanDirectory(self, days): # set days to -1 to save all logs
        if days == -1:
            return
        now = datetime.datetime.utcnow()
        limit = now - datetime.timedelta(days=days)
        for log in os.listdir("logs"):
            name, ext = os.path.splitext(log)
            if ext != ".log":
                continue
            time = datetime.datetime.strptime(
                    name.split("_")[1]+name.split("_")[2], '%Y%m%d%H%M%S')
            path = os.path.join("logs", log)
            if time < limit:
                os.remove(path)

    def getLogger(self, name, level):
        logger = logging.getLogger(name)
        if level == "debug":
            if self._debugMode == True:
                logger.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.INFO)
        elif level == "error":
            logger.setLevel(logging.ERROR)
        else:
            self._logger.error(str(level)+" is an invalid level for logger.")
            raise ValueError(str(level)+" is an invalid level for logger.")
        return logger

    def refreshStreamHandler(self):
        logging.getLogger("NQr").removeHandler(self._commandLineHandler)
        
        self._commandLineHandler = logging.StreamHandler()
        if self._debugMode == True:
            self._commandLineHandler.setLevel(logging.DEBUG)
        else:
            self._commandLineHandler.setLevel(logging.INFO)
        self._commandLineHandler.setFormatter(self._formatter)
        logging.getLogger("NQr").addHandler(self._commandLineHandler)
