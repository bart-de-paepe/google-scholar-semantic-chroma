import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOGGING_FILENAME = os.getenv("LOGGING_FILENAME")
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL")
class LoggingService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        filename = os.path.join(str(Path(__file__).parent.parent.parent.parent), 'log', LOGGING_FILENAME)
        match LOGGING_LEVEL:
            case "DEBUG":
                logging.basicConfig(handlers=[TimedRotatingFileHandler(filename, when='D', interval=1)], encoding='utf-8', level=logging.DEBUG)
            case "INFO":
                logging.basicConfig(handlers=[TimedRotatingFileHandler(filename, when='D', interval=1)], encoding='utf-8', level=logging.INFO)
            case "WARNING":
                logging.basicConfig(handlers=[TimedRotatingFileHandler(filename, when='D', interval=1)], encoding='utf-8', level=logging.WARNING)
            case "ERROR":
                logging.basicConfig(handlers=[TimedRotatingFileHandler(filename, when='D', interval=1)], encoding='utf-8', level=logging.ERROR)