import io
import re
import tokenize
from functools import lru_cache
from pathlib import Path

DECISION_KEYWORDS = {'if', 'elif', 'while', 'and', 'or', 'not', 'is', 'assert', 'True', 'False'}
DECISION_OPS = {'<', '>', '<=', '>=', '==', '!='}
_MAIN_RE = re.compile(r'^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]\s*:')


@lru_cache(maxsize=None)
def _main_block_start(filename):
    try:
        for i, line in enumerate(Path(filename).read_text().splitlines()):
            if _MAIN_RE.match(line):
                return i
    except OSError:
        pass
    return None


@lru_cache(maxsize=None)
def _decision_lines(filename):
    decision = set()
    try:
        source = Path(filename).read_text()
    except OSError:
        return frozenset()

    try:
        tokens = list(tokenize.tokenize(io.BytesIO(source.encode()).readline))
    except (tokenize.TokenizeError, IndentationError, SyntaxError):
        return frozenset()

    for tok in tokens:
        if tok.type == tokenize.NAME and tok.string in DECISION_KEYWORDS:
            decision.add(tok.start[0] - 1)
        elif tok.type == tokenize.OP and tok.string in DECISION_OPS:
            decision.add(tok.start[0] - 1)
    return frozenset(decision)


def pre_mutation(context):
    main_start = _main_block_start(context.filename)
    if main_start is not None and context.current_line_index >= main_start:
        context.skip = True
        return

    if context.current_line_index not in _decision_lines(context.filename):
        context.skip = True
