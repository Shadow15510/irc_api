Tutorials
=========

My first IRC bot
----------------
First of all, your bot will be composed of one main file which will contain your bot itself and one or several commands files.
If the targeted IRC server has a SASL auth, you'll have to give the auth parameters by the way you want.

Let's start with a minimal bot::

    from irc_api.bot import Bot   # imports the Bot
    from irc_api import commands  # imports command's decorators
    
    my_bot = Bot(
            ('irc.exemple.com', 6697),  # host and port for IRC server
        )
    
    @commands.command(name='hello')  # we create a new command
    def cmnd_hello(bot, msg):        # the function bounded to the command
        bot.send(msg.to, f'Hello {msg.author}')
    
    my_bot.add_command(cmnd_hello) # we add the command to the bot
    
    my_bot.start('SuperBot')  # we start the bot; this method take the nickname in argument

So here we have just created a minimal bot that will connect on the channel ``#general`` of the ``irc.exemple.com`` IRC server with the nick 'SuperBot'. When someone on this channel sends ``hello``, the bot will answer.

The PINGing of IRC is fully take in charge by IRC API you don't have to make a command to handle it.

.. note::
	You can create a new class that inherits from ``Bot``::
	
		from irc_api.bot import Bot
		
		class MyBot(Bot):
			my_custom_attritute = 0
		
		my_bot = MyBot(…)
		
		@commands.command('get')
		def get_custom_attr(bot, msg):
			bot.send(msg.to, f'{bot.my_custom_attribute}')
		
		my_bot.add_command(get_custom_attr)
		my_bot.start(…)
	
	And the same goes for custom methods.

SASL auth
---------
Some IRC servers required an auth. This package can handle SASL auth, you just have to give to the bot a positionnal argument::

    from irc_api.bot import Bot # imports the Bot
    from irc_api import commands # imports command's decorators
    
    from secrets import USER, PASSWORD  # you can import the secrets by the way you want
    
    my_bot = Bot(
            ('irc.exemple.com', 6697),  # host and port for IRC server
            channels=['#general'],      # the channels to bot will join
            auth=(USER, PASSWORD),      # the informations for SASL auth
            prefix='!'                  # the bot's prefix.
        )

Logging
-------
You can log what the bot receive and what callbacks are triggered. You just have to import the ``logging`` package and to specify a log format::

	import logging
	
	LOG_FORMAT = "[%(levelname)s] %(message)s"
	logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

You can change the LOG_FORMAT to suit your need.

Make a command
--------------
You have at your disposal a large panel of decorators to make custom commands. Let's see them all.

All your commands must take at least two parameters: 

– the bot itself (an irc_api.bot.Bot instance)

– the message that triggered the bot (an irc_api.message.Message instance)

In this part, you should import the ``commands`` module as follow: ``from irc_api import commands``.

``commands.command(name, alias)``
    This decorator allows you to make a classic command. The bot will react when the name (or one of the aliases) is at the beginning of a message.
    
    For exemple::

        @commands.command(name='hello', alias=('hi', 'hey'))
        def greetings(bot, msg):
            bot.send(msg.to, "Hello")

    This command will answer if the incoming message starts with 'hello', 'hi', or 'hey' (in addition of the custom prefix given to the bot).
    
    The commands created with this decorator can also take additionnal arguments, you should precise the type of each, so the bot can convert the arguments in the right type for you. You can also use default value if your parameter is optionnal. For instance::

        @commands.command(name='buy', alias=('shop', 'store'))
        def buy(bot, msg, article_name: str, quantity: int=1):
            if not article_name in articles_list:
                bot.send(msg.to, 'Unknown article.')
            else:
                player_buy(article_name, quantity)
                bot.send(msg.to, f'{msg.author} bought {quantity} {article_name}.')

    Let's say that the bot's prefix is '!', if the incoming message is ``!buy bread`` the player will buy one unity of bread idem if the incoming is ``!shop bread abc`` because 'abc' is not a valid ``int``. You can use quotes and double-quotes to give multi-words arguments: ``!store 'little piece of bread' 5`` to buy 5 unity of 'little piece of bread'. And so on and so far.

``commands.on(event)``
    This decorator allows you to go a little bit further by giving you the possibility to trigger a command on an event. An event is a function that must take only one argument: the message (an irc_api.message.Message instance), and must returns a bool instance.
    
    You can do litteraly what you want. Let's see a little exemple::

        @commands.on(lambda m: 'hello' in m.text.lower())
        def greetings(bot, msg):  # this type of command can't take additionnal parameters
            bot.send(msg.to, f'Hello {msg.author}'.)

    This command say 'Hello' if there is the word 'hello' in the content of a message.
    
    You can use several ``@commands.on`` on one command::

        @commands.on(lambda m: 'hello' in m.text.lower())
        @commands.on(lambda m: 'superbot' in m.text.lower())
        def greetings(bot, msg):
            bot.send(msg.to, f'Hello {msg.author}'.)

    So the command is triggered only if the two given events are on True

``commands.channel``
    This will trigger a command at each message on a specific channel. Used on it's own, it doesn't make much sense, but it can be used to complement another decorator.
    
    Let's see an exemple with it alone::

        @commands.channel('#bot-test')
        def test(bot, msg):
            bot.send(msg.to, f'Receive: {msg.}')

    As I said, you can combine it::

        @commands.channel('#bot-test')
        @commands.command('stat', alias=('info',))
        def player_stat(bot, msg):
            bot.send(msg.to, get_stat(msg.author))  # here msg.to is equal to '#bot-test'

    In this exemple, the command will be only available if the message has been sent in the channel ``#bot-test``.

``commands.user``
    This decorator allow to react on a specific user's name. Like ``commands.channel`` it can be user in addition to another decorator.
    
    For exemple, if you want to make some admin commands, it can be useful to check who is admin before running the admin command::

        @commands.user('AdminPseudo')
        @commands.command('kick')
        def user_kick(bot, msg, user_name: str):
            kick_hammer(user_name)
            bot.send(msg.to, f'{user_name} has been kicked by {msg.author}')  # here msg.author is equal to 'AdminPseudo'.

``commands.every``
    This decorator is different from the others. Indeed, the others allow to trigger a command on a specific event, this decorator allow to trigger a command at regular intervals. The commands define with this decorator take only one argument (instead of two): the bot.
    
    For instance, you want your bot to send notification when some contents is posted on a website (e.g. with RSS feed) and you want to check the website each hour::

        @commands.every(3600)  # time between calls in seconds, 3600s = 1h
        def check_rss(bot):
            if is_new_content():
                bot.send('#newspaper', "There is some new contents! Check out newspaper.org for more infos.")

Import commands into a bot
--------------------------
There is several ways to import commands into the bot.

``Bot.add_command``
    This method allows you to add a single command to the bot. It takes two arguments:
    
    – the command itself
    
    – a bool to consider the command as documented (``True``) or not (``False``). If the command is marked as documented, it will be stored into ``Bot.commands_help``
    
``Bot.add_commands``
    This allows you to a list of commands. For exemple::

        my_bot = Bot(…)
        my_bot.add_commands(cmnd1, cmnd2, cmnd3, …)

    To marked all the given as documented, you should add the ``auto_help`` command to the list::

        from irc_api.commands import auto_help
        
        my_bot = Bot(…)
        my_bot.add_commands(auto_help, cmnd1, cmnd2, cmnd3, …)

Note that you can also dynamically remove commands from the bot with the ``Bot.remove_command`` methode. You just have to give the command name.
        

Module of commands
------------------
When you have a complex bot, it can be more readable to isolate the commands in separates modules. In each module of commands you should import the ``commands`` modules with: ``from irc_api import commands``.

Once you've created your modules of commands, you can import them into your bot by several ways.
The first one is also the easiest::

    import cmnd1  # modules of commands
    import cmnd2
    import cmnd3
    
    from irc_api.bot import Bot
    from secrets import USER, PASSWORD
    
    my_bot = Bot(
            ('irc.exemple.com', 6697),  # host and port for IRC server
            cmnd1, cmnd2, cmnd3,        # the modules of commands, you can pass as many as you like
            channels=['#general'],      # the channels to bot will join
            auth=(USER, PASSWORD),      # the informations for SASL auth
            prefix='!'                  # the bot's prefix.
        )
    
    my_bot.stat('SuperBot')

You can also decide to declare the bot and to add the command after::

    import cmnd1  # modules of commands
    import cmnd2
    import cmnd3
    
    from irc_api.bot import Bot
    from secrets import USER, PASSWORD
    
    my_bot = Bot(
            ('irc.exemple.com', 6697),  # host and port for IRC server
            channels=['#general'],      # the channels to bot will join
            auth=(USER, PASSWORD),      # the informations for SASL auth
            prefix='!'                  # the bot's prefix.
        )
    
    my_bot.add_commands_modules(cmnd1, cmnd2, cmnd3)  # you can pass as many modules as you like
    my_bot.stat('SuperBot')

Auto-generated assistance
-------------------------
An auto-generated assistance is available. It allows you to have access to the command ``help``. To activate the auto-generated documentation for the whole module, you just have to import ``auto_help`` from ``commands``, you can proceed like: ``from irc_api.commands import auto_help``.

To have a constructive assistance, you can add a description to your commands by passing a ``desc`` positionnal argument to the decorator::

    @commands.command(name='hello', desc='Answer hello.')
    def greetings(bot, msg):
        …

Note that only the first decorator can have the description, the others will be ignored::

    @commands.channel('#bot-test', desc='An ignored description.')
    @commands.on(lambda m: 'hello' in m.text().lower(), desc='This description will be stored.')
    def greetings(bot, msg):
        …

You can also document your function and don't fill the ``desc`` argument::

    @commands.channel('#bot-test')
    @commands.on(lambda m: 'hello' in m.text().lower())
    def greetings(bot, msg):
        """This description will be stored. Say hello."""
        …

If the both are given (docstring and ``desc``), only ``desc`` is stored.

In the IRC chat, you can have access to the auto-generated assistance by enter: ``help`` (don't forget the prefix if you have set one) to have the list of all available commands or ``help cmnd`` where ``cmnd`` is the command's name. By default, only named commands are taken in charge. Feel free to make you're own assistance function. You can use ``Bot.callbacks`` to get all the registered commands and ``Bot.commands_help`` to get only the commands that are marked as documented.
