from typing import Optional, Any, Set


class ValidationException(Exception):

    def __init__(self, key: list, message: str, value=None):  # noqa: B042
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

    def __init__(
                self,
                expected: Optional[dict] = None,
                validator: Validator = None,
                allow_empty: bool = False,
                optional_keys: Optional[Set[str]] = None
            ):
        self.expected = expected if expected is not None else dict()
        self.validator = validator
        self.allow_empty = allow_empty
        self.optional_keys = optional_keys if optional_keys is not None else {}

    def _validate_expected_fields(self, data: dict, parent_key: list) -> None:
        for key, expected_type in self.expected.items():
            aggregate_key = parent_key + [key]
            try:
                value = data[key]
                self.validate_type(aggregate_key, value, expected_type)
            except KeyError:
                if key not in self.optional_keys:
                    raise ValidationException(aggregate_key, 'Key not present')

    def _validate_all_fields(self, data: dict, parent_key: list) -> None:
        if self.validator is None:
            return
        for key, value in data.items():
            if key not in self.expected:
                self.validator.validate(value, parent_key + [key])

    def validate(self, data, parent_key: Optional[list] = None) -> None:
        if parent_key is None:
            parent_key = []
        if not isinstance(data, dict):
            raise ValidationException(
                    parent_key,
                    'Element must be a dictionary',
                    data
                )
        if self.allow_empty and len(data) == 0:
            return
        self._validate_expected_fields(data, parent_key)
        self._validate_all_fields(data, parent_key)

    def add_field(self, key: Any, expected):
        self.expected[key] = expected


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


class AllowedValueValidator(Validator):

    def __init__(self, allowed: set):
        self.allowed = allowed

    def validate(self, data, parent_key: Optional[list] = None) -> None:
        for value in self.allowed:
            if data == value:
                return
        raise ValidationException(
                parent_key,
                'Value is not in allowed set: ' + repr(data)
            )


class OptionalValueValidator(Validator):

    def __init__(self, expected):
        self.expected = expected

    def validate(self, data, parent_key: Optional[list] = None) -> None:
        if data is None:
            return
        if parent_key is None:
            parent_key = []
        if isinstance(self.expected, Validator):
            self.expected.validate(data, parent_key)
        else:
            self.validate_type(parent_key, data, self.expected)


class NumberValidator(Validator):

    def __init__(self):
        pass

    def validate(self, data, parent_key: Optional[list] = None) -> None:
        if isinstance(data, int) or isinstance(data, float):
            return
        raise ValidationException(
                parent_key,
                'Value is not a valid number: ' + repr(data)
            )
