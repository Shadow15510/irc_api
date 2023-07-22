"""Allow to save the messages history."""

class History:
    """A custom queue to have access to the latest messages.

    Attributes
    ----------
    content : list, private
        The content of the History.
    limit : int, private
        The maximum number of messages that the History stored.
    """
    def __init__(self, limit: int):
        """Initialize the History.
        
        Parameters
        ----------
        limit : int
            The maximum number of messages the History's instance can handle.
        """
        self.__content = []
        if limit:
            self.__limit = limit
        else:
            self.__limit = 100

    def __len__(self):
        """Returns the lenght of the History's instance."""
        return len(self.__content)

    def add(self, elmnt):
        """Add a new element to the History's instance. If the History is full, the oldest message
        is deleted.

        Parameters
        ----------
        :elmnt : int: Whatever the type it will work.
        """
        if len(self.__content) == self.__limit:
            self.__content.pop(0)
        self.__content.append(elmnt)

    def get(self):
        """Returns the content of the History's instance."""
        return self.__content
