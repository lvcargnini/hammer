#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  hammer_vlsi.py
#  
#  Copyright 2017 Edward Wang <edward.c.wang@compdigitec.com>

from abc import ABCMeta, abstractmethod
from enum import Enum

from typing import Callable, Iterable, List, TypeVar

from functools import reduce

import importlib
import os
import subprocess
import sys

import hammer_config

# Need a way to bind the callbacks to the class...
def with_default_callbacks(cls):
    # TODO: think about how to remove default callbacks
    cls.add_callback(cls.callback_print)
    cls.add_callback(cls.callback_buffering)
    return cls

@with_default_callbacks
class HammerVLSILogging:
    """Singleton which handles logging in hammer-vlsi.

    This class is generally not intended to be used directly for logging, but through HammerVLSILoggingContext instead.
    """

    # Enable colour in logging?
    enable_colour = True # type: bool

    # If buffering is enabled, instead of printing right away, we will store it
    # into a buffer for later retrival.
    enable_buffering = False # type: bool

    # Enable printing the tag (e.g. "[synthesis] ...).
    enable_tag = True # type: bool

    # Explanation of logging levels:
    # DEBUG - for debugging only, too verbose for general use
    # INFO - general informational messages (e.g. "starting synthesis")
    # WARNING - things the user should check out (e.g. a setting uses something very usual)
    # ERROR - something gone wrong but the process can still continue (e.g. synthesis run failed), though the user should definitely check it out.
    # FATAL - an error which will abort the process immediately without warning (e.g. assertion failure)
    Level = Enum('Level', 'DEBUG INFO WARNING ERROR FATAL')

    # Various escape characters for colour output.
    COLOUR_BLUE = "\033[96m"
    COLOUR_GREY = "\033[37m"
    COLOUR_YELLOW = "\033[33m"
    COLOUR_RED = "\033[91m"
    COLOUR_RED_BG = "\033[101m"
    # Restore the default terminal colour.
    COLOUR_CLEAR = "\033[0m"

    # Some default callback implementations.
    @classmethod
    def callback_print(cls, message: str, level: Level, context: List[str] = []) -> None:
        """Default callback which prints a colour message."""
        print(cls.build_message(message, level, context))

    output_buffer = [] # type: List[str]
    @classmethod
    def callback_buffering(cls, message: str, level: Level, context: List[str] = []) -> None:
        """Get the current contents of the logging buffer and clear it."""
        if not cls.enable_buffering:
            return
        cls.output_buffer.append(cls.build_message(message, level, context))

    @classmethod
    def file_logger(cls, output_path: str, format_msg_callback: Callable[[str, Level, List[str]], str] = None) -> Callable[[str], None]:
        """Create a file logger which logs to the given file."""

        def build_log_message(message: str, level: "Level", context: List[str] = []) -> str:
            """Build a plain message for logs, without colour."""
            template = "{context} {level}: {message}"

            return template.format(context=cls.get_tag(context), level=level, message=message)

        f = open(output_path, "a")
        def file_callback(message: str, level: "Level", context: List[str] = []) -> None:
            if format_msg_callback:
                f.write(format_msg_callback(message, level, context) + "\n")
            else:
                f.write(build_log_message(message, level, context) + "\n")
        return file_callback

    # List of callbacks to call for logging.
    callbacks = [] # type: List[Callable[[str, Level, List[str]], None]]

    @classmethod
    def clear_callbacks(cls) -> None:
        """Clear the list of callbacks."""
        cls.callbacks = []

    @classmethod
    def add_callback(cls, callback: Callable[[str], None]) -> None:
        """Add a callback."""
        cls.callbacks.append(callback)

    @classmethod
    def context(cls, new_context: str = "") -> "HammerVLSILoggingContext":
        """
        Create a new context.

        :param new_context: Context name. Leave blank to get the global context.
        """
        if new_context == "":
            return HammerVLSILoggingContext([], cls)
        else:
            return HammerVLSILoggingContext([new_context], cls)

    @classmethod
    def get_colour_escape(cls, level: Level) -> str:
        """Colour table to translate level -> colour in logging."""
        table = {
            cls.Level.DEBUG: cls.COLOUR_GREY,
            cls.Level.INFO: cls.COLOUR_BLUE,
            cls.Level.WARNING: cls.COLOUR_YELLOW,
            cls.Level.ERROR: cls.COLOUR_RED,
            cls.Level.FATAL: cls.COLOUR_RED_BG
        }
        if level in table:
            return table[level]
        else:
            return ""

    @classmethod
    def debug(cls, message: str) -> None:
        """Create an debug-level log message."""
        return cls.log(message, cls.Level.DEBUG)

    @classmethod
    def info(cls, message: str) -> None:
        """Create an info-level log message."""
        return cls.log(message, cls.Level.INFO)

    @classmethod
    def warning(cls, message: str) -> None:
        """Create an warning-level log message."""
        return cls.log(message, cls.Level.WARNING)

    @classmethod
    def log(cls, message: str, level: Level, context: List[str] = []) -> None:
        """
        Log the given message at the given level in the given context.
        """
        for callback in cls.callbacks:
            callback(message, level, context)

    @classmethod
    def build_message(cls, message: str, level: Level, context: List[str] = []) -> str:
        """Build a colour message."""
        context_tag = cls.get_tag(context) # type: str

        output = "" # type: str
        output += cls.get_colour_escape(level) if cls.enable_colour else ""
        if cls.enable_tag and context_tag != "":
            output += context_tag + " "
        output += message
        output += cls.COLOUR_CLEAR if cls.enable_colour else ""

        return output

    @staticmethod
    def get_tag(context: List[str]) -> str:
        """Helper function to get the tag for outputing a message given a context."""
        if len(context) > 0:
            return str(reduce(lambda a, b: a + " " + b, map(lambda x: "[%s]" % (x), context)))
        else:
            return "[<global>]"

    @classmethod
    def get_buffer(cls) -> Iterable[str]:
        """Get the current contents of the logging buffer and clear it."""
        if not cls.enable_buffering:
            raise ValueError("Buffering is not enabled")
        output = list(cls.output_buffer)
        cls.output_buffer = []
        return output

VT = TypeVar('VT', bound='HammerVLSILoggingContext')
class HammerVLSILoggingContext:
    """
    Logging interface to hammer-vlsi which contains a context (list of strings denoting hierarchy where the log occurred).
    e.g. ["synthesis", "subprocess run-synthesis"]
    """
    def __init__(self, context: List[str], logging_class: HammerVLSILogging):
        """
        Create a new interface with the given context.
        """
        self._context = context # type: List[str]
        self.logging_class = logging_class # type: HammerVLSILogging

    def context(self: VT, new_context: str) -> VT:
        """
        Create a new subcontext from this context.
        """
        context2 = list(self._context)
        context2.append(new_context)
        return HammerVLSILoggingContext(context2, self.logging_class)

    # TODO: deduplicate these methods from the other class or merge things
    def debug(self, message: str) -> None:
        """Create an debug-level log message."""
        return self.log(message, self.logging_class.Level.DEBUG)

    def info(self, message: str) -> None:
        """Create an info-level log message."""
        return self.log(message, self.logging_class.Level.INFO)

    def warning(self, message: str) -> None:
        """Create an warning-level log message."""
        return self.log(message, self.logging_class.Level.WARNING)

    def error(self, message: str) -> None:
        """Create an error-level log message."""
        return self.log(message, self.logging_class.Level.ERROR)

    def fatal(self, message: str) -> None:
        """Create an fatal-level log message."""
        return self.log(message, self.logging_class.Level.FATAL)

    def log(self, message: str, level: HammerVLSILogging.Level) -> None:
        return self.logging_class.log(message, level, self._context)

import hammer_tech

class HammerVLSISettings:
    """
    Static class which holds global hammer-vlsi settings.
    """
    hammer_vlsi_path = "" # type: str

    @staticmethod
    def get_config() -> dict:
        """Export settings as a config dictionary."""
        return {
            "vlsi.builtins.hammer_vlsi_path": HammerVLSISettings.hammer_vlsi_path
        }

class HammerTool(metaclass=ABCMeta):
    # Interface methods.
    @abstractmethod
    def do_run(self) -> bool:
        """Run the tool after the setup.

        :return: True if the tool finished successfully; false otherwise.
        """
        pass

    # Setup functions.
    def run(self) -> bool:
        """Run this tool.

        Perform some setup operations to set up the config and tool environment, and then
        calls do_run() to invoke the tool-specific actions.

        :return: True if the tool finished successfully; false otherwise.
        """

        # Ensure that the run_dir exists.
        os.makedirs(self.run_dir, exist_ok=True)

        # Add HAMMER_DATABASE to the environment for the script.
        self._subprocess_env = os.environ.copy()
        self._subprocess_env.update({"HAMMER_DATABASE": self.dump_database()})

        return self.do_run()

    # Properties.
    @property
    def tool_dir(self) -> str:
        """
        Get the location of the tool library.

        :return: Path to the location of the library.
        """
        try:
            return self._tooldir
        except AttributeError:
            raise ValueError("Internal error: tool dir location not set by hammer-vlsi")

    @tool_dir.setter
    def tool_dir(self, value: str) -> None:
        """Set the directory which contains this tool library."""
        self._tooldir = value # type: str

    @property
    def run_dir(self) -> str:
        """
        Get the location of the run dir, a writable temporary information for use by the tool.

        :return: Path to the location of the library.
        """
        try:
            return self._rundir
        except AttributeError:
            raise ValueError("Internal error: run dir location not set by hammer-vlsi")

    @run_dir.setter
    def run_dir(self, value: str) -> None:
        """Set the location of a writable directory which the tool can use to store temporary information."""
        self._rundir = value # type: str

    @property
    def technology(self) -> hammer_tech.HammerTechnology:
        """
        Get the technology library currently in use.

        :return: HammerTechnology instance
        """
        try:
            return self._technology
        except AttributeError:
            raise ValueError("Internal error: technology not set by hammer-vlsi")

    @technology.setter
    def technology(self, value: hammer_tech.HammerTechnology) -> None:
        """Set the HammerTechnology currently in use."""
        self._technology = value # type: hammer_tech.HammerTechnology

    @property
    def logger(self) -> HammerVLSILoggingContext:
        """Get the logger for this tool."""
        try:
            return self._logger
        except AttributeError:
            raise ValueError("Internal error: logger not set by hammer-vlsi")

    @logger.setter
    def logger(self, value: HammerVLSILoggingContext) -> None:
        """Set the logger for this tool."""
        self._logger = value # type: HammerVLSILoggingContext

    # Accessory functions available to tools.
    # TODO(edwardw): maybe move set_database/get_setting into an interface like UsesHammerDatabase?
    def set_database(self, database: hammer_config.HammerDatabase) -> None:
        """Set the settings database for use by the tool."""
        self._database = database # type: hammer_config.HammerDatabase

    def dump_database(self) -> str:
        """Dump the current database JSON in a temporary file in the run_dir and return the path.
        """
        path = os.path.join(self.run_dir, "config_db_tmp.json")
        db_contents = self._database.get_database_json()
        open(path, 'w').write(db_contents)
        return path

    def get_config(self) -> List[dict]:
        """Get the config for this tool."""
        return hammer_config.load_config_from_defaults(self.tool_dir)

    def get_setting(self, key: str):
        """Get a particular setting from the database.
        """
        try:
            return self._database.get(key)
        except AttributeError:
            raise ValueError("Internal error: no database set by hammer-vlsi")

    # TODO(edwardw): consider pulling this out so that hammer_tech can also use this
    def run_executable(self, args: Iterable[str]) -> str:
        """
        Run an executable and log the command to the log while also capturing the output.

        :param args: Command-line to run; each item in the list is one token. The first token should be the command ot run.
        :return: Output from the command or an error message.
        """
        self.logger.debug("Executing subprocess: " + ' '.join(args))

        # Short version for easier display in the log.
        PROG_NAME_LEN = 14 # Capture last 14 characters of the command name
        if len(args[0]) <= PROG_NAME_LEN:
            prog_name = args[0]
        else:
            prog_name = "..." + args[0][len(args[0])-PROG_NAME_LEN:]
        remaining_args = " ".join(args[1:])
        if len(remaining_args) <= 15:
            prog_args = remaining_args
        else:
            prog_args = remaining_args[0:15] + "..."
        prog_tag = prog_name + " " + prog_args
        subprocess_logger = self.logger.context("Exec " + prog_tag)

        proc = subprocess.Popen(args, shell=False, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, env=self._subprocess_env)
        # Log output and also capture output at the same time.
        output_buf = ""
        while True:
            line = proc.stdout.readline().decode("utf-8")
            if line != '':
                subprocess_logger.debug(line.rstrip())
                output_buf += line
            else:
                break
        # TODO: check errors
        return line

class HammerSynthesisTool(HammerTool):
    ### Inputs ###

    @property
    def input_files(self) -> Iterable[str]:
        """
        Get the input collection of source RTL files (e.g. *.v).

        :return: The input collection of source RTL files (e.g. *.v).
        """
        try:
            return self._input_files
        except AttributeError:
            raise ValueError("Nothing set for the input collection of source RTL files (e.g. *.v) yet")

    @input_files.setter
    def input_files(self, value: Iterable[str]) -> None:
        """Set the input collection of source RTL files (e.g. *.v)."""
        if not isinstance(value, Iterable[str]):
            raise TypeError("input_files must be a Iterable[str]")
        self._input_files = value # type: Iterable[str]


    @property
    def top_module(self) -> str:
        """
        Get the top-level module.

        :return: The top-level module.
        """
        try:
            return self._top_module
        except AttributeError:
            raise ValueError("Nothing set for the top-level module yet")

    @top_module.setter
    def top_module(self, value: str) -> None:
        """Set the top-level module."""
        if not isinstance(value, str):
            raise TypeError("top_module must be a str")
        self._top_module = value # type: str


    ### Outputs ###

    @property
    def output_files(self) -> Iterable[str]:
        """
        Get the output collection of mapped (post-synthesis) RTL files.

        :return: The output collection of mapped (post-synthesis) RTL files.
        """
        try:
            return self._output_files
        except AttributeError:
            raise ValueError("Nothing set for the output collection of mapped (post-synthesis) RTL files yet")

    @output_files.setter
    def output_files(self, value: Iterable[str]) -> None:
        """Set the output collection of mapped (post-synthesis) RTL files."""
        if not isinstance(value, Iterable[str]):
            raise TypeError("output_files must be a Iterable[str]")
        self._output_files = value # type: Iterable[str]

class HammerPlaceAndRouteTool(HammerTool):
    pass

def load_tool(tool_name: str, path: Iterable[str]) -> HammerTool:
    """
    Load the given tool.
    See the hammer-vlsi README for how it works.

    :param tool_name: Name of the tool
    :param path: List of paths to get
    :return: HammerTool of the given tool
    """
    # Temporarily add to the import path.
    for p in path:
        sys.path.insert(0, p)
    try:
        mod = importlib.import_module(tool_name)
    except ImportError as e:
        raise ValueError("No such tool " + tool_name)
    # Now restore the original import path.
    for p in path:
        sys.path.pop(0)
    try:
        htool = getattr(mod, "tool")
    except AttributeError as e:
        raise ValueError("No such tool " + tool_name + ", or tool does not follow the hammer-vlsi tool library format")

    if not isinstance(htool, HammerTool):
        raise ValueError("Tool must be a HammerTool")

    # Set the tool directory.
    htool.tool_dir = os.path.dirname(os.path.abspath(mod.__file__))
    return htool
