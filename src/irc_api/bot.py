"""Provide a Bot class that react to IRC's message and events."""

import logging
import time
import re

from threading import Thread
from irc_api.irc import IRC
from irc_api.history import History


class Bot:
    """Watch the IRC server and handle commands.

    Attributes
    ----------
    prefix : str, public
        The bot's prefix for named command.
    irc : irc_api.irc.IRC, public
        IRC wrapper which handle communication with IRC server.
    history : irc_api.history.History, public
        The messages history. 
    channels : list, public
        The channels the bot will listen.
    auth : tuple, public
        This contains the username and the password for a SASL auth.
    callbacks : dict, public
        The callbacks of the bot. This dictionnary is like {name: command} where name is the name of
        the command and command a BotCommand's instance.
    commands_help : dict, public
        Same that ``callbacks`` but only with the documented commands. 
    threads : list, public
        A list of threads for the commands with ``@api.every``.

    Methods
    -------
    .. automethod:: __init__
    .. automethod:: add_command
    .. automethod:: add_commands
    .. automethod:: add_commands_module
    .. automethod:: remove_commands
    .. automethod:: send
    .. automethod:: start

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import api``
    You can create a bot::

        my_bot = api.Bot(
                irc_params=(irc.exemple.com, 6697),
                channels=["#general", "#bot-test"],
                prefix="!",
                cmnd_pack1, cmnd_pack2
            )
    """
    def __init__(
            self,
            irc_params: tuple,
            *commands_modules,
            auth: tuple=(),
            channels: list=["#general"],
            prefix: str="",
            limit: int=100,
        ):
        """Initialize the Bot instance.

        Parameters
        ----------
        irc_params : tuple
            A tuple like: (host, port) to connect to the IRC server.
        auth : tuple, optionnal
            Contains the IRC server informations (host, port).
        channels : list, optionnal
            Contains the names of the channels on which the bot will connect.
        prefix : str
            The bot's prefix for named commands.
        limit : int
            The message history of the bot. By default, the bot will remind 100 messages.
        *commands_module : optionnal
            Modules of commands that you can give to the bot at it's creation.
        """
        self.prefix = prefix

        self.irc = IRC(*irc_params)
        self.history = History(limit)
        self.channels = channels
        self.auth = auth
        self.callbacks = {}
        self.commands_help = {}
        self.threads = []

        if commands_modules:
            self.add_commands_modules(*commands_modules)

    def start(self, nick: str):
        """Start the bot and connect it to IRC. Handle the messages and callbacks too.

        Parameters
        ----------
        nick : str
            The nickname of the bot.
        """
        # Start IRC
        self.irc.connection(nick, self.auth)

        # Join channels
        for channel in self.channels:
            self.irc.join(channel)

        # mainloop
        while True:
            message = self.irc.receive()
            self.history.add(message)
            
            if message is not None:
                for callback in self.callbacks.values():
                    if not False in [event(message) for event in callback.events]:
                        logging.info("callback triggered: %s", callback.name)
                        # event commands
                        if callback.cmnd_type == 0:
                            callback(message)

                        # named commands
                        elif callback.cmnd_type == 1:
                            args = check_args(callback.func, *parse(message.text)[1:])
                            if isinstance(args, list):
                                callback(message, *args)
                            else:
                                self.send(
                                        message.to,
                                        "Error: arguments mismatch."
                                    )

    def send(self, target: str, message: str):
        """Send a message to the specified target (channel or user).

        Parameters
        ----------
        target : str
            The target of the message. It can be a channel or user (private message).
        message : str
            The content of the message to send.
        """
        for line in message.splitlines():
            self.irc.send(f"PRIVMSG {target} :{line}")

    def add_command(self, command, add_to_help: bool=False):
        """Add a single command to the bot.

        Parameters
        ----------
        command : BotCommand
            The command to add to the bot.
        add_to_help : bool, optionnal
            If the command should be added to the documented functions.
        """
        command.bot = self

        if command.cmnd_type == 1:
            command.events.append(
                    lambda m: True in \
                    [m.text == self.prefix + cmd or m.text.startswith(f"{self.prefix}{cmd} ")
                    for cmd in command.alias]
                )

        if command.cmnd_type == 2:
            def timed_func(bot):
                while True:
                    command.func(bot)
                    time.sleep(command.events)
                    logging.info("automatic callback: %s", command.name)
                    

            self.threads.append(Thread(target=timed_func, args=(self,)))
            self.threads[-1].start()
        else:
            self.callbacks[command.name] = command

        if add_to_help:
            self.commands_help[command.name] = command

    def add_commands(self, *commands):
        """Add a list of commands to the bot.

        Parameters
        ----------
        *commands
            The commands' instances.
        """
        add_to_help = "auto_help" in [cmnd.name for cmnd in commands]
        for command in commands:
            self.add_command(command, add_to_help=add_to_help)

    def add_commands_modules(self, *commands_modules):
        """Add a module of commands to the bot. You can give several modules.

        Parameters
        ----------
        *commands
            The commands modules to add to the bot.
        """
        for commands_module in commands_modules:
            add_to_help = "auto_help" in dir(commands_module)
            for cmnd_name in dir(commands_module):
                cmnd = getattr(commands_module, cmnd_name)
                if isinstance(cmnd, BotCommand):
                    self.add_command(cmnd, add_to_help=add_to_help)

    def remove_command(self, command_name: str):
        """Remove a command.

        Parameters
        ----------
        command_name : str
            The name of the command to delete.
        """
        if command_name in self.callbacks:
            self.callbacks.pop(command_name)
            self.commands_help.pop(command_name)


class BotCommand:
    """Implement a bot command.

    Attributes
    ----------
    name : str, public
        The name of the command.
    func : function, public
        The function to execute when the BotCommand is called.
    events : list, public
        The list of the conditions on which the BotCommand will be called.
    desc : str, public
        The description of the BotCommand. By default, the function's docstring is used.
    cmnd_type : int, public
        The type of the command.
        * if ``cmnd_type = 0``, the command is triggered on an event.
        * if ``cmnd_type = 1``, the command is a named command.
        * if ``cmnd_type = 2``, the command is a routine automatically triggered.
    bot : irc_api.bot.Bot, public
        The bot the command belongs to.
    """
    def __init__(self, name: str, func, events: list, desc: str, cmnd_type: int):
        """Constructor method.

        Parameters
        ----------
        name : str
            The name of the command.
        func : function
            The function to execute when the BotCommand is called.
        events : list
            The list of the conditions on which the BotCommand will be called.
        desc : str
            The description of the BotCommand. By default, the function's docstring is used.
        cmnd_type : int
            The type of the command.
            * if ``cmnd_type = 0``, the command is triggered on an event.
            * if ``cmnd_type = 1``, the command is a named command.
            * if ``cmnd_type = 2``, the command is a routine automatically triggered.
        """
        self.name = name
        self.func = func
        self.events = events
        self.cmnd_type = cmnd_type

        if desc:
            self.desc = desc
        else:
            self.desc = "..."
            if func.__doc__:
                self.desc = func.__doc__

        self.bot = None

    def __call__(self, msg, *args):
        """Call the function with the message that trigger the command and the given arguments.

        Parameters
        ----------
        msg : irc_api.message.Message
            The message that triggered the BotCommand.
        *args
            The arguments to give to the function.

        Returns
        -------
        out
            The output of ``BotCommand.func``.
        """
        return self.func(self.bot, msg, *args)


class WrongArg:
    """If the transtyping has failed and the argument has no default value."""


def parse(message):
    """Parse the given message to detect the command and the arguments. If a command's name is
    'cmnd' and the bot receive the message ``cmnd arg1 arg2`` this function will returns
    ``[arg1, arg2]``. It allows to have a powerfull commands with custom arguments.

    Parameters
    ----------
    message : irc_api.irc.Message
        The message to parse.

    Returns
    -------
    args_to_return : list
        The list of the given arguments in the message.
    """
    pattern = re.compile(r"((\"[^\"]+\"\ *)|(\'[^\']+\'\ *)|([^\ ]+\ *))", re.IGNORECASE)
    args_to_return = []
    for match in re.findall(pattern, message):
        match = match[0].strip().rstrip()
        if (match.startswith("\"") and match.endswith("\"")) \
                or (match.startswith("'") and match.endswith("'")):
            args_to_return.append(match[1: -1])
        else:
            args_to_return.append(match)
    return args_to_return


def convert(data, new_type: type, default=None):
    """Transtype a given variable into a given type. Returns a default value in case of failure.

    Parameters
    ----------
    data
        The given data to transtype.
    new_type : type


    """
    try:
        return new_type(data)
    except ValueError:
        return default


def check_args(func, *input_args):
    """Check if the given args fit to the function in terms of number and type.

    Parameters
    ----------
    func : function
        The function the user wants to run.
    *input_args
        The arguments given by the user.

    Returns
    -------
    converted_args : list
        The list of the arguments with the right type. The surplus arguments are ignored.
    """
    # gets the defaults values given in arguments
    defaults = getattr(func, "__defaults__")
    if not defaults:
        defaults = []

    # gets the arguments and their types
    annotations = getattr(func, "__annotations__")
    if not annotations:
        return []

    # number of required arguments
    required_args = len(annotations) - len(defaults)

    # if the number of given arguments just can't match
    if len(input_args) < required_args:
        return None

    wrong_arg = WrongArg()
    converted_args = []
    for index, arg_type in enumerate(annotations.values()):
        # construction of a tuple (type, default_value) for each expected argument
        if index + 1 > required_args:
            checked_args = (arg_type, defaults[index - required_args])
        else:
            checked_args = (arg_type, wrong_arg)

        # transtypes each given arguments to its target type
        if len(input_args) > index:
            converted_args.append(convert(input_args[index], *checked_args))
        else:
            converted_args.append(checked_args[1])

    # if an argument has no default value and transtyping has failed
    if wrong_arg in converted_args:
        return None

    return converted_args
