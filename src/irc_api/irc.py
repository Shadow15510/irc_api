"""Manage the IRC layer."""

import logging
import socket
import ssl

from queue import Queue
from threading import Thread
from irc_api.message import Message


class IRC:
    """Manage connection to an IRC server, authentication and callbacks.

    Attributes
    ----------
    connected : bool, public
        If the bot is connected to an IRC server or not.

    socket : ssl.SSLSocket, private
        The IRC's socket.
    inbox : Queue, private
        Queue of the incomming messages.
    handler : Thread, private

    Methods
    -------
    .. automethod:: __init__
    .. automethod:: connection
    .. automethod:: join
    .. automethod:: receive
    .. automethod:: send
    .. automethod:: waitfor

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
    def connection(self, nick: str, auth: tuple=()):
        """Start the IRC layer. Manage authentication as well.

        Parameters
        ----------
        nick : str
            The nickname used.
        auth : tuple, optionnal
            The tuple (username, password) for a SASL authentication. Leave empty if no SASL auth is
            required.
        """
        self.__handler.start()

        self.send(f"USER {nick} * * :{nick}")
        self.send(f"NICK {nick}")
        if auth:
            self.waitfor(lambda m: "NOTICE" in m and "/AUTH" in m)
            self.send(f"AUTH {auth[0]}:{auth[1]}")

        self.connected = True

    def send(self, raw: str):
        """Wrap and encode raw message to send.

        Parameters
        ----------
        raw : str
            The raw message to send.
        """
        self.__socket.send(f"{raw}\r\n".encode())

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
                    logging.info("receive: %s", msg)
                    return msg

    def join(self, channel: str):
        """Join a channel.
        
        Parameters
        ----------
        channel : str
            The name of the channel to join.
        """
        logging.info("join %s", channel)
        self.send(f"JOIN {channel}")

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
