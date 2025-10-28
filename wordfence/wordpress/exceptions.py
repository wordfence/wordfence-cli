class WordpressException(Exception):
    pass


class ExtensionException(WordpressException):
    pass


class WordpressDatabaseException(Exception):

    def __init__(self, database, message):  # noqa: B042
        self.database = database
