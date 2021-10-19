# I think we still need logging?
from abc import ABC, abstractclassmethod
from enum import Enum
from typing import List

from rich import console


class LogLevels(Enum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    NOTSET = "not_set"


class BaseOutputter(ABC):
    """Represents an Outputter"""

    @abstractclassmethod
    def critical(self, to_output: str) -> None:
        raise NotImplementedError

    @abstractclassmethod
    def error(self, to_output: str) -> None:
        raise NotImplementedError

    @abstractclassmethod
    def warning(self, to_output: str) -> None:
        raise NotImplementedError

    @abstractclassmethod
    def info(self, to_output: str, Log) -> None:
        raise NotImplementedError

    @abstractclassmethod
    def debug(self, to_output: str) -> None:
        raise NotImplementedError


class CliOutputter(BaseOutputter):
    def info(to_output: str) -> None:
        console.print(to_output)


class FileOutputter(BaseOutputter):
    def __init__(self, filepath):
        self._filepath = filepath

    def info(self, to_output: str) -> None:
        with open(self._filepath, "a") as file:
            file.write(to_output)


class Logger:
    def __init__(self, outputters: List[BaseOutputter]):
        self._outputters = outputters

    def info(
        self,
        to_output: str,
    ) -> None:
        for outputter in self._outputters:
            outputter.info(to_output)


def get_cci_logger(name: str) -> Logger:
    """Returns a Logger object with the default outputters attached."""
    cli_outputter = CliOutputter()
    file_outputter = FileOutputter(get_next_logfile_path())
    return Logger([cli_outputter, file_outputter])


#################################
#          Example Usage
#################################
logger = get_cci_logger(__name__)
# ouputs to all attached outputters
logger.info("Hello logger!")
