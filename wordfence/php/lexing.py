import re

from collections import deque
from enum import Enum, auto
from typing import Generator, IO, Optional, Union, Set


class LexingException(Exception):
    pass


class MatchType(Enum):
    NONE = auto(),
    MATCH = auto(),
    FINAL_MATCH = auto(),
    PARTIAL_MATCH = auto()


class TokenMatcher:

    def match(value: str) -> MatchType:
        return MatchType.NONE


def match_literal(literal: str, value: str) -> MatchType:
    if value == literal:
        return MatchType.FINAL_MATCH
    elif len(value) < len(literal) and literal.find(value) == 0:
        return MatchType.PARTIAL_MATCH
    else:
        return MatchType.NONE


class LiteralTokenMatcher(TokenMatcher):

    def __init__(self, value: str):
        self.value = value

    def match(self, value: str) -> MatchType:
        return match_literal(self.value, value)


class WhitespaceTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        # TODO: Does this match PHP's definition of whitespace?
        if value.isspace():
            return MatchType.MATCH
        return MatchType.NONE


class OpenTagTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        # TODO: Handle tag variations
        return match_literal('<?php', value)


DOC_COMMENT_START = '/*'
DOC_COMMENT_END = '*/'
COMMENT_START = '//'
COMMENT_END = '\n'


class EnclosedTokenMatcher(TokenMatcher):

    def __init__(self, start: str, end: str):
        self.start = start
        self.end = end
        self.end_length = len(end)

    def match(self, value: str) -> MatchType:
        if value.find(self.start) == 0:
            if value.find(self.end) == \
                    len(value) - self.end_length:
                return MatchType.FINAL_MATCH
            else:
                return MatchType.PARTIAL_MATCH
        if self.start.find(value) == 0:
            return MatchType.PARTIAL_MATCH
        return MatchType.NONE


class DocCommentTokenMatcher(EnclosedTokenMatcher):

    def __init__(self):
        super().__init__(
                DOC_COMMENT_START,
                DOC_COMMENT_END
            )


class CommentTokenMatcher(EnclosedTokenMatcher):

    def __init__(self):
        super().__init__(
                COMMENT_START,
                COMMENT_END
            )


VARIABLE_PREFIX = '$'
IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*$')


class VariableTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        if value[0] == VARIABLE_PREFIX:
            if IDENTIFIER_PATTERN.match(value[1:]) is not None:
                return MatchType.MATCH
            if len(value) == 1:
                return MatchType.PARTIAL_MATCH
        return MatchType.NONE


class IdentifierTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        if IDENTIFIER_PATTERN.match(value):
            return MatchType.MATCH
        return MatchType.NONE


class SingleCharacterTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        if len(value) == 1:
            return MatchType.MATCH
        return MatchType.NONE


STRING_QUOTES = {
    '"',
    "'"
}
STRING_ESCAPE = "\\"


class StringLiteralTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        quote = value[0]
        if quote in STRING_QUOTES:
            escaped = None
            length = len(value)
            end = length - 1
            for index in range(1, length):
                character = value[index]
                if escaped is None:
                    escaped = False
                if character == quote and not escaped:
                    if index == end:
                        return MatchType.FINAL_MATCH
                    else:
                        return MatchType.NONE
                escaped = (character == STRING_ESCAPE)
            return MatchType.MATCH
        return MatchType.NONE


INTEGER_PATTERN = re.compile('^[0-9]+$')


class IntegerLiteralTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        # TODO: Support alternate integer syntaxes
        if INTEGER_PATTERN.match(value) is not None:
            return MatchType.MATCH
        return MatchType.NONE


class UnmatchingTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        return MatchType.NONE


class CharacterTokenMatcher(TokenMatcher):

    def match(self, value: str) -> MatchType:
        if len(value) == 1:
            return MatchType.FINAL_MATCH
        return MatchType.NONE


def _literal(value) -> LiteralTokenMatcher:
    return LiteralTokenMatcher(value)


# TODO: Add matchers for remaining token types
class TokenType(Enum):
    # Custom matching types
    # DNUMBER   "floating-point number"
    # NAME_FULLY_QUALIFIED "fully qualified name"
    # NAME_RELATIVE "namespace-relative name"
    # NAME_QUALIFIED "namespaced name"
    # INLINE_HTML
    # ENCAPSED_AND_WHITESPACE  "string content"
    # CONSTANT_ENCAPSED_STRING "quoted string"
    # STRING_VARNAME "variable name"
    # NUM_STRING "number"
    # COMMENT         "comment"
    # DOC_COMMENT     "doc comment"
    # OPEN_TAG        "open tag"
    # WHITESPACE      "whitespace"
    # START_HEREDOC   "heredoc start"
    # END_HEREDOC     "heredoc end"
    OPEN_TAG = OpenTagTokenMatcher(),
    WHITESPACE = WhitespaceTokenMatcher(),
    DOC_COMMENT = DocCommentTokenMatcher(),
    COMMENT = CommentTokenMatcher(),
    VARIABLE = VariableTokenMatcher(),
    CONSTANT_ENCAPSED_STRING = StringLiteralTokenMatcher(),
    LNUMBER = IntegerLiteralTokenMatcher(),

    # Literal token types
    INCLUDE_ONCE = _literal('include_once'),
    INCLUDE = _literal('include'),
    EVAL = _literal('eval'),
    REQUIRE_ONCE = _literal('require_once'),
    REQUIRE = _literal('require'),
    LOGICAL_OR = _literal('or'),
    LOGICAL_XOR = _literal('xor'),
    LOGICAL_AND = _literal('and'),
    PRINT = _literal('print'),
    YIELD = _literal('yield'),
    YIELD_FROM = _literal('yield from'),
    INSTANCEOF = _literal('instanceof'),
    NEW = _literal('new'),
    CLONE = _literal('clone'),
    EXIT = _literal('exit'),
    IF = _literal('if'),
    ELSEIF = _literal('elseif'),
    ELSE = _literal('else'),
    ENDIF = _literal('endif'),
    ECHO = _literal('echo'),
    DO = _literal('do'),
    WHILE = _literal('while'),
    ENDWHILE = _literal('endwhile'),
    FOR = _literal('for'),
    ENDFOR = _literal('endfor'),
    FOREACH = _literal('foreach'),
    ENDFOREACH = _literal('endforeach'),
    DECLARE = _literal('declare'),
    ENDDECLARE = _literal('enddeclare'),
    AS = _literal('as'),
    SWITCH = _literal('switch'),
    ENDSWITCH = _literal('endswitch'),
    CASE = _literal('case'),
    DEFAULT = _literal('default'),
    MATCH = _literal('match'),
    BREAK = _literal('break'),
    CONTINUE = _literal('continue'),
    GOTO = _literal('goto'),
    FUNCTION = _literal('function'),
    FN = _literal('fn'),
    CONST = _literal('const'),
    RETURN = _literal('return'),
    TRY = _literal('try'),
    CATCH = _literal('catch'),
    FINALLY = _literal('finally'),
    THROW = _literal('throw'),
    USE = _literal('use'),
    INSTEADOF = _literal('insteadof'),
    GLOBAL = _literal('global'),
    STATIC = _literal('static'),
    ABSTRACT = _literal('abstract'),
    FINAL = _literal('final'),
    PRIVATE = _literal('private'),
    PROTECTED = _literal('protected'),
    PUBLIC = _literal('public'),
    READONLY = _literal('readonly'),
    VAR = _literal('var'),
    UNSET = _literal('unset'),
    ISSET = _literal('isset'),
    EMPTY = _literal('empty'),
    HALT_COMPILER = _literal('__halt_compiler'),
    CLASS = _literal('class'),
    TRAIT = _literal('trait'),
    INTERFACE = _literal('interface'),
    ENUM = _literal('enum'),
    EXTENDS = _literal('extends'),
    IMPLEMENTS = _literal('implements'),
    NAMESPACE = _literal('namespace'),
    LIST = _literal('list'),
    ARRAY = _literal('array'),
    CALLABLE = _literal('callable'),
    LINE = _literal('__LINE__'),
    FILE = _literal('__FILE__'),
    DIR = _literal('__DIR__'),
    CLASS_C = _literal('__CLASS__'),
    TRAIT_C = _literal('__TRAIT__'),
    METHOD_C = _literal('__METHOD__'),
    FUNC_C = _literal('__FUNCTION__'),
    NS_C = _literal('__NAMESPACE__'),
    PLUS_EQUAL = _literal('+='),
    MINUS_EQUAL = _literal('-='),
    MUL_EQUAL = _literal('*='),
    DIV_EQUAL = _literal('/='),
    CONCAT_EQUAL = _literal('.='),
    MOD_EQUAL = _literal('%='),
    AND_EQUAL = _literal('&='),
    OR_EQUAL = _literal('|='),
    XOR_EQUAL = _literal('^='),
    SL_EQUAL = _literal('<<='),
    SR_EQUAL = _literal('>>='),
    COALESCE_EQUAL = _literal('??='),
    BOOLEAN_OR = _literal('||'),
    BOOLEAN_AND = _literal('&&'),
    IS_EQUAL = _literal('=='),
    IS_NOT_EQUAL = _literal('!='),
    IS_IDENTICAL = _literal('==='),
    IS_NOT_IDENTICAL = _literal('!=='),
    IS_SMALLER_OR_EQUAL = _literal('<='),
    IS_GREATER_OR_EQUAL = _literal('>='),
    SPACESHIP = _literal('<=>'),
    SL = _literal('<<'),
    SR = _literal('>>'),
    INC = _literal('++'),
    DEC = _literal('--'),
    INT_CAST = _literal('(int)'),
    DOUBLE_CAST = _literal('(double)'),
    STRING_CAST = _literal('(string)'),
    ARRAY_CAST = _literal('(array)'),
    OBJECT_CAST = _literal('(object)'),
    BOOL_CAST = _literal('(bool)'),
    UNSET_CAST = _literal('(unset)'),
    OBJECT_OPERATOR = _literal('->'),
    NULLSAFE_OBJECT_OPERATOR = _literal('?->'),
    DOUBLE_ARROW = _literal('=>'),
    DOLLAR_OPEN_CURLY_BRACES = _literal('${'),
    CURLY_OPEN = _literal('{$'),
    PAAMAYIM_NEKUDOTAYIM = _literal('::'),
    NS_SEPARATOR = _literal('\\'),
    ELLIPSIS = _literal('...'),
    COALESCE = _literal('??'),
    POW = _literal('**'),
    POW_EQUAL = _literal('**='),
    ATTRIBUTE = _literal('#['),
    OPEN_TAG_WITH_ECHO = _literal('<?='),
    CLOSE_TAG = _literal('?>'),

    STRING = IdentifierTokenMatcher(),
    CHARACTER = CharacterTokenMatcher(),

    def __init__(self, matcher: TokenMatcher):
        self.matcher = matcher

    def match(self, value: str) -> MatchType:
        return self.matcher.match(value)


class CharacterType(str, Enum):
    EQUALS = '=',
    SEMICOLON = ';',
    OPEN_PARENTHESIS = '(',
    CLOSE_PARENTHESIS = ')',
    COMMA = ',',
    OPEN_BRACE = '{',
    CLOSE_BRACE = '}'


class Token:

    def __init__(self, type: TokenType, value: str):
        self.type = type
        self.value = value

    def is_character(
                self,
                type: Optional[Union[CharacterType, Set[CharacterType]]] = None
            ) -> bool:
        return self.type is TokenType.CHARACTER \
            and (
                type is None
                or (isinstance(type, CharacterType) and self.value == type)
                or self.value in type
            )

    def is_semicolon(self) -> bool:
        return self.is_character(CharacterType.SEMICOLON)


class Lexer:

    def __init__(self, stream: IO, chunk_size: int = 4096):
        self.chunks = deque()
        self.chunk_size = chunk_size
        self.chunk_offset = 0
        self.read = 0
        self.stream = stream
        self.offset = 0
        self.position = 0

    def _read_chunk(self) -> bool:
        chunk = self.stream.read(self.chunk_size)
        length = len(chunk)
        if length == 0:
            return False
        self.read += length
        self.chunks.append(chunk)
        return True

    def step(self) -> bool:
        self.position += 1
        if self.position > self.read:
            if not self._read_chunk():
                return False
        return True

    def get_current(self) -> str:
        components = []
        remaining = self.position - self.offset
        remaining_offset = self.offset
        for chunk in self.chunks:
            chunk_length = len(chunk)
            if chunk_length <= remaining_offset:
                remaining_offset -= chunk_length
                continue
            chunk = chunk[remaining_offset:remaining_offset + remaining]
            components.append(chunk)
            chunk_length = len(chunk)
            if chunk_length >= remaining:
                break
            remaining -= chunk_length
        return ''.join(components)

    def step_backwards(self) -> None:
        self.position -= 1

    def reset(self) -> None:
        self.position = self.offset

    def consume_token(self, token_type: TokenType) -> Token:
        value = self.get_current()
        self.offset = self.position
        return Token(token_type, value)

    def get_next_token(self) -> Optional[Token]:
        while self.step():
            position = self.position
            for type in TokenType:
                current = self.get_current()
                potential = False
                while True:
                    match_type = type.match(current)
                    if match_type == MatchType.FINAL_MATCH:
                        return self.consume_token(type)
                    elif match_type == MatchType.MATCH:
                        potential = True
                    elif match_type == MatchType.NONE:
                        if potential:
                            self.step_backwards()
                            return self.consume_token(type)
                        self.position = position
                        break
                    if not self.step():
                        self.position = position
                        break
                    current = self.get_current()
        current = self.get_current()
        if current is not None and len(current) > 0:
            raise LexingException(
                    f'Input does not match any known token: "{current}"'
                )
        return None


def lex(stream: IO) -> Generator[Token, None, None]:
    lexer = Lexer(stream)
    while (token := lexer.get_next_token()) is not None:
        yield token
