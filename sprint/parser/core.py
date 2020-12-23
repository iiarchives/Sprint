# Modules
import string
import inspect

import importlib
from os import listdir

from os.path import exists
from ..utils.logging import error

from .runtime.exec import Executer
from ..utils.bases import BaseCommand

from .runtime.globals import generate_globals

# Storage object
class Storage:
    pass

Storage.globals = generate_globals()

# Sprint parser
class SprintParser(object):

    def __init__(self):
        self.commands = self.load_commands()
        self.executer = Executer(self, self.commands)

    def load_commands(self, directory = "sprint/commands"):

        # Setup commands
        commands = {}

        # Check directory existance
        if not exists(directory):
            error("FileError", "The command directory could not be found.")

        # Locate all of our commands
        for file in listdir(directory):

            # Ensure this is a python file
            if not file.endswith(".py"):
                continue

            # Try to load it
            try:
                m = importlib.import_module(directory.replace("/", ".") + "." + file[:-3])

                # Scan for our class
                for name, _class in inspect.getmembers(m, inspect.isclass):

                    if _class == BaseCommand:
                        continue

                    elif issubclass(_class, BaseCommand):

                        # Initialize the class
                        init = _class(Storage)

                        # Locate the function
                        func = None
                        for n, f in inspect.getmembers(init, inspect.ismethod):
                            if n == file[:-3].lower():  # Check this is the command name
                                func = f

                        if func is None:
                            continue

                        # Load the class into our command list
                        commands[file[:-3]] = {
                            "class": init,
                            "function": func
                        }

            except Exception as err:
                error("LoadError", f"The '{file}' command failed to import properly.\nPython traceback: {err}")

        return commands

    def remove_whitespace(self, line):

        for char in line:
            if char in string.whitespace:
                line = line.replace(char, "", 1)
            else:
                return line  # No more whitespace remaining

        return line

    def convert_datatype(self, data):

        # Try and convert to an integer
        try:
            data = int(data)
        except ValueError:

            # Try it as a float?
            try:
                data = float(data)
            except ValueError:
                pass

            # Perhaps we can turn this into a boolean
            if data == "true":
                data = True
            elif data == "false":
                data = False

        # Should be either a string, integer, or boolean
        return data

    def execute(self, command):

        # Reinitialize globals
        Storage.globals = generate_globals() | Storage.globals

        # Ignore whitespace
        command = self.remove_whitespace(command)
        if not command:
            return

        # Format line with globals
        for glob in Storage.globals:
            command = command.replace(f"%{glob}", Storage.globals[glob])

        # Load our arguments
        args = command.split(" ")
        arguments = []

        in_string = False
        string_data = ""
        for arg in args:

            # Check if we aren't in a string
            if not in_string:

                # Is this the start of a string?
                if arg.startswith("\""):
                    in_string = True
                    string_data += arg[1:] + " "

                else:

                    # Normal argument
                    arguments.append(self.convert_datatype(arg))

            elif arg.endswith("\""):

                # The end of a string
                in_string = False
                string_data += arg[:-1]

                arguments.append(string_data)
                string_data = ""

            else:

                # In the middle of a string
                string_data += arg + " "

        # Process our arguments
        formatted_args = {
            "pos": [],
            "vals": {},
            "flags": []
        }

        base = arguments[0]
        arguments = arguments[1:]

        for argument in arguments:

            # Check for a flag
            if isinstance(argument, str) and argument.startswith("--"):
                argument = argument[2:]

                # Check for a value
                if argument.count("=") == 1:
                    values = argument.split("=")

                    key = values[0]
                    value = values[1]

                    if not key or not value:
                        return error("ArgumentError", f"Invalid argument supplied '{argument}'.")

                    if key in formatted_args["vals"]:
                        return error("ArgumentError", f"Key '{key}' is already assigned to.")

                    formatted_args["vals"][key] = self.convert_datatype(value)

                else:

                    # Normal flag
                    formatted_args["flags"].append(argument)

            else:

                # Normal positional argument
                formatted_args["pos"].append(argument)

        # Execute this line
        self.executer.execute(base, formatted_args)
