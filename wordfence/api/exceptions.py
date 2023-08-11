from typing import Optional


class ApiException(Exception):

    def __init__(
                self,
                internal_message: str,
                public_message: Optional[str] = None
            ):
        super().__init__(f'{internal_message}: {public_message}')
        self.public_message = public_message
