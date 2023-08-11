import regex
import signal

from ..intel.signatures import CommonString, Signature, SignatureSet
from ..logging import log

regex.DEFAULT_VERSION = regex.VERSION1


DEFAULT_TIMEOUT = 1  # Seconds


class TimeoutException(Exception):
    pass


class MatchResult:

    def __init__(self, matches: list):
        self.matches = matches

    def matches(self) -> bool:
        return len(self.matches) > 0


class Matcher:

    def __init__(
                self,
                signature_set: SignatureSet,
                timeout: int = DEFAULT_TIMEOUT,
                match_all: bool = False
            ):
        self.signature_set = signature_set
        self.timeout = timeout
        self.match_all = match_all


class MatcherContext:
    pass


class RegexMatcherContext(MatcherContext):

    def __init__(self, matcher):
        self.matcher = matcher
        self.common_string_states = self._initialize_common_string_states()
        self.matches = {}
        self.timeouts = set()

    def _initialize_common_string_states(self) -> list:
        states = []
        for _common_string in self.matcher.common_strings:
            states.append(False)
        return states

    def _check_common_strings(self, chunk: bytes) -> list:
        common_string_counts = {}
        for index, common_string in enumerate(self.matcher.common_strings):
            if not self.common_string_states[index]:
                match = common_string.pattern.search(chunk)
                if match is not None:
                    self.common_string_states[index] = True
            if self.common_string_states[index]:
                for identifier in common_string.common_string.signature_ids:
                    if identifier in self.matches:
                        continue
                    if identifier in common_string_counts:
                        common_string_counts[identifier] += 1
                    else:
                        common_string_counts[identifier] = 1
        possible_signatures = []
        for identifier, count in common_string_counts.items():
            signature = self.matcher.signatures[identifier]
            if count == signature.signature.get_common_string_count():
                possible_signatures.append(signature)
        return possible_signatures

    def _match_signature(self, signature: Signature, chunk: str) -> bool:
        if not signature.is_valid():
            return False
        try:
            signal.alarm(self.matcher.timeout)
            match = signature.get_pattern().search(chunk)
            signal.alarm(0)  # Clear the alarm
            if match is not None:
                self.matches[signature.signature.identifier] = match.group(0)
                return True
        except TimeoutException:
            self.timeouts.add(signature.signature.identifier)
        return False

    def process_chunk(self, chunk: bytes) -> bool:
        chunk = chunk.decode('utf-8', 'ignore')
        possible_signatures = self._check_common_strings(chunk)
        for signature in self.matcher.signatures_without_common_strings:
            if self._match_signature(signature, chunk) and \
                    not self.matcher.match_all:
                return True
        for signature in possible_signatures:
            if self._match_signature(signature, chunk) and \
                    not self.matcher.match_all:
                return True
        return False

    def __enter__(self):
        def handle_timeout(signum, frame):
            raise TimeoutException()

        self._previous_alarm_handler = signal.signal(
                signal.SIGALRM,
                handle_timeout
            )
        if self._previous_alarm_handler is None:
            self._previous_alarm_handler = signal.SIG_DFL
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        signal.signal(signal.SIGALRM, self._previous_alarm_handler)
        pass


class RegexCommonString:

    def __init__(self, common_string: CommonString):
        self.common_string = common_string
        self.pattern = regex.compile(common_string.string)


class RegexSignature:

    def __init__(self, signature: Signature):
        self.signature = signature
        if not signature.has_common_strings():
            self.compile()

    def is_valid(self) -> bool:
        return self.get_pattern() is not None

    def compile(self) -> None:
        try:
            rule = self.signature.rule
            self.pattern = regex.compile(rule)
        except BaseException as error:
            log.error('Regex compilation for signature ' +
                      str(self.signature.identifier) +
                      ' failed: ' +
                      str(error) +
                      ', pattern: ' +
                      repr(rule))
            self.pattern = None
            # raise error #TODO: How should this be handled

    def get_pattern(self) -> regex.Pattern:
        # Signature patterns are compiled lazily as they are only needed if
        # common strings are matched and compiling all takes several seconds
        if not hasattr(self, 'pattern'):
            self.compile()
        return self.pattern


class RegexMatcher(Matcher):

    def __init__(
                self,
                signature_set: SignatureSet,
                timeout: int = DEFAULT_TIMEOUT,
                match_all: bool = False
            ):
        super().__init__(signature_set, timeout, match_all)
        self._compile_regexes()
        self.signatures_without_common_strings = \
            self._extract_signatures_without_common_strings()

    def _extract_signatures_without_common_strings(self) -> list:
        signatures = []
        for signature in self.signatures.values():
            if not signature.signature.has_common_strings():
                signatures.append(signature)
        return signatures

    def _compile_common_strings(self) -> None:
        self.common_strings = [
                RegexCommonString(common_string)
                for common_string in self.signature_set.common_strings
            ]

    def _compile_signatures(self) -> None:
        self.signatures = {}
        for identifier, signature in self.signature_set.signatures.items():
            self.signatures[identifier] = RegexSignature(signature)

    def _compile_regexes(self) -> None:
        self._compile_common_strings()
        self._compile_signatures()

    def create_context(self) -> RegexMatcherContext:
        return RegexMatcherContext(self)
