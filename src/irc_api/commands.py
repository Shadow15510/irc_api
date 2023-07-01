"""Defines the decorators for bot commands."""
from irc_api.bot import BotCommand

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
        a BotCommand's instance.

    Examples
    --------
    For example, assuming the module was imported as follow: ``from irc_api import commands``
    You can make a command::

        @commands.command(name="ping", desc="Answer 'pong' when the user enters 'ping'.")
        def foo(bot, message):
            bot.send(message.to, "pong")
    """
    if not alias or not name in alias:
        alias += (name,)
    def decorator(func):
        cmnd = BotCommand(
                name=name,
                func=func,
                events=[],
                desc=desc,
                cmnd_type=1
            )
        cmnd.alias = alias
        return cmnd
    return decorator


def on(event, desc: str=""):
    """Make a command on a custom event. It can be useful if you want to have a complex calling
    processus. Such as a regex recognition or a specific pattern. This decorator allows you to call
    a command when a specific event is verified.

    You can use several ``@commands.on`` on one function.
    
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
        a BotCommand's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import commands``
    You can make a new command::

        @commands.on(lambda m: isinstance(re.match(r"(.*)(merci|merci beaucoup|thx|thanks|thank you)(.*)", m.text, re.IGNORECASE), re.Match))
        def thanks(bot, message):
            bot.send(message.to, f"You're welcome {message.author}! ;)")
    """
    def decorator(func_or_cmnd):
        if isinstance(func_or_cmnd, BotCommand):
            func_or_cmnd.events.append(event)
            return func_or_cmnd

        return BotCommand(
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
        a BotCommand's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import commands``
    If you want to react on every message on a specific channel, you can make a command like::

        @commands.channel(channel_name="bot-test", desc="The bot will react on every message post on #bot-test")
        def spam(bot, message):
            bot.send("#bot-test", "This is MY channel.")


    You can also cumulate this decorator with ``@commands.command``, ``@commands.on`` and
    ``@commands.user``::

        @commands.channel(channel_name="bot-test") # note that the description given here isn't taken into account
        @commands.command(name="troll", desc="Some troll command")
        def troll_bot(bot, message):
            emotions = ("happy", "sad", "angry")
            bot.send("#bot-test", f"*{choice(emotions)} troll's noises*")
    """
    def decorator(func_or_cmnd):
        if isinstance(func_or_cmnd, BotCommand):
            func_or_cmnd.events.append(lambda m: m.to == channel_name)
            return func_or_cmnd

        return BotCommand(
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
        a BotCommand's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import commands``.
    If you want to react on every message from a specific user, you can make a command like::

        @commands.user(user_name="my_pseudo", desc="The bot will react on every message post by my_pseudo")
        def spam(bot, message):
            bot.send(message.to, "I subscribe to what my_pseudo said.")

    You can also cumulate this decorator with ``@commands.command``, ``@commands.on`` and
    ``@commands.channel``::

        @commands.user(user_name="my_pseudo")
        @commands.command(name="test", desc="Some test command.")
        def foo(bot, message):
            bot.send(message.to, "Test received, my_pseudo.")
    """
    def decorator(func_or_cmnd):
        if isinstance(func_or_cmnd, BotCommand):
            func_or_cmnd.events.append(lambda m: m.author == user_name)
            return func_or_cmnd

        return BotCommand(
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
        a BotCommand's instance.

    Examples
    --------
    Assuming the module was imported as follow: ``from irc_api import commands``.
    You can make a routine::

        @commands.every(time=5, desc="This routine says 'hello' on #general every 5 seconds")
        def spam(bot, message):
            bot.send("#general", "Hello there!") # please don't do that (.><)'
    """
    def decorator(func):
        return BotCommand(
                name=func.__name__,
                func=func,
                events=time,
                desc=desc,
                cmnd_type=2
            )

    return decorator


@command("help")
def auto_help(bot, msg, fct_name: str=""):
    """Auto generated help command."""
    if fct_name and fct_name in bot.commands_help.keys():
        cmnd = bot.commands_help[fct_name]
        answer = f"Help on the command: {bot.prefix}{fct_name}\n"
        for line in bot.commands_help[fct_name].desc.splitlines():
            answer += f" │ {line}\n"
    else:
        answer = f"List of available commands ({bot.prefix}help <cmnd> for more informations)\n"
        for cmnd_name, cmnd in bot.commands_help.items():
            if cmnd.cmnd_type == 1:
                answer += f" - {cmnd_name}\n"

    bot.send(msg.to, answer)
