from typing import Optional


class ValidationException(Exception):

    def __init__(self, key: list, message: str, value=None):
        self.key = key
        self.value = value
        super().__init__(
                self.get_key_as_string() +
                ': ' +
                message +
                ', received: ' +
                repr(value)
            )

    def get_key_as_string(self) -> str:
        return '.'.join([str(component) for component in self.key])


class Validator:

    def validate(self, data, parent_key: Optional[list] = None):
        pass

    def validate_type(self, key, value, expected_type) -> None:
        if isinstance(expected_type, Validator):
            expected_type.validate(value, key)
        elif not isinstance(value, expected_type):
            raise ValidationException(
                    key,
                    'Value must be of type ' + str(expected_type),
                    value
                )


class DictionaryValidator(Validator):

    def __init__(self, expected: dict = None):
        self.expected = expected

    def validate(self, data, parent_key: Optional[list] = None) -> None:
        if parent_key is None:
            parent_key = []
        if not isinstance(data, dict):
            raise ValidationException(
                    parent_key,
                    'Element must be a dictionary',
                    data
                )
        for key, expected_type in self.expected.items():
            aggregate_key = parent_key + [key]
            try:
                value = data[key]
                self.validate_type(aggregate_key, value, expected_type)
            except KeyError:
                raise ValidationException(aggregate_key, 'Key not present')


class ListValidator(Validator):

    def __init__(self, expected):
        self.expected = expected

    def validate(self, data, parent_key: Optional[list] = None) -> None:
        if parent_key is None:
            parent_key = []
        if not isinstance(data, list):
            raise ValidationException(
                    parent_key,
                    'Element must be a list',
                    data
                )
        if isinstance(self.expected, dict):
            for index, expected_type in self.expected.items():
                key = parent_key + [index]
                try:
                    value = data[index]
                    self.validate_type(key, data[index], expected_type)
                except IndexError:
                    raise ValidationException(
                            key,
                            'Index does not exist in list'
                        )
        else:
            for index, value in enumerate(data):
                self.validate_type(parent_key + [index], value, self.expected)
