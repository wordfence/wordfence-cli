from typing import Optional

from ...intel.signatures import CommonString, Signature, SignatureSet
from ...logging import log
from ...util import vectorscan

from .matching import MatchEngineOptions, Matcher, BaseMatcherContext, \
        MatchWorkspace


if not vectorscan.AVAILABLE:
    raise RuntimeError('Vectorscan is not available')


from ...util.vectorscan import VectorscanDatabase, VectorscanScanner, \
    VectorscanMatch, VectorscanFlags, vectorscan_compile


class VectorscanMatcherContext(BaseMatcherContext):

    def _match_callback(self, match: VectorscanMatch) -> bool:
        self._record_match(
                identifier=match.identifier,
                matched=''
            )
        return False if self.matcher.match_all else True

    def process_chunk(
                self,
                chunk: bytes,
                start: bool = False,
                workspace: Optional[MatchWorkspace] = None
            ) -> bool:
        log.debug('Processing chunk')
        self.matcher.scanner.scan(chunk, self._match_callback, context=chunk)
        log.debug('Processed chunk')
        return False


class VectorscanMatcher(Matcher):

    def __init__(
                self,
                signature_set: SignatureSet,
                match_all: bool = False
            ):
        super().__init__(
                signature_set=signature_set,
                match_all=match_all
            )
        self.signature_set = signature_set
        self.match_all = match_all
        self.database = None
        self.scanner = None

    def _prepare(self) -> None:
        log.debug('Preparing...')
        patterns = {
                signature.identifier: signature.rule
                for signature in self.signature_set.signatures.values()
            }
        #patterns_limited = {}
        #for key, value in patterns.items():
        #    if b'\x00' in value.encode('utf-8'):
        #        print('Null byte in pattern')
        #    patterns_limited[key] = value
        #    last = (key, value)
        #    if (len(patterns_limited) >= 100):
        #        break
        #print("Last: " + repr(last))
        #import json
        #print(json.dumps(last[1]))
        #patterns = patterns_limited
        ##patterns = {135: last[1]}
        #print(repr(patterns))
        pattern_count = len(patterns)
        log.debug(f'Compiling {pattern_count} pattern(s)...')
        flags = (
                VectorscanFlags.CASELESS |
                VectorscanFlags.SINGLEMATCH |
                VectorscanFlags.ALLOWEMPTY
            )
        self.database = vectorscan_compile(patterns, flags=flags)
        log.debug('Compiled')
        self.scanner = VectorscanScanner(self.database)
        log.debug('Prepared')

    def create_context(self) -> VectorscanMatcherContext:
        return VectorscanMatcherContext(
                self
            )


def create_matcher(options: MatchEngineOptions):
    return VectorscanMatcher(
            options.signature_set,
            match_all=options.match_all
        )
