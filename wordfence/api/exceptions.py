from typing import Optional


class ApiException(Exception):

    def __init__(  # noqa: B042
                self,
                internal_message: str,
                public_message: Optional[str] = None
            ):
        if public_message is not None:
            message = f'{internal_message}: {public_message}'
        else:
            message = internal_message
        super().__init__(message)
        self.public_message = public_message
