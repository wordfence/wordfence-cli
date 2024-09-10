class WordpressException(Exception):
    pass


class ExtensionException(WordpressException):
    pass


class WordpressDatabaseException(Exception):

    def __init__(self, database, message):
        self.database = database
