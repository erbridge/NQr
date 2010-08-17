## Logger

import logging
import datetime

class LoggerFactory:
    def __init__(self):
        dateString = str(
            datetime.datetime.strftime(datetime.datetime.utcnow(),
                                       '%Y%m%d_%H%M%S'))

        debugLogFilename = "logs/debug_"+dateString+".log"
        errorLogFilename = "logs/error_"+dateString+".log"

        formatter = logging.Formatter(
            "%(asctime)s   %(name)-13s %(levelname)-8s %(message)s",
            "%Y-%m-%d %H:%M:%S")

        commandLineHandler = logging.StreamHandler()
        commandLineHandler.setLevel(logging.DEBUG)
        commandLineHandler.setFormatter(formatter)

        debugFileHandler = logging.FileHandler(debugLogFilename, delay=True)
        debugFileHandler.setLevel(logging.DEBUG)
        debugFileHandler.setFormatter(formatter)

        errorFileHandler = logging.FileHandler(errorLogFilename, delay=True)
        errorFileHandler.setLevel(logging.ERROR)
        errorFileHandler.setFormatter(formatter)

        logging.getLogger("NQr").addHandler(commandLineHandler)
        logging.getLogger("NQr").addHandler(debugFileHandler)
        logging.getLogger("NQr").addHandler(errorFileHandler)

        self._logger = logging.getLogger("NQr.Logger")
        self._logger.setLevel(logging.DEBUG)

    def getLogger(self, name, level):
        logger = logging.getLogger(name)
        if level == "debug":
            logger.setLevel(logging.DEBUG)
        elif level == "error":
            logger.setLevel(logging.ERROR)
        else:
            self._logger.error("Invalid level set for logger.")
            raise ValueError(str(level)+" is an invalid level for logger.")
        return logger
