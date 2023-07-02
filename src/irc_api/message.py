"""Parse the raw incoming message into a Message instance."""

import re


class Message:
    """Parse the raw message in three fields: the author, the channel and the text content.
    
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
        """Initialize and parse a raw message into a Message's instance.

        Parameters
        ----------
        raw : str
            The raw received message.
        """
        match = re.search(Message.pattern, raw)
        if match:
            self.author = match.group("author")
            self.to = match.group("to")
            self.text = match.group("text")
        else:
            self.author = ""
            self.to = ""
            self.text = ""

    def __str__(self):
        """Convert the Message's instance into a human readable string."""
        return f"{self.author} to {self.to}: {self.text}"
