import sys

from typing import Optional, Callable, Any


class InputException(Exception):
    pass


class InvalidInputException(InputException):

    def __init__(self, message: str):  # noqa: B042
        self.message = message


class NoInputException(InputException):
    pass


class NoTerminalException(InputException):
    pass


def has_terminal_output() -> bool:
    return sys.stdout is not None \
            and sys.stdout.isatty()


def has_terminal_input() -> bool:
    return sys.stdin is not None \
            and sys.stdin.isatty()


def has_terminal() -> bool:
    return has_terminal_input() and has_terminal_output()


def prompt(
            message: str,
            default: Optional[str] = None,
            transformer: Optional[Callable[[str], Any]] = None,
            allow_empty: bool = False
        ) -> Any:
    if not has_terminal():
        raise NoTerminalException('Interactive prompts require a terminal')
    default_message = ''
    if default is not None:
        default_message = f' (default: {default})'
    while True:
        try:
            response = input(f'{message}{default_message}: ')
        except EOFError as error:
            raise NoInputException('Unable to read input') from error
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


def initialize_str_to_int_transformer(
            min: Optional[int] = None,
            max: Optional[int] = None
        ):
    def transformer(response: str) -> int:
        value = transform_str_to_int(response)
        if min is not None and value < min:
            raise InvalidInputException(
                    f'Please enter a value that is at least {min}'
                )
        if max is not None and value > max:
            raise InvalidInputException(
                    f'Please enter a value that is no greater than {max}'
                )
        return value
    return transformer


def prompt_yes_no(message: str, default: Optional[bool] = None) -> bool:
    default_string = None
    if default is not None:
        default_string = 'y' if default else 'n'
    return prompt(
            message=f'{message} [y/n]',
            default=default_string,
            transformer=transform_yn_to_bool
        )


def prompt_int(
            message: str,
            default: Optional[int] = None,
            min: Optional[int] = None,
            max: Optional[int] = None
        ) -> int:
    default_string = None
    if default is not None:
        default_string = str(default)
    transformer = initialize_str_to_int_transformer(min, max)
    return prompt(
            message,
            default=default_string,
            transformer=transformer
        )
