import os.path
from typing import IO, List, Optional, Any, Callable, Dict, Set
from enum import Enum
from collections import deque

from ..util.encoding import str_to_bytes

from .lexing import Lexer, Token, TokenType, CharacterType, STRING_ESCAPE


class SourceMetadata:

    def __init__(self, path: bytes):
        self.path = path


class Source:

    def __init__(
                self,
                stream: IO,
                metadata: SourceMetadata
            ):
        self.stream = stream
        self.metadata = metadata


class PhpException(Exception):
    pass


class ParsingException(PhpException):
    pass


class EvaluationException(PhpException):
    pass


class ImplementationException(PhpException):
    pass


class PhpStateType:
    pass


def make_strings_binary(value: Any) -> Any:
    if isinstance(value, str):
        return str_to_bytes(value)
    return value


class PhpType(Enum):
    STRING = bytes,
    INTEGER = int,
    ARRAY = List,
    NULL = type(None)

    def is_valid_value(self, value: Any) -> bool:
        return value is self.value or isinstance(value, self.value)

    def validate(self, value: Any) -> None:
        if not self.is_valid_value(value):
            raise EvaluationException(
                    'Value ' + repr(value) +
                    f' is not valid for type {self.name} ({self.value})'
                )

    @classmethod
    def for_python_value(cls, value: Any):
        value = make_strings_binary(value)
        for type in cls:
            if type.is_valid_value(value):
                return type
        raise ImplementationException(
                'Python value does not have a corresponding PHP type: '
                + repr(value)
            )


class PhpValue:

    def __init__(
                self,
                type: PhpType,
                value: Any
            ):
        type.validate(value)
        self.type = type
        self.value = value

    @classmethod
    def for_python_value(cls, value: Any):
        value = make_strings_binary(value)
        type = PhpType.for_python_value(value)
        return cls(
                type,
                value
            )


PHP_NULL = PhpValue(PhpType.NULL, None)
PHP_VOID = PHP_NULL  # TODO: Differentiate null and void


class Evaluable:

    def evaluate(self, state: PhpStateType) -> PhpValue:
        raise ImplementationException()


class PhpName:

    def __init__(
                self,
                components: List[bytes],
                base=None
            ):
        self.components = components
        self.base = base


class PhpEntity:

    def __init__(self):
        self.comments = []

    def attach_comment(self, comment: bytes) -> None:
        self.comments.append(comment)

    def attach_comments(self, comments: List[bytes]) -> None:
        self.comments.extend(comments)


class PhpIdentifiedEntity(PhpEntity):

    def __init__(self, name: bytes):
        super().__init__()
        self.name = name

    def __str__(self):
        return type(self).__name__ + ':' + self.name


class PhpVariable(PhpIdentifiedEntity):

    def __init__(
                self,
                name: bytes,
                value: PhpValue,
            ):
        super().__init__(name)
        self.value = value

    def assign(self, value: PhpValue):
        self.value = value


class PhpInstruction(PhpEntity, Evaluable):

    def __init__(self):
        pass

    def evaluate(self, state: PhpStateType) -> Any:
        pass


class PhpInstructionGroup(PhpEntity, Evaluable):

    def __init__(
                self,
                instructions: List[PhpInstruction] = None):
        self.instructions = instructions if instructions is not None else []

    def add_instruction(self, instruction: PhpInstruction) -> None:
        self.instructions.append(instruction)

    def evaluate(self, state: PhpStateType) -> PhpValue:
        for instruction in self.instructions:
            instruction.evaluate(state)
        return state.return_value


class PhpArgument(PhpIdentifiedEntity):
    pass


class PhpFunction(PhpEntity, Evaluable):

    def __init__(
                self,
                instruction_group: PhpInstructionGroup = None,
                arguments: List[PhpArgument] = None
            ):
        super().__init__()
        self.instruction_group = instruction_group \
            if instruction_group is not None \
            else PhpInstructionGroup()
        self.arguments = arguments if arguments is not None else []

    def evaluate(self, state: PhpStateType):
        # TODO: Pass arguments
        return self.instruction_group.evaluate(state)


class PhpVisibility(bytes, Enum):
    PRIVATE = b'private'
    PROTECTED = b'protected'
    PUBLIC = b'public'

    @classmethod
    def for_token_type(cls, token_type: TokenType):
        if token_type is TokenType.PRIVATE:
            return cls.PRIVATE
        elif token_type is TokenType.PROTECTED:
            return cls.PROTECTED
        elif token_type is TokenType.PUBLIC:
            return cls.PUBLIC
        else:
            return None


class PhpModifier(bytes, Enum):
    ABSTRACT = b'abstract'
    STATIC = b'static'
    FINAL = b'final'
    READONLY = b'readonly'

    @classmethod
    def for_token_type(cls, token_type: TokenType):
        if token_type is TokenType.ABSTRACT:
            return cls.ABSTRACT
        elif token_type is TokenType.STATIC:
            return cls.STATIC
        elif token_type is TokenType.FINAL:
            return cls.FINAL
        elif token_type is TokenType.READONLY:
            return cls.READONLY
        else:
            return None


class PhpModifierGroup:

    def __init__(
                self,
                visibility: PhpVisibility = PhpVisibility.PUBLIC,
                modifiers: Optional[Set[PhpModifier]] = None):
        self.visibility = visibility
        self.modifiers = modifiers if modifiers is not None else set()


class PhpClassMember(PhpEntity, Evaluable):

    def __init__(
                self,
                name: bytes,
                modifier_group: Optional[PhpModifierGroup] = None
            ):
        self.name = name
        self.modifier_group = modifier_group if modifier_group is not None \
            else PhpModifierGroup()


class PhpProperty(PhpClassMember):

    def evaluate(self, state: PhpStateType) -> PhpValue:
        # TODO: Implement this
        return PHP_NULL


class PhpMethod(PhpClassMember):

    def __init__(
                self,
                name: bytes,
                function: PhpFunction,
                modifier_group: Optional[PhpModifierGroup] = None
            ):
        super().__init__(name, modifier_group)
        self.function = function

    def evaluate(self, state: PhpStateType) -> PhpValue:
        # TODO: Implement this
        return PHP_NULL


class PhpClassConstant(PhpEntity, Evaluable):

    def __init__(
                self,
                class_name: bytes,
                constant_name: bytes
            ):
        self.class_name = class_name
        self.constant_name = constant_name

    def evaluate(self, state: PhpStateType) -> PhpValue:
        cls = state.get_class(self.class_name)
        if cls is None:
            raise EvaluationException(
                    f'Class {self.class_name} does not exist'
                )
        value = cls.get_constant(self.constant_name)
        return PhpValue.for_python_value(value)


class PhpClass(PhpIdentifiedEntity):

    def __init__(
                self,
                name: bytes,
                modifier_group: PhpModifierGroup
            ):
        super().__init__(name)
        self.modifier_group = modifier_group
        self.properties = {}
        self.methods = {}
        self.constants = {}

    def add_property(self, property: PhpProperty) -> None:
        self.properties[property.name] = property

    def add_method(self, method: PhpMethod) -> None:
        self.methods[method.name] = method

    def get_method(self, name: bytes) -> Optional[PhpMethod]:
        try:
            return self.methods[name]
        except KeyError:
            return None

    def add_constant(self, constant: PhpClassConstant) -> None:
        self.constants[constant.constant_name] = constant

    def get_constant(self, name: bytes) -> Optional[PhpClassConstant]:
        try:
            return self.constants[name]
        except KeyError:
            return None


class PhpDefinitions:

    def __init__(
                self,
                base_functions: Dict[bytes, Callable] = None,
                base_classes: Dict[bytes, PhpClass] = None
            ):
        self.functions = base_functions.copy()
        self.classes = base_classes.copy()

    def define_function(self, name: bytes, callable: Callable) -> None:
        self.functions[name] = callable

    def get_function(self, name: bytes) -> Optional[Callable]:
        try:
            return self.functions[name]
        except KeyError:
            return None

    def define_class(self, definition: PhpClass) -> None:
        self.classes[definition.name] = definition

    def get_class(self, name: bytes) -> Optional[PhpClass]:
        try:
            return self.classes[name]
        except KeyError:
            return None


class PhpScope:

    def __init__(self):
        self.variables = {}

    def get_variable(self, name: bytes) -> PhpVariable:
        try:
            return self.variables[name]
        except KeyError:
            variable = PhpVariable(
                    name=name,
                    value=PHP_NULL
                )
            self.variables[name] = variable
            return variable


class PhpEvaluationOptions:

    def __init__(
                self,
                allow_includes: bool = True
            ):
        self.allow_includes = allow_includes


class PhpState(PhpStateType):

    def __init__(
                self,
                definitions: PhpDefinitions,
                options: Optional[PhpEvaluationOptions] = None
            ):
        self.definitions = definitions
        self.global_scope = PhpScope()
        self.scope = self.global_scope
        self.constants = {}
        self.output = []
        self.return_value = None
        self.options = options if options is not None \
            else PhpEvaluationOptions()

    def define_constant(self, name: bytes, value: Any) -> None:
        if name in self.constants:
            raise EvaluationException(f'Constant {name} is already defined')
        self.constants[name] = value

    def get_constant(
                self,
                name: bytes,
                default_to_name: bool = True
            ) -> PhpValue:
        try:
            return self.constants[name]
        except KeyError:
            if default_to_name:
                return PhpValue(PhpType.STRING, name)
            return PHP_NULL

    def get_constant_value(
                self,
                name: bytes,
                default_to_name: bool = True
            ) -> PhpValue:
        return self.get_constant(name, default_to_name).value

    def get_variable(self, name: bytes) -> PhpVariable:
        return self.scope.get_variable(name)

    def get_variable_value(self, name: bytes) -> Any:
        return self.get_variable(name).value.value

    def write_output(self, output: bytes) -> None:
        self.output.append(output)


def php_define(state: PhpState, constant: PhpValue, value: PhpValue) -> None:
    state.define_constant(constant.value, value)


def php_defined(state: PhpState, constant: PhpValue) -> PhpValue:
    return PhpValue.for_python_value(constant.value in state.constants)


def php_dirname(state: PhpState, path: PhpValue) -> PhpValue:
    return PhpValue.for_python_value(
            os.fsencode(os.path.dirname(path.value))
        )


BASE_FUNCTIONS = {
        b'define': php_define,
        b'defined': php_defined,
        b'dirname': php_dirname
    }
BASE_CLASSES = {
    }


def initialize_php_definitions() -> PhpDefinitions:
    return PhpDefinitions(
            base_functions=BASE_FUNCTIONS,
            base_classes=BASE_CLASSES
        )


class PhpLiteral(PhpValue, PhpEntity, Evaluable):

    def evaluate(self, state: PhpState) -> PhpValue:
        return self


OPERATOR_MAP = dict()


class PhpOperator(PhpEntity):
    pass


class PhpUnaryOperator(PhpOperator):

    def __init__(
                self,
                operator: bytes,
                callable: Callable[[Any], Any]
            ):
        self.operator = operator
        self.callable = callable

    def apply(self, value: PhpValue) -> Any:
        return self.callable(value)


def _register_unary_operator(
            operator: bytes,
            callable: Callable[[Any], Any]
        ) -> None:
    instance = PhpUnaryOperator(operator, callable)
    OPERATOR_MAP[operator] = instance


_register_unary_operator(
        b'!',
        lambda value: PhpValue(value.type, not value.value)
    )


class PhpBinaryOperator(PhpOperator):

    def __init__(
                self,
                operator: bytes,
                callable: Callable[[Any, Any], Any]
            ):
        super().__init__()
        self.operator = operator
        self.callable = callable

    def apply(self, left: Any, right: Any) -> Any:
        return self.callable(left, right)


def _register_binary_operator(
            operator: bytes,
            callable: Callable[[Any, Any], Any]
        ):
    operator_instance = PhpBinaryOperator(operator, callable)
    OPERATOR_MAP[operator] = operator_instance


_register_binary_operator(
        b'.',
        lambda left, right: PhpValue(left.type, left.value + right.value)
    )
_register_binary_operator(
        b'===',
        lambda left, right: left.type is right.type and
        left.value == right.value
    )
_register_binary_operator(
        b'!==',
        lambda left, right: left.type is not right.type or
        left.value != right.value
    )
_register_binary_operator(
        b'==',
        lambda left, right: left.value == right.value
    )
_register_binary_operator(
        b'!=',
        lambda left, right: left.value != right.value
    )
_register_binary_operator(
        b'=',
        lambda left, right: left.assign(right)
    )
_register_binary_operator(
        b'>=',
        lambda left, right: left.value >= right.value
    )
_register_binary_operator(
        b'&&',
        lambda left, right: left.value and right.value
    )
_register_binary_operator(
        b'||',
        lambda left, right: left.value or right.value
    )


class PhpOutput(PhpInstruction):

    def __init__(self, content: bytes):
        super().__init__()
        self.content = content

    def evaluate(self, state: PhpState) -> PhpValue:
        state.write_output(self.content)
        return PHP_VOID


class PhpExpression(PhpInstruction):

    def __init__(self):
        self.components = []

    def add_component(self, component: PhpEntity) -> None:
        self.components.append(component)

    def evaluate(self, state: PhpState) -> PhpValue:
        operator = None
        value = None
        for component in self.components:
            if isinstance(component, Evaluable):
                new_value = component.evaluate(state)
                if operator is None:
                    if value is not None:
                        raise EvaluationException(
                                'Unexpected adjacent expressions'
                            )
                    value = new_value
                elif isinstance(operator, PhpUnaryOperator):
                    value = operator.apply(new_value)
                elif isinstance(operator, PhpBinaryOperator):
                    value = operator.apply(value, new_value)
                else:
                    raise EvaluationException(
                            'Unexpected operator type'
                        )
            elif isinstance(component, PhpOperator):
                if operator is not None:
                    raise EvaluationException('Unexpected adjacent operators')
                operator = component
            else:
                raise ImplementationException('Not yet implemented')
        if value is None:
            return PHP_NULL
        return value


class PhpDeclaration(PhpIdentifiedEntity):

    def __init__(self):
        pass


class PhpIdentifier(PhpEntity):

    def __init__(self, name: bytes, parent_name: Optional[bytes] = None):
        super().__init__()
        self.name = name
        self.parent_name = parent_name


class PhpVariableReference(PhpIdentifiedEntity, Evaluable):

    def evaluate(self, state: PhpState) -> PhpVariable:
        return state.scope.get_variable(self.name)


class PhpConstant(PhpIdentifiedEntity, Evaluable):

    def evaluate(self, state: PhpState) -> Any:
        try:
            return state.constants[self.name]
        except KeyError:
            # Constants are treated as strings if undefined
            return PhpValue.for_python_value(self.name)


class PhpMagicConstant(PhpEntity, Evaluable):

    def __init__(
                self,
                token_type: TokenType,
                source_metadata: SourceMetadata
            ):
        self.token_type = token_type
        self.source_metadata = source_metadata

    def evaluate(self, state: PhpState) -> Any:
        if self.token_type == TokenType.DIR:
            return PhpValue.for_python_value(
                    os.fsdecode(os.path.dirname(self.source_metadata.path))
                )
        elif self.token_type == TokenType.FILE:
            return PhpValue.for_python_value(
                    os.fsdecode(self.source_metadata.path)
                )
        else:
            raise EvaluationException('Unsupported magic constant')


class PhpInclude(PhpInstruction, Evaluable):

    def __init__(
                self,
                path: PhpExpression,
                required: bool = False,
                once: bool = False
            ):
        self.path = path
        self.required = required
        self.once = once

    def evaluate_path(self, state: PhpState) -> bytes:
        path = self.path.evaluate(state)
        if isinstance(path, bytes):
            return os.fsencode(path)
        raise EvaluationException(
                'Included path is not a string, received: {repr(path)}'
            )

    def evaluate(self, state: PhpState) -> Any:
        if not state.options.allow_includes:
            return None
        path = self.evaluate_path(state)
        context = parse_php_file(path)
        return context.evaluate(state=state)


class PhpCallable():

    def get_callable(self, state: PhpState) -> Callable:
        raise EvaluationException('get_callable is not implemented')


class PhpFunctionReference(PhpIdentifiedEntity, PhpCallable):

    def get_callable(self, state: PhpState) -> Callable:
        callable = state.definitions.get_function(self.name)
        if callable is None:
            raise EvaluationException(f'Function {self.name} is not defined')
        return callable


class PhpStaticMethodReference(PhpCallable):

    def __init__(self, class_name: bytes, method_name: bytes):
        self.class_name = class_name
        self.method_name = method_name

    def get_callable(self, state: PhpState) -> Callable:
        class_definition = state.definitions.get_class(self.class_name)
        callable = class_definition.get_method(self.method_name)
        if callable is None:
            raise EvaluationException(
                    f'Method {self.name} does not exist on class '
                    f'{self.class_name}'
                )
        return callable


class PhpMethodReference(PhpCallable):

    def __init__(
                self,
                method_name: bytes
            ):
        self.method_name = method_name


class PhpCallableInvocation(PhpEntity, Evaluable):

    def __init__(
                self,
                callable: PhpCallable,
                arguments: List[PhpExpression]
            ):
        self.callable = callable
        self.arguments = arguments

    def evaluate(self, state: PhpState) -> Any:
        arguments = [argument.evaluate(state) for argument in self.arguments]
        callable = self.callable.get_callable(state)
        return callable(state, *arguments)

    def __repr__(self) -> str:
        return repr(self.callable) + '(' + repr(self.arguments) + ')'


class PhpPropertyReference(PhpEntity, Evaluable):

    def __init__(
                self,
                property_name: bytes
            ):
        self.property_name = property_name


class PhpCondition(PhpEntity, Evaluable):

    def __init__(
                self,
                instruction_group: PhpInstructionGroup,
                expression: Optional[PhpExpression] = None
            ):
        self.expression = expression
        self.instruction_group = instruction_group

    def should_execute(self, state: PhpState) -> bool:
        if self.expression is None:
            return True
        return bool(self.expression.evaluate(state))

    def evaluate(self, state: PhpState) -> bool:
        if self.should_execute(state):
            self.instruction_group.evaluate(state)
            return True
        return False


class PhpConditional(Evaluable):

    def __init__(
                self,
                conditions: List[PhpCondition]
            ):
        self.conditions = conditions

    def evaluate(self, state: PhpState) -> None:
        for condition in self.conditions:
            if condition.evaluate(state):
                break


class PhpReturn(PhpInstruction):

    def __init__(self, expression: Optional[PhpExpression] = None):
        self.expression = expression

    def evaluate_return_value(self, state: PhpState) -> Any:
        if self.expression is None:
            return None
        return self.expression.evaluate(state)

    def evaluate(self, state: PhpState) -> Any:
        state.return_value = self.evaluate_return_value(state)


class PhpInstantiation(PhpInstruction):

    def __init__(
                self,
                class_name: PhpName,
                arguments: List[PhpExpression]
            ):
        self.class_name = class_name
        self.arguments = arguments

    def evaluate(self, state: PhpState) -> PhpValue:
        raise ImplementationException()


class PhpForeach(PhpInstruction):

    def __init__(
                self,
                expression: PhpExpression,
                instruction_group: PhpInstructionGroup,
                value_name: bytes,
                key_name: Optional[bytes]
            ):
        self.expression = expression
        self.instruction_group = instruction_group
        self.value_name = value_name
        self.key_name = key_name

    def evaluate(self, state: PhpState) -> PhpValue:
        return PHP_VOID


class PhpContext:

    def __init__(self):
        self.instructions = []
        self.definitions = initialize_php_definitions()
        self.state = PhpState(self.definitions)

    def get_includes(self) -> List[PhpInclude]:
        includes = []
        for instruction in self.instructions:
            if isinstance(instruction, PhpInclude):
                includes.append(instruction)
        return includes

    def evaluate(
                self,
                state: PhpState = None,
                options: PhpEvaluationOptions = None
            ) -> PhpState:
        if state is None:
            state = PhpState(
                    definitions=self.definitions
                )
        state.options = options
        for instruction in self.instructions:
            instruction.evaluate(state)
        return state


COMMENT_TOKEN_TYPES = {
        TokenType.COMMENT,
        TokenType.DOC_COMMENT
    }
INCLUDE_TOKEN_TYPES = {
        TokenType.INCLUDE,
        TokenType.INCLUDE_ONCE,
        TokenType.REQUIRE,
        TokenType.REQUIRE_ONCE
    }
REQUIRE_TOKEN_TYPES = {
        TokenType.REQUIRE,
        TokenType.REQUIRE_ONCE
    }
INCLUDE_ONCE_TOKEN_TYPES = {
        TokenType.INCLUDE_ONCE,
        TokenType.REQUIRE_ONCE
    }
MAGIC_CONSTANT_TOKEN_TYPES = {
        TokenType.LINE,
        TokenType.FILE,
        TokenType.DIR,
        TokenType.CLASS_C,
        TokenType.TRAIT_C,
        TokenType.METHOD_C,
        TokenType.FUNC_C,
        TokenType.NS_C
    }
SECONDARY_CONDITION_TOKEN_TYPES = {
        TokenType.ELSEIF,
        TokenType.ELSE
    }


class TokenStream:

    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.pending_comments = []
        self.pending_tokens = deque()

    def consume_preview(self) -> None:
        try:
            return self.pending_tokens.popleft()
        except IndexError:
            raise ParsingException('No preview tokens present')

    def accept_base_token(
                self,
                include_pending: bool = True
            ) -> Optional[Token]:
        if include_pending:
            try:
                return self.pending_tokens.popleft()
            except IndexError:
                pass  # No pending tokens
        return self.lexer.get_next_token()

    def accept_token(self, include_pending: bool = True) -> Optional[Token]:
        while (token := self.accept_base_token()) is not None:
            if token.type is TokenType.WHITESPACE:
                continue
            elif token.type in COMMENT_TOKEN_TYPES:
                self.pending_comments.append(token.value)
            else:
                return token
        return None

    def require_token(self) -> Token:
        token = self.accept_token()
        if token is None:
            raise ParsingException('Token expected')
        return token

    def require_token_of_type(self, type: TokenType) -> Token:
        token = self.require_token()
        if token.type is not type:
            raise ParsingException(f'Expected token of type {type}')
        return token

    def require_token_of_types(self, types: Set[TokenType]) -> Token:
        token = self.require_token()
        if token.type not in types:
            types_string = ', '.join(types)
            raise ParsingException(
                    'Expected token of one of the following types: '
                    f'{types_string}'
                )
        return token

    def require_semicolon(self) -> None:
        token = self.require_token()
        if token.is_semicolon():
            return
        raise ParsingException('Expected semicolon')

    def require_character(self, type: CharacterType) -> None:
        token = self.require_token()
        if token.type == TokenType.CHARACTER \
                and token.value == type:
            return
        raise ParsingException(f'Expected character: {type}')

    def require_equals(self) -> None:
        self.require_character(CharacterType.EQUALS)

    def take_comments(self) -> List[bytes]:
        comments = self.pending_comments
        self.pending_comments = []
        return comments

    def push_token(self, token: Token) -> None:
        self.pending_tokens.append(token)

    def preview_token(self) -> Optional[Token]:
        next = self.accept_token(False)
        if next is not None:
            self.push_token(next)
        return next

    def require_preview_token(self) -> Token:
        token = self.preview_token()
        if token is None:
            raise ParsingException('Unexpected end of token stream')
        return token


class TagStateChanged(Exception):

    def __init__(self, state: bool):  # noqa: B042
        self.state = state


expression_level = 0


class Parser:

    def __init__(self, source: Source):
        self.source = source
        self.lexer = Lexer(source.stream)
        self.token_stream = TokenStream(self.lexer)

    def parse_instruction(
                self,
                token_stream: TokenStream
            ) -> Optional[PhpInstruction]:
        return None

    def parse_string(self, token: Token) -> PhpLiteral:
        if token.type != TokenType.CONSTANT_ENCAPSED_STRING:
            raise ParsingException('Token is not a valid string')
        value = token.value[1:-1].replace(STRING_ESCAPE, b'')
        return PhpLiteral(PhpType.STRING, value)

    def parse_integer(self, token: Token) -> PhpLiteral:
        if token.type != TokenType.LNUMBER:
            raise ParsingException('Token is not a valid integer literal')
        value = int(token.value)
        return PhpLiteral(PhpType.INTEGER, value)

    def parse_magic_constant(self, token: Token) -> PhpMagicConstant:
        if token.type not in MAGIC_CONSTANT_TOKEN_TYPES:
            raise ParsingException('Token is not a magic constant')
        return PhpMagicConstant(token.type, self.source.metadata)

    def parse_constant(self, identifier: PhpIdentifier) -> PhpConstant:
        if identifier.parent_name is not None:
            return PhpClassConstant(identifier.parent_name, identifier.name)
        return PhpConstant(identifier.name)

    def parse_operator(self, token: Token) -> PhpBinaryOperator:
        try:
            return OPERATOR_MAP[token.value]
        except KeyError:
            raise ParsingException(f'Unrecognized operator: {token}')

    def parse_identifier(
                self,
                token: Token,
                token_stream: TokenStream
            ) -> PhpIdentifier:
        if token.type is not TokenType.STRING:
            raise ParsingException(
                    'First token of identifier is not the correct type'
                )
        name = token.value
        parent_name = None
        preview = token_stream.preview_token()
        if preview.type is TokenType.PAAMAYIM_NEKUDOTAYIM:
            parent_name = name
            token_stream.consume_preview()
            preview = token_stream.preview_token()
            name = token_stream.require_token_of_types(
                    {TokenType.STRING, TokenType.VARIABLE}
                ).value
        return PhpIdentifier(name, parent_name)

    def parse_array(
                self,
                token: Token,
                token_stream: TokenStream
            ) -> PhpLiteral:
        if token.type is not TokenType.ARRAY:
            raise ParsingException(f'Expected array, received: {token}')
        items = self.parse_argument_list(token_stream)
        return PhpLiteral(PhpType.ARRAY, items)

    def parse_name(
                self,
                token_stream: TokenStream
            ) -> PhpName:
        components = []
        base = None  # TODO: Default to current namespace
        first = True
        accept_component = True
        while True:
            token = token_stream.require_preview_token()
            if first:
                first = False
                if token.type is TokenType.NS_SEPARATOR:
                    token_stream.consume_preview()
                    base = None
                    continue
            if token.type is TokenType.STRING:
                if not accept_component:
                    raise ParsingException('Missing namespace separator')
                components.append(token.value)
            elif token.type is TokenType.NS_SEPARATOR:
                if accept_component:
                    raise ParsingException('Missing name component')
            else:
                break
            token_stream.consume_preview()
            accept_component = not accept_component
        if len(components) == 0:
            raise ParsingException('Name is empty')
        return PhpName(
                components,
                base
            )

    def parse_instantiation(
                self,
                token: Token,
                token_stream: TokenStream
            ) -> PhpInstantiation:
        if token.type is not TokenType.NEW:
            raise ParsingException('Expected new, received: {token}')
        class_name = self.parse_name(token_stream)
        arguments = self.parse_argument_list(token_stream)
        return PhpInstantiation(
                class_name,
                arguments
            )

    def parse_object_access(
                self,
                token_stream: TokenStream
            ):
        token = token_stream.requir_token()
        if token.type is TokenType.STRING:
            preview = token_stream.require_preview_token()
            if preview.is_opening_parenthesis():
                arguments = self.parse_argument_list(token_stream)
                return PhpCallableInvocation(
                        PhpMethod(token.value),
                        arguments
                    )
            else:
                pass

    def parse_expression_component(
                self,
                token: Token,
                token_stream: TokenStream
            ) -> PhpEntity:
        # TODO: Parse more expression components
        if token.type is TokenType.CONSTANT_ENCAPSED_STRING:
            return self.parse_string(token)
        elif token.type is TokenType.LNUMBER:
            return self.parse_integer(token)
        elif token.type in MAGIC_CONSTANT_TOKEN_TYPES:
            return self.parse_magic_constant(token)
        elif token.type is TokenType.STRING:
            if token.value.lower() == 'null':
                return PHP_NULL
            identifier = self.parse_identifier(token, token_stream)
            preview = token_stream.preview_token()
            if preview is not None:
                if preview.is_character(CharacterType.OPEN_PARENTHESIS):
                    return self.parse_invocation(
                            identifier,
                            token_stream
                        )
            return self.parse_constant(identifier)
        elif token.type is TokenType.VARIABLE:
            return PhpVariableReference(
                    self.parse_variable_name(token)
                )
        elif token.type is TokenType.ARRAY:
            return self.parse_array(token, token_stream)
        elif token.type is TokenType.NEW:
            return self.parse_instantiation(token, token_stream)
        elif token.type is TokenType.NS_SEPARATOR:
            # TODO: Apply root namespace to subsequent element
            next = token_stream.require_token()
            return self.parse_expression_component(next, token_stream)
        elif token.type in INCLUDE_TOKEN_TYPES:
            return self.parse_include(token, token_stream)
        elif token.type is TokenType.OBJECT_OPERATOR:
            return self.parse_object_access(token_stream)
        elif token.value in OPERATOR_MAP:
            return self.parse_operator(token)
        else:
            raise ParsingException(
                    f'Unrecognized token in expression: {token}'
                )

    def parse_expression(
                self,
                token_stream: TokenStream,
                nested: bool = False,
                terminal_tokens: Set[TokenType] = None
            ) -> PhpExpression:
        global expression_level
        expression_level += 1
        expression = PhpExpression()
        while True:
            token = token_stream.accept_token()
            if token is None or token.is_semicolon():
                if nested:
                    token_stream.push_token(token)
                break
            if token.is_character({
                        CharacterType.COMMA,
                        CharacterType.CLOSE_PARENTHESIS,
                        CharacterType.CLOSE_BRACE
                    }) or (
                        terminal_tokens is not None
                        and token.type in terminal_tokens
                    ):
                token_stream.push_token(token)
                break
            if token.is_character(CharacterType.OPEN_PARENTHESIS):
                component = self.parse_expression(token_stream, True)
                token_stream.require_character(CharacterType.CLOSE_PARENTHESIS)
            else:
                component = self.parse_expression_component(
                            token,
                            token_stream
                        )
            expression.add_component(component)
        expression_level -= 1
        return expression

    def parse_variable_name(self, token: Token) -> bytes:
        return token.value[1:]

    def parse_include(
                self,
                token: Token,
                token_stream: TokenStream,
            ) -> PhpInclude:
        expression = self.parse_expression(token_stream, True)
        return PhpInclude(
                expression,
                required=token in REQUIRE_TOKEN_TYPES,
                once=token in INCLUDE_ONCE_TOKEN_TYPES
            )

    def parse_argument_list(
                self,
                token_stream: TokenStream
            ) -> List:
        token_stream.require_character(CharacterType.OPEN_PARENTHESIS)
        arguments = []
        while True:
            next = token_stream.accept_token()
            if next.is_character(CharacterType.CLOSE_PARENTHESIS):
                break
            if next.is_character(CharacterType.COMMA):
                continue
            token_stream.push_token(next)
            expression = self.parse_expression(token_stream, True)
            arguments.append(expression)
        return arguments

    def parse_invocation(
                self,
                identifier: PhpIdentifier,
                token_stream: TokenStream
            ) -> PhpCallableInvocation:
        arguments = self.parse_argument_list(token_stream)
        if identifier.parent_name is None:
            callable = PhpFunctionReference(identifier.name)
        else:
            callable = PhpStaticMethodReference(
                        identifier.parent_name,
                        identifier.name
                    )
        return PhpCallableInvocation(
                callable,
                arguments
            )

    def parse_return(
                self,
                token_stream: TokenStream
            ) -> PhpReturn:
        token_stream.require_token_of_type(TokenType.RETURN)
        preview = token_stream.preview_token()
        if preview.is_semicolon():
            expression = None
        else:
            expression = self.parse_expression(token_stream, True)
        return PhpReturn(expression)

    def parse_modifiers(
                self,
                token_stream: TokenStream,
                allowed: Set = None
            ) -> PhpModifierGroup:
        group = PhpModifierGroup()
        visibility_specified = False
        while True:
            token = token_stream.preview_token()
            if token is None:
                break
            visibility = PhpVisibility.for_token_type(token.type)
            if visibility is not None:
                if visibility_specified:
                    raise ParsingException(
                            'Multiple visibility modifiers found'
                        )
                if allowed is not None and visibility not in allowed:
                    raise ParsingException(
                            f'Visibility {visibility} is not permitted'
                        )
                group.visibility = visibility
                visibility_specified = True
                token_stream.consume_preview()
                continue
            modifier = PhpModifier.for_token_type(token.type)
            if modifier is not None:
                if allowed is not None and modifier not in allowed:
                    raise ParsingException(
                            f'Modifier {modifier} is not permitted'
                        )
                group.modifiers.add(modifier)
                token_stream.consume_preview()
                continue
            break
        return group

    def parse_property(
                self,
                token: Token,
                token_stream: TokenStream,
                modifier_group: PhpModifierGroup
            ) -> PhpProperty:
        name = self.parse_variable_name(token)
        token_stream.require_semicolon()
        property = PhpProperty(name, modifier_group)
        # TODO: Parse default values
        return property

    def parse_arguments(
                self,
                token_stream: TokenStream
            ) -> List[PhpArgument]:
        arguments = []
        token_stream.require_character(CharacterType.OPEN_PARENTHESIS)
        while (token := token_stream.preview_token()) is not None:
            if token.is_closing_parenthesis():
                break
            if token.type is TokenType.VARIABLE:
                token_stream.consume_preview()
                arguments.append(PhpArgument(token.value))
            token = token_stream.preview_token()
            if token is None or token.is_closing_parenthesis():
                break
            if token.is_comma():
                token_stream.consume_preview()
                continue
            raise ParsingException(
                    f'Unexpected token in function arguments: {token}'
                )
        token_stream.require_character(CharacterType.CLOSE_PARENTHESIS)
        return arguments

    def parse_function(
                self,
                token_stream: TokenStream,
            ) -> PhpFunction:
        arguments = self.parse_arguments(token_stream)
        token_stream.require_character(CharacterType.OPEN_BRACE)
        instruction_group = PhpInstructionGroup()
        in_php_tag = True
        while True:
            preview = token_stream.preview_token()
            if preview.is_character(CharacterType.CLOSE_BRACE):
                token_stream.consume_preview()
                break
            else:
                in_php_tag, instruction = self.parse_any(
                        token_stream,
                        in_php_tag
                    )
                if instruction is None:
                    break
                instruction_group.add_instruction(instruction)
        return PhpFunction(
                instruction_group,
                arguments
            )

    def parse_method(
                self,
                token_stream: TokenStream,
                modifier_group: PhpModifierGroup
            ) -> PhpMethod:
        name = token_stream.require_token_of_type(TokenType.STRING).value
        function = self.parse_function(token_stream)
        return PhpMethod(
                name,
                function,
                modifier_group
            )

    def parse_members(
                self,
                token_stream: TokenStream,
                definition: PhpClass
            ) -> None:
        while True:
            modifier_group = self.parse_modifiers(token_stream)
            token = token_stream.preview_token()
            if token is None:
                break
            if token.type is TokenType.VARIABLE:
                token_stream.consume_preview()
                property = self.parse_property(
                        token,
                        token_stream,
                        modifier_group
                    )
                definition.add_property(property)
            elif token.type is TokenType.FUNCTION:
                token_stream.consume_preview()
                method = self.parse_method(
                        token_stream,
                        modifier_group
                    )
                definition.add_method(method)
            elif token.is_character(CharacterType.CLOSE_BRACE):
                break
            else:
                raise ParsingException(
                        f'Unexpected token in class definition: {token}'
                    )

    def parse_class(
                self,
                token_stream: TokenStream
            ) -> PhpClass:
        modifier_group = self.parse_modifiers(
                token_stream,
                {
                    PhpModifier.ABSTRACT,
                    PhpModifier.FINAL
                }
            )
        token_stream.require_token_of_type(TokenType.CLASS)
        name = token_stream.require_token_of_type(TokenType.STRING).value
        definition = PhpClass(
                name,
                modifier_group
            )
        token_stream.require_character(CharacterType.OPEN_BRACE)
        self.parse_members(token_stream, definition)
        token_stream.require_character(CharacterType.CLOSE_BRACE)
        return definition

    def parse_block(
                self,
                token_stream: TokenStream
            ) -> PhpInstructionGroup:
        instruction_group = PhpInstructionGroup()
        next = token_stream.require_preview_token()
        if next.is_character(CharacterType.OPEN_BRACE):
            token_stream.require_character(CharacterType.OPEN_BRACE)
            while True:
                next = token_stream.require_preview_token()
                if next.is_character(CharacterType.CLOSE_BRACE):
                    break
                instruction = self.parse_statement(token_stream)
                instruction_group.add_instruction(instruction)
            token_stream.require_character(CharacterType.CLOSE_BRACE)
        else:
            instruction = self.parse_statement(token_stream)
            instruction_group.add_instruction(instruction)
        return instruction_group

    def parse_condition(
                self,
                token_stream: TokenStream,
                first: bool = True
            ) -> Optional[PhpCondition]:
        token = token_stream.preview_token()
        if first:
            token_stream.require_token()
            if token.type is not TokenType.IF:
                raise ParsingException(
                        f'Unexpected token in conditional: {token}'
                    )
        else:
            if token is None or \
                    token.type not in SECONDARY_CONDITION_TOKEN_TYPES:
                return None
            token_stream.consume_preview()
        if token.type is TokenType.ELSE:
            expression = None
        else:
            token_stream.require_character(CharacterType.OPEN_PARENTHESIS)
            expression = self.parse_expression(token_stream, True)
            token_stream.require_character(CharacterType.CLOSE_PARENTHESIS)
        instruction_group = self.parse_block(token_stream)
        return PhpCondition(instruction_group, expression)

    def parse_conditional(
                self,
                token_stream: TokenStream
            ) -> PhpConditional:
        first = True
        conditions = []
        while True:
            condition = self.parse_condition(token_stream, first)
            if condition is None:
                if first:
                    raise ParsingException('Malformed condition')
                break
            conditions.append(condition)
            first = False
        return PhpConditional(conditions)

    def parse_foreach(
                self,
                token_stream: TokenStream
            ) -> PhpForeach:
        token_stream.require_token_of_type(TokenType.FOREACH)
        token_stream.require_character(CharacterType.OPEN_PARENTHESIS)
        expression = self.parse_expression(token_stream, True, {TokenType.AS})
        token_stream.require_token_of_type(TokenType.AS)
        first_name = token_stream.require_token_of_type(
                TokenType.VARIABLE
            ).value
        preview = token_stream.require_preview_token()
        if preview.type is TokenType.DOUBLE_ARROW:
            token_stream.consume_preview()
            second_name = token_stream.require_token_of_type(
                    TokenType.VARIABLE
                ).value
        elif preview.is_closing_parenthesis():
            second_name = None
        token_stream.require_character(CharacterType.CLOSE_PARENTHESIS)
        instruction_group = self.parse_block(token_stream)
        if second_name is None:
            value_name = first_name
            key_name = None
        else:
            key_name = first_name
            value_name = second_name
        return PhpForeach(
                expression,
                instruction_group,
                value_name,
                key_name
            )

    def parse_output(
                self,
                token_stream: TokenStream
            ) -> Optional[PhpOutput]:
        content = None
        while (token := token_stream.accept_base_token()) is not None:
            if token.type is TokenType.INLINE_HTML:
                if content is None:
                    content = token.value
                else:
                    content = content + token.value
            elif token.type is TokenType.OPEN_TAG:
                if content is None:
                    raise TagStateChanged(True)
                else:
                    break
            elif token.type is TokenType.CLOSE_TAG:
                raise TagStateChanged(False)
            else:
                raise ParsingException(f'Unexpected token: {token}')
        if content is not None:
            return PhpOutput(content)
        return None

    def parse_statement(
                self,
                token_stream: TokenStream,
                in_php_tag: bool = False
            ) -> Optional[PhpInstruction]:
        preview = token_stream.preview_token()
        if preview is None:
            return None
        elif preview.type is TokenType.CLOSE_TAG:
            raise TagStateChanged(False)
        elif preview.type is TokenType.RETURN:
            return self.parse_return(token_stream)
        elif preview.type is TokenType.CLASS:
            return self.parse_class(token_stream)
        elif preview.type is TokenType.IF:
            return self.parse_conditional(token_stream)
        elif preview.type is TokenType.FOREACH:
            return self.parse_foreach(token_stream)
        else:
            return self.parse_expression(token_stream)

    def parse_any(
                self,
                token_stream: TokenStream,
                in_php_tag: bool = False
            ) -> (bool, Optional[PhpInstruction]):
        try:
            if in_php_tag:
                return (True, self.parse_statement(token_stream))
            else:
                return (False, self.parse_output(token_stream))
        except TagStateChanged as change:
            return self.parse_any(token_stream, change.state)

    def parse(self, context: PhpContext = None) -> PhpContext:
        if context is None:
            context = PhpContext()
        in_php_tag = False
        while True:
            in_php_tag, instruction = self.parse_any(
                    self.token_stream,
                    in_php_tag
                )
            if instruction is None:
                break
            context.instructions.append(instruction)
        return context


def parse_php_file(path: bytes) -> PhpContext:
    try:
        with open(path, 'rb') as stream:
            metadata = SourceMetadata(path)
            source = Source(stream, metadata)
            parser = Parser(source)
            return parser.parse()
    except OSError as error:
        raise ParsingException(
                f'Unable to read file at {path}'
            ) from error
