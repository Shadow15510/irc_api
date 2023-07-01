import logging
import re
from irc_api.irc import IRC, History
from threading import Thread
import time


PREFIX = ""


def command(name: str, alias: tuple=(), desc: str=""):
    """Create a new bot's command. Note that's a decorator.
    
    Parameters
    ----------
    name : str
        The name of the command; i.e. the string by which the command will be called.
    alias : tuple, optionnal
        The others name by which the command will be called (in addition to the given name).
        This parameter can be left empty if the command has no alias.
    desc : str, optionnal
        This is the description of the command. It allows you to make an auto-generated
        documentation with this field.

    Returns
    -------
    decorator : function
        This function take in argument the function you want to transform into a command and returns
        a Command's instance.

    Examples
    --------
    For example, assuming the module was imported as follow: ``from irc_api import api``
    You can make a command::
        @api.command(name="ping", desc="Answer 'pong' when the user enters 'ping'.")
        def foo(bot, message):
            bot.send(message.to, "pong")
    """
    if not alias or not name in alias:
        alias += (name,)
    def decorator(func):
        return Command(
                name=name,
                func=func,
                events=[lambda m: True in [m.text == PREFIX + cmd or m.text.startswith(PREFIX + cmd + " ") for cmd in alias]],
                desc=desc,
                cmnd_type=1
            )
    return decorator


def on(event, desc: str=""):
    """Make a command on a custom event. It can be useful if you want to have a complex calling
    processus. Such as a regex recognition or a specific pattern. This decorator allows you to call
    a command when a specific event is verified.
    
    Parameters
    ----------
    event : function
        The ``event`` function should take the processed message (please refer to
        irc_api.irc.Message for more informations) in argument and returns a bool's instance.
    desc : str, optionnal
        This is the description of the command. It allows you to make an auto-generated
        documentation with this field.

    Returns
    -------
    decorator : function
        This function take in argument the function you want to transform into a command and returns
        a Command's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import api``
    You can make a new command::
        @api.on(lambda m: isinstance(re.match(r"(.*)(merci|merci beaucoup|thx|thanks|thank you)(.*)", m.text, re.IGNORECASE), re.Match))
        def thanks(bot, message):
            bot.send(message.to, f"You're welcome {message.author}! ;)")
    """
    def decorator(func_or_cmnd):
        if isinstance(func_or_cmnd, Command):
            func_or_cmnd.events.append(event)
            return func_or_cmnd
        else:
            return Command(
                    name=func_or_cmnd.__name__,
                    func=func_or_cmnd,
                    events=[event],
                    desc=desc,
                    cmnd_type=0
                )
    return decorator


def channel(channel_name: str, desc: str=""):
    """Allow to create a command when the message come from a given channel. This decorator can be
    used with another one to have more complex commands.

    Parameters
    ----------
    channel_name : str
        The channel's name on which the command will be called.
    desc : str, optionnal
        This is the description of the command. It allows you to make an auto-generated
        documentation with this field.

    Returns
    -------
    decorator : function
        This function take in argument the function you want to transform into a command and returns
        a Command's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import api``
    If you want to react on every message on a specific channel, you can make a command like::
        @api.channel(channel_name="bot-test", desc="The bot will react on every message post on #bot-test")
        def spam(bot, message):
            bot.send("#bot-test", "This is MY channel.")

    You can also cumulate this decorator with ``@api.command``, ``@api.on`` and ``@api.user``::
        from random import choice

        @api.channel(channel_name="bot-test") # note that the description given here isn't taken into account
        @api.command(name="troll", desc="Some troll command")
        def troll_bot(bot, message):
            emotions = ("happy", "sad", "angry")
            bot.send("#bot-test", f"*{choice(emotions)} troll's noises*")

    """
    def decorator(func_or_cmnd):
        if isinstance(func_or_cmnd, Command):
            func_or_cmnd.events.append(lambda m: m.to == channel_name)
            return func_or_cmnd
        else:
            return Command(
                name=func_or_cmnd.__name__,
                func=func_or_cmnd,
                events=[lambda m: m.to == channel_name],
                desc=desc,
                cmnd_type=0
            )
    return decorator


def user(user_name: str, desc: str=""):
    """Allow to create a command when the message come from a given user. This decorator can be
    used with another one to have more complex commands.

    Parameters
    ----------
    user_name : str
        The user's name on which the command will be called.
    desc : str, optionnal
        This is the description of the command. It allows you to make an auto-generated
        documentation with this field.

    Returns
    -------
    decorator : function
        This function take in argument the function you want to transform into a command and returns
        a Command's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import api``.
    If you want to react on every message from a specific user, you can make a command like::
        @api.user(user_name="my_pseudo", desc="The bot will react on every message post by my_pseudo")
        def spam(bot, message):
            bot.send(message.to, "I subscribe to what my_pseudo said.")


    You can also cumulate this decorator with ``@api.command``, ``@api.on`` and ``@api.channel``::
        @api.user(user_name="my_pseudo")
        @api.command(name="test", desc="Some test command.")
        def foo(bot, message):
            bot.send(message.to, "Test received, my_pseudo.")
    """
    def decorator(func_or_cmnd):
        if isinstance(func_or_cmnd, Command):
            func_or_cmnd.events.append(lambda m: m.author == user_name)
            return func_or_cmnd
        else:
            return Command(
                name=func_or_cmnd.__name__,
                func=func_or_cmnd,
                events=[lambda m: m.author == user_name],
                desc=desc,
                cmnd_type=0
            )
    return decorator


def every(time: float, desc=""):
    """This is not a command but it allows you to call some routines at regular intervals.

    Parameters
    ----------
    time : float
        The time in seconds between two calls.
     desc : str, optionnal
        This is the description of the command. It allows you to make an auto-generated
        documentation with this field.

    Returns
    -------
    decorator : function
        This function take in argument the function you want to transform into a command and returns
        a Command's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import api``.
    You can make a routine::
        @api.every(time=5, desc="This routine says 'hello' on #general every 5 seconds")
        def spam(bot, message):
            bot.send("#general", "Hello there!") # please don't do that (.><)'
    """
    def decorator(func):
        return Command(
                name=func.__name__,
                func=func,
                events=time,
                desc=desc,
                cmnd_type=2
            )

    return decorator


class Command:
    def __init__(self, name, func, events, desc, cmnd_type):
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
        return self.func(self.bot, msg, *args)


class WrongArg:
    """If the transtyping has failed and the argument has no default value."""


class Bot:
    """Run the connexion between IRC's server and V5 one.

    Attributes
    ----------
    prefix : str, public

    irc : IRC, public
        IRC wrapper which handle communication with IRC server.
    history : History, public
        The messages history. 
    channels : list, public
        The channels the bot will listen.
    auth : tuple, public
        This contains the username and the password for a SASL auth.
    callbacks : dict, public
        The callbacks of the bot. This dictionnary is like {name: command} where name is the name of
        the command and command a Command's instance.
    commands_help : dict, public
        Same that ``callbacks`` but only with the documented commands. 
    threads : list, public
        A list of threads for the commands with ``@api.every``.

    Methods
    -------
    start : NoneType, public
        Runs the bot and connects it to IRC server.
    send : NoneType, public
        Send a message on the IRC server.
    add_command : NoneType, public
        Add a single command to the bot.
    add_commands : NoneType, public
        Allow to add a list of command to the bot.
    add_commands_module : NoneType, public
        Allow to add a module of command to the bot.
    remove_command : NoneType, public
        Remove a command.
    """
    def __init__(
            self,
            irc_params: tuple,
            auth: tuple=(),
            channels: list=["#general"],
            prefix: str="",
            limit: int=100,         
            *commands_modules,
        ):
        """Initialize the Bot instance.

        Parameters
        ----------
        irc_params : tuple
            A tuple like: (host, port) to connect to the IRC server.
        auth : tuple, optionnal
            Contains the IRC server informations (host, port)
        channels : list, optionnal
            Contains the names of the channels on which the bot will connect.
        prefix : str
            The bot's prefix for named commands.
        limit : int
            The message history of the bot. By default, the bot will remind 100 messages.
        *commands_module : optionnal
            Modules of commands that you can give to the bot at it's creation.

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
        global PREFIX
        PREFIX = prefix
        self.prefix = PREFIX

        self.irc = IRC(*irc_params)
        self.history = limit
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
        self.irc.connexion(nick, self.auth)

        # Join channels
        for channel in self.channels:
            self.irc.join(channel)

        # mainloop
        while True:
            message = self.irc.receive()
            self.history.add(message)
            logging.info("received %s", message)
            if message is not None:
                for callback in self.callbacks.values():
                    if not False in [event(message) for event in callback.events]:
                        logging.info("matched %s", callback.name)

                        # others command types
                        if callback.cmnd_type == 0:
                            callback(message)

                        # @api.command
                        elif callback.cmnd_type == 1:
                            args = check_args(callback.func, *parse(message.text)[1:])
                            if isinstance(args, list):
                                callback(message, *args)
                            else:
                                self.send(
                                        message.to,
                                        "Erreur : les arguments donnés ne correspondent pas."
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
        command : Command
            The command to add to the bot.
        add_to_help : bool, optionnal
            If the command should be added to the documented functions.
        """
        command.bot = self

        if command.cmnd_type == 2:
            def timed_func(bot):
                while True:
                    command.func(bot)
                    time.sleep(command.events)
                    logging.info("auto call : %s", command.name)

            self.threads.append(Thread(target=lambda bot: timed_func(bot), args=(self,)))
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
                if isinstance(cmnd, Command):
                    self.add_command(cmnd, add_to_help=add_to_help)

    def remove_command(self, command_name: str):
        """Remove a command.

        Parameters
        ----------
        command_name : str
            The name of the command to delete.
        """
        if command_name in self.callbacks.keys():
            self.callbacks.pop(command_name)
            self.commands_help.pop(command_name)


@command("help")
def auto_help(bot, msg, fct_name: str=""):
    """Auto generated help command."""
    if fct_name and fct_name in bot.commands_help.keys():
        cmnd = bot.commands_help[fct_name]
        answer = f"Help on the command: {bot.prefix}{fct_name}\n"
        for line in bot.commands_help[fct_name].desc.splitlines():
            answer += f" │ {line}\n"
    else:
        answer = f"List of available commands ({PREFIX}help <cmnd> for more informations)\n"
        for cmnd_name, cmnd in bot.commands_help.items():
            if cmnd.type == 1:
                answer += f" - {cmnd_name}\n"

    bot.send(msg.to, answer)


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
    except:
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
            check_args = (arg_type, defaults[index - required_args])
        else:
            check_args = (arg_type, wrong_arg)

        # transtypes each given arguments to its target type
        if len(input_args) > index:
            converted_args.append(convert(input_args[index], *check_args))
        else:
            converted_args.append(check_args[1])

    # if an argument has no default value and transtyping has failed
    if wrong_arg in converted_args:
        return None

    return converted_args
