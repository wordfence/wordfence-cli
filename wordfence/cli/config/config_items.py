import abc
import base64
import json
from dataclasses import dataclass, fields
from enum import Enum
from functools import lru_cache
from typing import Optional, Any, Dict, Set, Tuple, Type, Callable, Union
from .typing import ConfigDefinitions

# see wordfence/config/__init__.py for special handling of reserved names
invalid_config_item_names: Set[str] = {
    'subcommand',
    'trailing_arguments'
}


class Context(Enum):
    ALL = 1
    """a config item that is available in both the CLI and INI contexts"""
    CLI = 2
    """a config item that is only available in the CLI context (not INI)"""
    CONFIG = 3
    """a config item that is only available in the INI context (not CLI)"""


class ArgumentType(Enum):
    ARGUMENT = 1
    """No names, just ordered CLI values"""
    FLAG = 2
    """boolean values set by name (no value) -- inverts the default value when
    provided"""
    OPTIONAL_FLAG = 3
    """boolean values set by name with an optional third state (None)
    representing the absence of a value"""
    OPTION = 4
    """required the option name plus a value"""
    OPTION_REPEATABLE = 5
    """an option that can be repeated multiple times with different values"""


@dataclass(frozen=True)
class ReferenceToken:
    """Instantiate a new instance to use the `x is y` language construct to
    determine if other instances point to the same token"""
    pass


not_set_token = ReferenceToken()


@dataclass(frozen=True)
class ConfigItemMeta:
    valid_options: Optional[Tuple[str]] = None
    multiple: Optional[bool] = None
    separator: Optional[str] = None
    value_type: Union[Type, Callable] = str
    accepts_file: bool = False
    accepts_directory: bool = False

    def accepts_paths(self) -> bool:
        return self.accepts_file or self.accepts_directory


@dataclass(frozen=True)
class ConfigItemDefinition:
    name: str
    property_name: str
    description: str
    context: Context
    argument_type: ArgumentType
    default: Any
    hidden: bool = False
    short_name: Optional[str] = None
    meta: Optional[ConfigItemMeta] = None
    category: str = 'General Options'

    @staticmethod
    def clean_argument_dict(source: Dict[str, Any]) -> Dict[str, Any]:
        return {key: value for key, value in source.items() if
                key in get_data_item_fields()}

    def has_options_list(self) -> bool:
        return True if self.meta and self.meta.valid_options else False

    def has_separator(self) -> bool:
        return True if self.meta and self.meta.separator else False

    def is_flag(self) -> bool:
        return self.argument_type == ArgumentType.FLAG \
            or self.argument_type == ArgumentType.OPTIONAL_FLAG

    def accepts_value(self) -> bool:
        return not self.is_flag()

    def get_value_type(self):
        if self.is_flag():
            return bool
        if not self.meta:
            return str
        return_type = self.meta.value_type
        if not return_type:
            if self.meta.accepts_paths():
                return bytes
            raise ValueError(
                f"Specified type not in the allow list: {self.meta.value_type}"
                )
        return return_type

    def accepts_paths(self) -> bool:
        return self.meta and self.meta.accepts_paths()

    @classmethod
    def from_dict(cls, source: dict):
        # The property name is always derived from the configuration's "name"
        # value. Any "property_name" value specified in the configuration is
        # ignored.
        source['property_name'] = source['name'].replace('-', '_')

        is_optional_flag = \
            ArgumentType.OPTIONAL_FLAG == source['argument_type']
        is_flag = (
                is_optional_flag or
                ArgumentType.FLAG == source['argument_type']
            )

        if source.get('default_type', None) == 'base64':
            if 'default' not in source:
                raise ValueError(
                    "When base64 default type is specified, a default value "
                    "must be present")
            source['default'] = base64.b64decode(source['default'])

        if 'default' not in source:
            source['default'] = not_set_token
        # convert enums
        source['context'] = source['context'] if isinstance(source['context'],
                                                            Context) else \
            Context[source['context']]
        source['argument_type'] = source['argument_type'] if isinstance(
            source['argument_type'], ArgumentType) else \
            ArgumentType[
                source['argument_type']]

        # convert the meta dict to an object to make it hashable
        if source.get('meta', False):
            # convert lists to tuples to make them hashable
            if source['meta'].get('valid_options', False):
                source['meta']['valid_options'] = tuple(
                    source['meta']['valid_options'])
            # set flags to booleans types
            # if another type is not already defined
            if not_set_token is source['meta'].get('value_type',
                                                   not_set_token) and is_flag:
                source['meta']['value_type'] = 'bool'
            source['meta'] = ConfigItemMeta(**source['meta'])
        else:
            source['meta'] = ConfigItemMeta()

        # sanity check
        if is_flag and not (
                    isinstance(source['default'], bool) or
                    (is_optional_flag and source['default'] is None)
                ):
            raise ValueError(
                f"Flag {source['name']} has a non-boolean value type defined: "
                f"{type(source['default'])}")
        return cls(**ConfigItemDefinition.clean_argument_dict(source))

    @classmethod
    def from_json(cls, source: str):
        return cls.from_dict(json.loads(source))


@dataclass(frozen=True)
class ConfigValue:
    definition: ConfigItemDefinition
    value: Any


class CanonicalValueExtractorInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (callable(subclass.get_canonical_value),
                callable(subclass.is_valid_source),
                callable(subclass.assert_is_valid_source))

    @abc.abstractmethod
    def is_valid_source(self, source: Any) -> bool:
        """Validate the source is supported"""
        raise NotImplementedError

    def assert_is_valid_source(self, source: Any) -> None:
        if not self.is_valid_source(source):
            raise ValueError(f"Invalid configuration source: {type(source)}")

    @abc.abstractmethod
    def get_canonical_value(self, definition: ConfigItemDefinition,
                            source: Any) -> Any:
        """Return the canonical configuration value as stored in the
        configuration source"""
        raise NotImplementedError

    @abc.abstractmethod
    def get_context(self) -> Context:
        raise NotImplementedError


@lru_cache(maxsize=1)
def get_data_item_fields() -> Set[str]:
    return set([x.name for x in fields(ConfigItemDefinition)])


def config_definitions_to_config_map(
            config_definitions: ConfigDefinitions
        ) -> Dict[str, ConfigItemDefinition]:
    result: Dict[str, ConfigItemDefinition] = {}
    used_short_names: Set[str] = set()
    implied_names: Set[str] = set()
    for name, value in config_definitions.items():
        value['name'] = name
        config_item = ConfigItemDefinition.from_dict(value)
        if config_item.name in result:
            raise KeyError(
                f"The name {json.dumps(config_item.name)} has already been "
                f"loaded")
        if config_item.name in implied_names:
            raise KeyError(
                f"A configured flag has already claimed "
                f"{json.dumps(config_item.name)} as an implied name")
        if config_item.short_name:
            if config_item.short_name in used_short_names:
                raise KeyError(
                    f"The short name {json.dumps(config_item.short_name)} "
                    f"has already been loaded")
            else:
                used_short_names.add(config_item.short_name)
        if config_item.is_flag():
            implied_name = f'no-{config_item.name}'
            if implied_name in implied_names:
                raise KeyError(
                    f"Another option has already taken the implied name "
                    f"{json.dumps(implied_name)}")
            implied_names.add(implied_name)

        if config_item.name in invalid_config_item_names:
            raise KeyError(
                f"The name {json.dumps(config_item.name)} is reserved")
        result[config_item.name] = config_item
    return result


def merge_config_maps(
            a: Dict[str, ConfigItemDefinition],
            b: Dict[str, ConfigItemDefinition]
        ) -> Dict[str, ConfigItemDefinition]:
    return {**a, **b}
