class RateLimitException(Exception):
    """
    This is a custom Exception that occurs when the API RateLimit is reached.
    Occurs when a set limit is reached

    :param message: Custom Exception message
    """

    def __init__(self, message: str = None):
        super(RateLimitException, self).__init__(message)
