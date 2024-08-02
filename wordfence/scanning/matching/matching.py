from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from importlib import import_module
from contextlib import AbstractContextManager

from ...intel.signatures import SignatureSet
from ...util.caching import Cacheable
from ...util.pcre import PcreOptions, PCRE_DEFAULT_OPTIONS

DEFAULT_TIMEOUT = 1  # Seconds


class TimeoutException(Exception):
    pass


class MatchResult:

    def __init__(self, matches: list):
        self.matches = matches

    def matches(self) -> bool:
        return len(self.matches) > 0


class MatchWorkspace(AbstractContextManager):

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return self


class MatcherContext(AbstractContextManager):

    def __init__(self):
        self.matches = {}
        self.timeouts = set()

    def process_chunk(
                self,
                chunk: bytes,
                start: bool = False,
                workspace: Optional[MatchWorkspace] = None
            ):
        raise NotImplementedError()

    def finalize_content(self) -> None:
        pass

    def _record_match(self, identifier: str, matched: Optional[bytes]) -> None:
        self.matches[identifier] = matched

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        pass


class Matcher:

    def __init__(
                self,
                signature_set: SignatureSet,
                timeout: int = DEFAULT_TIMEOUT,
                match_all: bool = False,
                lazy: bool = False
            ):
        self.signature_set = signature_set
        self.timeout = timeout
        self.match_all = match_all
        self.prepared = False
        self.prepared_thread = False
        if not lazy:
            self.prepare()

    def get_cacheable(self) -> Optional[Cacheable]:
        return None

    def prepare(self, thread: bool = False) -> None:
        if not self.prepared:
            self._prepare()
            self.prepared = True
        if thread:
            self.prepare_thread()

    def _prepare(self) -> None:
        pass

    def prepare_thread(self) -> None:
        if self.prepared_thread:
            return
        self._prepare_thread()
        self.prepared_thread = True

    def _prepare_thread(self) -> None:
        pass

    def create_workspace(self) -> Optional[MatchWorkspace]:
        return MatchWorkspace()

    def create_context(self) -> MatcherContext:
        raise NotImplementedError()


class BaseMatcherContext(MatcherContext):

    def __init__(self, matcher: Matcher):
        self.matcher = matcher
        super().__init__()


@dataclass
class MatchEngineCompilerOptions:
    generic: bool = False


@dataclass
class MatchEngineOptions:
    signature_set: SignatureSet
    match_all: bool = False
    lazy: bool = False
    pcre_options: PcreOptions = PCRE_DEFAULT_OPTIONS
    database_source: Optional[bytes] = None


class Compiler:

    def compile_serializable(self, signatures: SignatureSet) -> bytes:
        raise NotImplementedError()


class MatchEngine(Enum):
    PCRE = 'pcre'
    VECTORSCAN = 'vectorscan'

    def __init__(self, option: str, module: Optional[str] = None):
        self.option = option
        self.module = option if module is None else module
        self._loaded_module = None

    @classmethod
    def get_options(cls) -> List:
        return [engine.option for engine in cls]

    @classmethod
    def for_option(cls, option: str):
        for engine in cls:
            if engine.option == option:
                return engine
        raise ValueError(f'Unrecognized engine option: {option}')

    @classmethod
    def get_default(cls):
        return cls.PCRE

    @classmethod
    def get_default_option(cls):
        return cls.get_default().option

    def _load_module(self):
        return import_module(
                f'.{self.module}',
                'wordfence.scanning.matching'
            )

    def _get_loaded_module(self):
        if self._loaded_module is None:
            self._loaded_module = self._load_module()
        return self._loaded_module

    def get_compiler(
                self,
                options: MatchEngineCompilerOptions
            ) -> Optional[Compiler]:
        module = self._get_loaded_module()
        return module.create_compiler(options)

    def supports_pre_compilation(self) -> bool:
        compiler = self.get_compiler(MatchEngineCompilerOptions())
        return compiler is not None

    def validate_database_source(self, source: Optional[bytes]) -> bool:
        if source is None:
            return True
        module = self._get_loaded_module()
        return module.validate_database_source(source)

    def create_matcher(self, options: MatchEngineOptions) -> Matcher:
        module = self._get_loaded_module()
        return module.create_matcher(options)
