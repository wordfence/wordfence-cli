import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from ..php.parsing import (
        PhpBinaryOperator,
        PhpCallableInvocation,
        PhpConditional,
        PhpConstant,
        PhpExpression,
        PhpInstruction,
        PhpInstructionGroup,
        PhpLiteral,
        PhpMagicConstant,
        PhpVariableReference,
        parse_php_file
    )


@dataclass
class WordpressConfigState:
    constants: Dict[bytes, bytes] = field(default_factory=dict)
    variables: Dict[bytes, bytes] = field(default_factory=dict)

    def get_constant_value(
                self,
                name: bytes,
                default_to_name: bool = True
            ) -> Optional[bytes]:
        try:
            return self.constants[name]
        except KeyError:
            if default_to_name:
                return name
            return None

    def get_variable_value(self, name: bytes) -> Optional[bytes]:
        return self.variables.get(name)


class WordpressConfigParser:

    def __init__(self, path: bytes):
        self.path = os.fsencode(path)
        self.state = WordpressConfigState()

    def parse(self) -> WordpressConfigState:
        context = parse_php_file(self.path)
        self._process_instructions(context.instructions)
        return self.state

    def _process_instructions(
                self,
                instructions: Iterable[PhpInstruction]
            ) -> None:
        for instruction in instructions:
            self._process_instruction(instruction)

    def _process_instruction(self, instruction: PhpInstruction) -> None:
        if isinstance(instruction, PhpExpression):
            self._process_expression(instruction)
        elif isinstance(instruction, PhpInstructionGroup):
            self._process_instructions(instruction.instructions)
        elif isinstance(instruction, PhpConditional):
            for condition in instruction.conditions:
                instructions = condition.instruction_group.instructions
                self._process_instructions(instructions)

    def _process_expression(self, expression: PhpExpression) -> None:
        components = expression.components
        if len(components) == 0:
            return
        first = components[0]
        if isinstance(first, PhpCallableInvocation):
            self._process_callable(first)
        elif isinstance(first, PhpVariableReference):
            self._process_assignment(components)

    def _process_callable(self, invocation: PhpCallableInvocation) -> None:
        callable_reference = invocation.callable
        name = getattr(callable_reference, 'name', None)
        if name is None:
            return
        normalized = name.lower()
        has_arguments = len(invocation.arguments) >= 2
        if normalized == b'define' and has_arguments:
            constant_name = self._resolve_expression(invocation.arguments[0])
            constant_value = self._resolve_expression(invocation.arguments[1])
            if constant_name is not None and constant_value is not None:
                self.state.constants[constant_name] = constant_value

    def _process_assignment(self, components) -> None:
        if len(components) < 3:
            return
        variable = components[0]
        operator = components[1]
        if not isinstance(operator, PhpBinaryOperator) \
                or operator.operator != b'=':
            return
        value = self._resolve_components(components[2:])
        if value is not None:
            self.state.variables[variable.name] = value

    def _resolve_expression(
                self,
                expression: PhpExpression
            ) -> Optional[bytes]:
        return self._resolve_components(expression.components)

    def _resolve_components(self, components) -> Optional[bytes]:
        value: Optional[bytes] = None
        pending_operator: Optional[bytes] = None
        for component in components:
            if isinstance(component, PhpBinaryOperator):
                pending_operator = component.operator
                continue
            resolved = self._resolve_component(component)
            if resolved is None:
                return None
            if value is None:
                value = resolved
            else:
                if pending_operator == b'.':
                    value = value + resolved
                elif pending_operator in {b'.=', b'='}:
                    value = resolved
                else:
                    return None
            pending_operator = None
        return value

    def _resolve_component(self, component) -> Optional[bytes]:
        if isinstance(component, PhpLiteral):
            return self._convert_literal(component.value)
        if isinstance(component, PhpExpression):
            return self._resolve_expression(component)
        if isinstance(component, PhpCallableInvocation):
            return self._resolve_callable_component(component)
        if isinstance(component, PhpVariableReference):
            return self.state.variables.get(component.name)
        if isinstance(component, PhpConstant):
            return self.state.constants.get(component.name)
        if isinstance(component, PhpMagicConstant):
            return self._resolve_magic_constant(component)
        return None

    def _resolve_callable_component(
                self,
                invocation: PhpCallableInvocation
            ) -> Optional[bytes]:
        callable_reference = invocation.callable
        name = getattr(callable_reference, 'name', None)
        if name is None:
            return None
        normalized = name.lower()
        if normalized == b'constant' and len(invocation.arguments) >= 1:
            constant_name = self._resolve_expression(
                    invocation.arguments[0]
                )
            if constant_name is not None:
                return self.state.constants.get(constant_name)
        return None

    def _resolve_magic_constant(
                self,
                constant: PhpMagicConstant
            ) -> Optional[bytes]:
        if hasattr(constant, 'token_type'):
            token = constant.token_type
            if token.name == 'DIR':
                return os.path.dirname(self.path)
            if token.name == 'FILE':
                return self.path
        return None

    def _convert_literal(self, value) -> Optional[bytes]:
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode('latin1')
        if isinstance(value, int):
            return str(value).encode('latin1')
        return None


def parse_wordpress_config(path: bytes) -> WordpressConfigState:
    parser = WordpressConfigParser(path)
    return parser.parse()
