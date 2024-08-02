import re

from collections import deque
from enum import Enum, auto
from typing import Generator, BinaryIO, Optional, Union, Set

from wordfence.util.encoding import bytes_to_str


class LexingException(Exception):
    pass


class MatchType(Enum):
    NONE = auto(),
    MATCH = auto(),
    FINAL_MATCH = auto(),
    PARTIAL_MATCH = auto()


class TokenMatcher:

    def match(self, value: bytes) -> MatchType:
        return MatchType.NONE

    # TODO: Find a more efficient algorithm for string end matching
    def match_at_end(self, value: bytes) -> MatchType:
        match_length = 1
        total_length = len(value)
        while match_length <= total_length:
            partial = value[-match_length:]
            match_type = self.match(partial)
            if match_type != MatchType.NONE:
                return match_type
            match_length += 1
        return MatchType.NONE


def match_literal(literal: bytes, value: bytes) -> MatchType:
    if value == literal:
        return MatchType.FINAL_MATCH
    elif len(value) < len(literal) and literal.find(value) == 0:
        return MatchType.PARTIAL_MATCH
    else:
        return MatchType.NONE


class LiteralTokenMatcher(TokenMatcher):

    def __init__(self, value: bytes):
        self.value = value

    def match(self, value: bytes) -> MatchType:
        return match_literal(self.value, value)


class WhitespaceTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        # TODO: Does this match PHP's definition of whitespace?
        if value.isspace():
            return MatchType.MATCH
        return MatchType.NONE


class OpenTagTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        # TODO: Handle tag variations
        return match_literal(b'<?php', value)


DOC_COMMENT_START = b'/*'
DOC_COMMENT_END = b'*/'
COMMENT_START = b'//'
ALTERNATE_COMMENT_START = b'#'
COMMENT_END = b'\n'
CLOSING_TAG = b'?>'
POSSIBLE_COMMENT_STARTS = {
        COMMENT_START,
        ALTERNATE_COMMENT_START
    }
POSSIBLE_COMMENT_ENDS = {
        COMMENT_END,
        CLOSING_TAG
    }


class EnclosedTokenMatcher(TokenMatcher):

    def __init__(self, start: bytes, end: bytes):
        self.start = start
        self.end = end
        self.end_length = len(end)

    def match(self, value: bytes) -> MatchType:
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


class CommentTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        for start in POSSIBLE_COMMENT_STARTS:
            if value.find(start) == 0:
                for end in POSSIBLE_COMMENT_ENDS:
                    if value.find(end) != -1:
                        return MatchType.NONE
                return MatchType.MATCH
            elif start.find(value) == 0:
                return MatchType.PARTIAL_MATCH
        return MatchType.NONE


VARIABLE_PREFIX = b'$'
IDENTIFIER_PATTERN = re.compile(br'^[a-zA-Z_\x80-\xff][a-zA-Z0-9_\x80-\xff]*$')


class VariableTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        if value[0:1] == VARIABLE_PREFIX:
            if IDENTIFIER_PATTERN.fullmatch(value[1:]) is not None:
                return MatchType.MATCH
            if len(value) == 1:
                return MatchType.PARTIAL_MATCH
        return MatchType.NONE


class IdentifierTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        if IDENTIFIER_PATTERN.fullmatch(value):
            return MatchType.MATCH
        return MatchType.NONE


STRING_QUOTES = {
    b'"',
    b"'"
}
STRING_ESCAPE = b"\\"


class StringLiteralTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        quote = value[0:1]
        if quote in STRING_QUOTES:
            escaped = None
            length = len(value)
            end = length - 1
            for index in range(1, length):
                character = value[index:index+1]
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


INTEGER_PATTERN = re.compile(b'^[0-9]+$')


class IntegerLiteralTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        # TODO: Support alternate integer syntaxes
        if INTEGER_PATTERN.match(value) is not None:
            return MatchType.MATCH
        return MatchType.NONE


class UnmatchingTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
        return MatchType.NONE


class CharacterTokenMatcher(TokenMatcher):

    def match(self, value: bytes) -> MatchType:
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
    INCLUDE_ONCE = _literal(b'include_once'),
    INCLUDE = _literal(b'include'),
    EVAL = _literal(b'eval'),
    REQUIRE_ONCE = _literal(b'require_once'),
    REQUIRE = _literal(b'require'),
    LOGICAL_OR = _literal(b'or'),
    LOGICAL_XOR = _literal(b'xor'),
    LOGICAL_AND = _literal(b'and'),
    PRINT = _literal(b'print'),
    YIELD = _literal(b'yield'),
    YIELD_FROM = _literal(b'yield from'),
    INSTANCEOF = _literal(b'instanceof'),
    NEW = _literal(b'new'),
    CLONE = _literal(b'clone'),
    EXIT = _literal(b'exit'),
    IF = _literal(b'if'),
    ELSEIF = _literal(b'elseif'),
    ELSE = _literal(b'else'),
    ENDIF = _literal(b'endif'),
    ECHO = _literal(b'echo'),
    DO = _literal(b'do'),
    WHILE = _literal(b'while'),
    ENDWHILE = _literal(b'endwhile'),
    FOREACH = _literal(b'foreach'),
    FOR = _literal(b'for'),
    ENDFOR = _literal(b'endfor'),
    ENDFOREACH = _literal(b'endforeach'),
    DECLARE = _literal(b'declare'),
    ENDDECLARE = _literal(b'enddeclare'),
    AS = _literal(b'as'),
    SWITCH = _literal(b'switch'),
    ENDSWITCH = _literal(b'endswitch'),
    CASE = _literal(b'case'),
    DEFAULT = _literal(b'default'),
    MATCH = _literal(b'match'),
    BREAK = _literal(b'break'),
    CONTINUE = _literal(b'continue'),
    GOTO = _literal(b'goto'),
    FUNCTION = _literal(b'function'),
    FN = _literal(b'fn'),
    CONST = _literal(b'const'),
    RETURN = _literal(b'return'),
    TRY = _literal(b'try'),
    CATCH = _literal(b'catch'),
    FINALLY = _literal(b'finally'),
    THROW = _literal(b'throw'),
    USE = _literal(b'use'),
    INSTEADOF = _literal(b'insteadof'),
    GLOBAL = _literal(b'global'),
    STATIC = _literal(b'static'),
    ABSTRACT = _literal(b'abstract'),
    FINAL = _literal(b'final'),
    PRIVATE = _literal(b'private'),
    PROTECTED = _literal(b'protected'),
    PUBLIC = _literal(b'public'),
    READONLY = _literal(b'readonly'),
    VAR = _literal(b'var'),
    UNSET = _literal(b'unset'),
    ISSET = _literal(b'isset'),
    EMPTY = _literal(b'empty'),
    HALT_COMPILER = _literal(b'__halt_compiler'),
    CLASS = _literal(b'class'),
    TRAIT = _literal(b'trait'),
    INTERFACE = _literal(b'interface'),
    ENUM = _literal(b'enum'),
    EXTENDS = _literal(b'extends'),
    IMPLEMENTS = _literal(b'implements'),
    NAMESPACE = _literal(b'namespace'),
    LIST = _literal(b'list'),
    ARRAY = _literal(b'array'),
    CALLABLE = _literal(b'callable'),
    LINE = _literal(b'__LINE__'),
    FILE = _literal(b'__FILE__'),
    DIR = _literal(b'__DIR__'),
    CLASS_C = _literal(b'__CLASS__'),
    TRAIT_C = _literal(b'__TRAIT__'),
    METHOD_C = _literal(b'__METHOD__'),
    FUNC_C = _literal(b'__FUNCTION__'),
    NS_C = _literal(b'__NAMESPACE__'),
    PLUS_EQUAL = _literal(b'+='),
    MINUS_EQUAL = _literal(b'-='),
    MUL_EQUAL = _literal(b'*='),
    DIV_EQUAL = _literal(b'/='),
    CONCAT_EQUAL = _literal(b'.='),
    MOD_EQUAL = _literal(b'%='),
    AND_EQUAL = _literal(b'&='),
    OR_EQUAL = _literal(b'|='),
    XOR_EQUAL = _literal(b'^='),
    SL_EQUAL = _literal(b'<<='),
    SR_EQUAL = _literal(b'>>='),
    COALESCE_EQUAL = _literal(b'??='),
    BOOLEAN_OR = _literal(b'||'),
    BOOLEAN_AND = _literal(b'&&'),
    IS_IDENTICAL = _literal(b'==='),
    IS_NOT_IDENTICAL = _literal(b'!=='),
    IS_SMALLER_OR_EQUAL = _literal(b'<='),
    IS_GREATER_OR_EQUAL = _literal(b'>='),
    SPACESHIP = _literal(b'<=>'),
    IS_EQUAL = _literal(b'=='),
    IS_NOT_EQUAL = _literal(b'!='),
    SL = _literal(b'<<'),
    SR = _literal(b'>>'),
    INC = _literal(b'++'),
    DEC = _literal(b'--'),
    INT_CAST = _literal(b'(int)'),
    DOUBLE_CAST = _literal(b'(double)'),
    STRING_CAST = _literal(b'(string)'),
    ARRAY_CAST = _literal(b'(array)'),
    OBJECT_CAST = _literal(b'(object)'),
    BOOL_CAST = _literal(b'(bool)'),
    UNSET_CAST = _literal(b'(unset)'),
    OBJECT_OPERATOR = _literal(b'->'),
    NULLSAFE_OBJECT_OPERATOR = _literal(b'?->'),
    DOUBLE_ARROW = _literal(b'=>'),
    DOLLAR_OPEN_CURLY_BRACES = _literal(b'${'),
    CURLY_OPEN = _literal(b'{$'),
    PAAMAYIM_NEKUDOTAYIM = _literal(b'::'),
    NS_SEPARATOR = _literal(b'\\'),
    ELLIPSIS = _literal(b'...'),
    COALESCE = _literal(b'??'),
    POW = _literal(b'**'),
    POW_EQUAL = _literal(b'**='),
    ATTRIBUTE = _literal(b'#['),
    OPEN_TAG_WITH_ECHO = _literal(b'<?='),
    CLOSE_TAG = _literal(CLOSING_TAG),

    STRING = IdentifierTokenMatcher(),
    CHARACTER = CharacterTokenMatcher(),
    INLINE_HTML = UnmatchingTokenMatcher(),

    def __init__(self, matcher: TokenMatcher):
        self.matcher = matcher

    def match(self, value: bytes) -> MatchType:
        return self.matcher.match(value)

    def match_at_end(self, value: bytes) -> MatchType:
        return self.matcher.match_at_end(value)


class CharacterType(bytes, Enum):
    EQUALS = b'=',
    SEMICOLON = b';',
    OPEN_PARENTHESIS = b'(',
    CLOSE_PARENTHESIS = b')',
    COMMA = b',',
    OPEN_BRACE = b'{',
    CLOSE_BRACE = b'}'


class Token:

    def __init__(self, type: TokenType, value: bytes):
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

    def is_opening_parenthesis(self) -> bool:
        return self.is_character(CharacterType.OPEN_PARENTHESIS)

    def is_closing_parenthesis(self) -> bool:
        return self.is_character(CharacterType.CLOSE_PARENTHESIS)

    def is_comma(self) -> bool:
        return self.is_character(CharacterType.COMMA)

    def __repr__(self) -> str:
        return self.type.name + ' (' + bytes_to_str(self.value) + ')'

    def __str__(self) -> str:
        return repr(self)


class Lexer:

    def __init__(self, stream: BinaryIO, chunk_size: int = 4096):
        self.chunks = deque()
        self.chunk_size = chunk_size
        self.chunk_offset = 0
        self.read = 0
        self.stream = stream
        self.offset = 0
        self.position = 0
        self.inside_tag = False

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

    def get_current(self) -> bytes:
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
        return b''.join(components)

    def step_backwards(self) -> None:
        self.position -= 1

    def reset(self) -> None:
        self.position = self.offset

    def consume_token(self, token_type: TokenType) -> Token:
        value = self.get_current()
        self.offset = self.position
        return Token(token_type, value)

    def extract_php_token(self, types=TokenType) -> Optional[Token]:
        while self.step():
            position = self.position
            for type in types:
                current = self.get_current()
                potential = False
                while True:
                    match_type = type.match(current)
                    if match_type == MatchType.FINAL_MATCH:
                        position = self.position
                        if TokenType.STRING.match(current) == MatchType.MATCH:
                            string = self.extract_php_token({TokenType.STRING})
                            if string is not None:
                                return string
                        self.position = position
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
                        if potential:
                            return self.consume_token(type)
                        self.position = position
                        break
                    current = self.get_current()
        current = self.get_current()
        if current is not None and len(current) > 0 and types is TokenType:
            raise LexingException(
                    f'Input does not match any known token: "{current}"'
                )
        return None

    def extract_inline_html_or_open_tag(self) -> Optional[Token]:
        partial_start = None
        while self.step():
            current = self.get_current()
            match_type = TokenType.OPEN_TAG.match_at_end(current)
            if match_type == MatchType.PARTIAL_MATCH and partial_start is None:
                partial_start = self.position
            elif match_type == MatchType.FINAL_MATCH:
                if partial_start is None or partial_start > 0:
                    return self.consume_token(TokenType.OPEN_TAG)
                else:
                    self.offset = partial_start
                    return self.consume_token(TokenType.INLINE_HTML)
            else:
                partial_start = None
        current = self.get_current()
        if current is not None and len(current) > 0:
            return self.consume_token(TokenType.INLINE_HTML)
        return None

    def get_next_token(self) -> Optional[Token]:
        if self.inside_tag:
            token = self.extract_php_token()
            if token is not None and token.type == TokenType.CLOSE_TAG:
                self.inside_tag = False
        else:
            token = self.extract_inline_html_or_open_tag()
            if token is not None and token.type == TokenType.OPEN_TAG:
                self.inside_tag = True
        return token


def lex(stream: BinaryIO) -> Generator[Token, None, None]:
    lexer = Lexer(stream)
    while (token := lexer.get_next_token()) is not None:
        yield token
