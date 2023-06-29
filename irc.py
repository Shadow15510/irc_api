"""
irc (IRC API)
=============

Description
-----------
Manage the IRC layer.
"""

import logging
import re
import socket
import ssl

from functools import wraps
from queue import Queue
from threading import Thread


class IRC:
    """Manage connexion to an IRC server, authentication and callbacks.

    Attributes
    ----------
    connected : bool, public
        If the bot is connected to an IRC server or not.
    callbacks : list, public
        List of the registred callbacks.

    socket : ssl.SSLSocket, private
        The IRC's socket.
    inbox : Queue, private
        Queue of the incomming messages.
    handler : Thread, private

    Methods
    -------
    start : NoneType, public
        Starts the IRC layer and manage authentication.
    run : NoneType, public
        Mainloop, allows to handle public messages.
    send : NoneType, public
        Sends a message to a given channel.
    receive : Message, public
        Same as ``run`` for private messages.
    join : NoneType, public
        Allows to join a given channel.
    on : function, public
        Add a callback on a given message.

    handle : NoneType, private
        Handles the ping and store incoming messages into the inbox attribute.
    send : NoneType, private
        Send message to a target.
    recv : str, private
        Get the oldest incoming message and returns it.
    waitfor : str, private
        Wait for a raw message that matches the given condition.
    """
    def __init__(self, host: str, port: int):
        """Initialize an IRC wrapper.

        Parameters
        ----------
        host : str
            The adress of the IRC server.
        port : int
            The port of the IRC server.
        """

        # Public attributes
        self.connected = False  # Simple lock

        # Private attributes
        self.__socket = ssl.create_default_context().wrap_socket(
                socket.create_connection((host, port)),
                server_hostname=host
            )
        self.__inbox = Queue()
        self.__handler = Thread(target=self.__handle)

    # Public methods
    def connexion(self, username: str, password: str, nick: str):
        """Start the IRC layer. Manage authentication as well.

        Parameters
        ----------
        nick : str
            The username for login and nickname once connected.
        password : str
            The password for authentification.
        """
        self.__handler.start()

        self.send(f"USER {nick} * * :{nick}")
        self.send(f"NICK {nick}")
        self.waitfor(lambda m: "NOTICE" in m and "/AUTH" in m)
        self.send(f"AUTH {username}:{password}")
        self.waitfor(lambda m: "You are now logged in" in m)

        self.connected = True

    def receive(self):
        """Receive a private message.
        
        Returns
        -------
        msg : Message
            The incoming processed private message.
        """
        while True:
            message = self.__inbox.get()
            if " PRIVMSG " in message:
                msg = Message(message)
                if msg:
                    return msg

    def join(self, channel: str):
        """Join a channel.
        
        Parameters
        ----------
        channel : str
            The name of the channel to join.
        """
        self.send(f"JOIN {channel}")
        logging.info("joined %s", channel)

    def send(self, raw: str):
        """Wrap and encode raw message to send.

        Parameters
        ----------
        raw : str
            The raw message to send.
        """
        self.__socket.send(f"{raw}\r\n".encode())

    def waitfor(self, condition):
        """Wait for a raw message that matches the condition.

        Parameters
        ----------
        condition : function
            ``condition`` is a function that must taking a raw message in parameter and returns a
            boolean.

        Returns
        -------
        msg : str
            The last message received that doesn't match the condition.
        """
        msg = self.__inbox.get()
        while not condition(msg):
            msg = self.__inbox.get()
        return msg

    # Private methods
    def __handle(self):
        """Handle raw messages from irc and manage ping."""
        while True:
            # Get incoming messages
            data = self.__socket.recv(4096).decode()

            # Split multiple lines
            for msg in data.split('\r\n'):
                # Manage ping
                if msg.startswith("PING"):
                    self.send(msg.replace("PING", "PONG"))
                
                # Or add a new message to inbox
                elif len(msg):
                    self.__inbox.put(msg)
                    logging.debug("received %s", msg)


class History:
    def __init__(self, limit: int):
        self.__content = []
        if limit:
            self.__limit = limit
        else:
            self.__limit = 100

    def __len__(self):
        return len(self.__content)

    def add(self, elmnt):
        if len(self.__content) == self.__limit:
            self.__content.pop(0)
        self.__content.append(elmnt)

    def get(self):
        return self.__content


class Message:
    """Parse the raw message in three fields : author, the channel, and text.
    
    Attributes
    ----------
    pattern : re.Pattern, public
        The message parsing pattern.
    author : str, public
        The message's author.
    to : str, public
        The message's origin (channel or DM).
    text : str, public
        The message's content.
    """
    pattern = re.compile(
            r"^:(?P<author>[\w.~|\-\[\]]+)(?:!(?P<host>\S+))? PRIVMSG (?P<to>\S+) :(?P<text>.+)"
        )

    def __init__(self, raw: str):
        match = re.search(Message.pattern, raw)
        if match:
            self.author = match.group("author")
            self.to = match.group("to")
            self.text = match.group("text")
            logging.debug("sucessfully parsed %s into %s", raw, self.__str__())
        else:
            self.author = ""
            self.to = ""
            self.text = ""
            logging.warning("failed to parse %s into valid message", raw)

    def __str__(self):
        return f"{self.author} to {self.to}: {self.text}"
