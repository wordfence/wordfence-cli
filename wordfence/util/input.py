from typing import Optional, Callable, Any


class InvalidInputException(Exception):

    def __init__(self, message: str):
        self.message = message


def prompt(
            message: str,
            default: Optional[str] = None,
            transformer: Optional[Callable[[str], Any]] = None,
            allow_empty: bool = False
        ) -> Any:
    default_message = ''
    if default is not None:
        default_message = f' (default: {default})'
    while True:
        response = input(f'{message}{default_message}: ')
        if len(response) == 0 and not allow_empty:
            response = default
        if transformer is not None:
            try:
                return transformer(response)
            except InvalidInputException as e:
                print(e.message)
        else:
            return response


def transform_yn_to_bool(response: str) -> Any:
    lower_response = response.lower()
    if lower_response == 'y':
        return True
    elif lower_response == 'n':
        return False
    else:
        raise InvalidInputException(
                f'Invalid response: "{response}", please enter "y" or "n"'
            )


def transform_str_to_int(response: str) -> int:
    try:
        if response.isascii() and response.isdigit():
            return int(response)
    except ValueError:
        pass
    raise InvalidInputException(
            'Please enter a valid integer'
        )


def prompt_yes_no(message: str, default: Optional[bool] = None) -> bool:
    default_string = None
    if default is not None:
        default_string = 'y' if default else 'n'
    return prompt(
            message=f'{message} [y/n]',
            default=default_string,
            transformer=transform_yn_to_bool
        )


def prompt_int(message: str, default: Optional[int] = None) -> int:
    default_string = None
    if default is not None:
        default_string = str(default)
    return prompt(
            message,
            default=default_string,
            transformer=transform_str_to_int)
