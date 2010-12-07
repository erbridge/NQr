## Logger

import logging
import datetime

class LoggerFactory:
    def __init__(self, debugMode=False):
        self._debugMode = debugMode

        dateString = str(
            datetime.datetime.strftime(datetime.datetime.utcnow(),
                                       '%Y%m%d_%H%M%S'))

        debugLogFilename = "logs/debug_"+dateString+".log"
        infoLogFilename = "logs/info_"+dateString+".log"
        errorLogFilename = "logs/error_"+dateString+".log"

        self._formatter = logging.Formatter(
            "%(asctime)s   %(name)-17s %(levelname)-10s %(message)s",
            "%Y-%m-%d %H:%M:%S")

        self._commandLineHandler = logging.StreamHandler()
        self._commandLineHandler.setLevel(logging.DEBUG)
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

    def getLogger(self, name, level):
        logger = logging.getLogger(name)
        if level == "debug":
            if self._debugMode == True:
                logger.setLevel(logging.DEBUG)
            elif self._debugMode == False:
                logger.setLevel(logging.INFO)
            else:
                self._logger.error(str(self.debugMode)\
                                   +" is an invalid debug mode.")
                raise ValueError(str(self.debugMode)\
                                 +" is an invalid debug mode.")
        elif level == "error":
            logger.setLevel(logging.ERROR)
        else:
            self._logger.error(str(level)+" is an invalid level for logger.")
            raise ValueError(str(level)+" is an invalid level for logger.")
        return logger

    def refreshStreamHandler(self):
        logging.getLogger("NQr").removeHandler(self._commandLineHandler)
        
        self._commandLineHandler = logging.StreamHandler()
        self._commandLineHandler.setLevel(logging.DEBUG)
        self._commandLineHandler.setFormatter(self._formatter)
        logging.getLogger("NQr").addHandler(self._commandLineHandler)
