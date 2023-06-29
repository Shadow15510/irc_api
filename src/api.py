import logging
import re
from irc import IRC, History
from threading import Thread
import time


PREFIX = ""


def command(name, alias=(), desc=""):
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


def on(event, desc=""):
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


def channel(channel_name, desc=""):
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


def user(user_name, desc=""):
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


def every(time, desc=""):
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
    irc : IRC, public
        IRC wrapper which handle communication with IRC server.
    v5 : V5, public
        V5 wrapper which handle communication with V5 server.
    channels : list, public
        The channels the bot will listen.

    Methods
    -------
    start : NoneType, public
        Runs the bot and connects it to IRC and V5 servers.
    """
    def __init__(
            self,
            auth: tuple,
            irc_params: tuple,
            channels: list=["#general"],
            *commands_modules,
            **kwargs
        ):
        """Initialize the Bot instance.

        Parameters
        ----------
        irc_params : tuple
            Contains the IRC server informations (host, port)
        channels : list
            Contains the names of the channels on which the bot will connect.
        prefix : str, optionnal
            The prefix on which the bot will react.
        """
        global PREFIX
        if kwargs.get('prefix'):
            PREFIX = kwargs.get('prefix')
        self.prefix = PREFIX

        self.irc = IRC(*irc_params)
        self.history = History(kwargs.get('limit'))
        self.channels = channels
        self.auth = auth
        self.callbacks = {}
        self.commands_help = {}
        self.threads = []

        if commands_modules:
            self.add_commands_modules(*commands_modules)

    def start(self, nick: str):
        """Starts the bot and connect it to the given IRC and V5 servers."""
        # Start IRC
        self.irc.connexion(self.auth[0], self.auth[1], nick)

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
                        
                        # @api.on
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

    def add_command(self, command, add_to_help=False):
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

        if add_to_help and command.cmnd_type == 1:
            self.commands_help[command.name] = command

    def add_commands(self, *commands, **kwargs):
        """Add a list of commands to the bot.

        Parameters
        ----------
        commands : list
            A list of command's instances.
        """
        add_to_help = "auto_help" in [cmnd.name for cmnd in commands]
        for command in commands:
            self.add_command(command, add_to_help=add_to_help)

    def add_commands_modules(self, *commands_modules):
        for commands_module in commands_modules:
            add_to_help = "auto_help" in dir(commands_module)
            for cmnd_name in dir(commands_module):
                    cmnd = getattr(commands_module, cmnd_name)
                    if isinstance(cmnd, Command):
                        self.add_command(cmnd, add_to_help=add_to_help)

    def remove_command(self, command_name: str):
        if command_name in self.callbacks.keys():
            self.callbacks.pop(command_name)


@command("aide", alias=("aide", "help", "doc", "assistance"))
def auto_help(bot, msg, fct_name: str=""):
    """Aide des commandes disponibles."""
    if fct_name and fct_name in bot.commands_help.keys():
        cmnd = bot.commands_help[fct_name]
        answer = f"Aide sur la commande : {bot.prefix}{fct_name}\n"
        for line in bot.commands_help[fct_name].desc.splitlines():
            answer += f" │ {line}\n"
    else:
        answer = f"Liste des commandes ({PREFIX}aide <cmnd> pour plus d'info)\n"
        for cmnd_name in bot.commands_help.keys():
            answer += f" - {cmnd_name}\n"

    bot.send(msg.to, answer)


def parse(message):
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


def convert(data, new_type, default=None):
    try:
        return new_type(data)
    except:
        return default


def check_args(func, *input_args):
    # gets the defaults values given in arguments
    defaults = getattr(func, "__defaults__")
    if not defaults:
        defaults = []

    # gets the arguments and their types
    annotations = getattr(func, "__annotations__")
    if not annotations:
        return []

    # nb of required arguments
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
