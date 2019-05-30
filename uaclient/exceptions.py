class UserFacingError(Exception):
    """
    An exception to be raised when an execution-ending error is encountered.

    :param msg:
        Takes a single parameter, which is the user-facing error message that
        should be emitted before exiting non-zero.
    """

    def __init__(self, msg: str) -> None:
        self.msg = msg
