from typing import Callable, Dict, List, NamedTuple, Set, Optional, Tuple, Union, Iterable
from enum import Enum
import regex
import json
import os
import pickle
import pickletools
from pyunormalize import NFC, NFD


SPEC_PATH = os.path.join(os.path.dirname(__file__), 'spec.json')


class ErrorTypeBase(Enum):
    def __new__(cls, *args):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, general_info: str):
        self.general_info = general_info

    @property
    def code(self) -> str:
        return self.name


class CurableErrorTypeBase(Enum):
    def __new__(cls, *args):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, general_info: str, disallowed_sequence_info: str):
        self.general_info = general_info
        self.disallowed_sequence_info = disallowed_sequence_info

    @property
    def code(self) -> str:
        return self.name


class DisallowedNameErrorType(ErrorTypeBase):
    """
    The name is disallowed and cannot be normalized.
    """

    # GENERIC ----------------

    EMPTY_NAME = "The name is empty"

    # NSM --------------------

    NSM_REPEATED = "Contains a repeated non-spacing mark"

    NSM_TOO_MANY = "Contains too many consecutive non-spacing marks"

    # CONFUSABLES ----------

    CONF_WHOLE = "Contains visually confusing characters that are disallowed"


class CurableErrorType(CurableErrorTypeBase):
    """
    The name is disallowed but a cure is available.
    """

    # GENERIC ----------------

    UNDERSCORE = "Contains an underscore in a disallowed position", \
                 "An underscore is only allowed at the start of a label"

    HYPHEN     = "Contains the sequence '--' in a disallowed position", \
                 "Hyphens are disallowed at the 2nd and 3rd positions of a label"

    EMPTY_LABEL = "Contains a disallowed empty label", \
                  "Empty labels are not allowed, e.g. abc..eth"

    # CM ---------------------

    CM_START   = "Contains a combining mark in a disallowed position at the start of the label", \
                 "A combining mark is disallowed at the start of a label"

    CM_EMOJI   = "Contains a combining mark in a disallowed position after an emoji", \
                 "A combining mark is disallowed after an emoji"

    # TOKENS -----------------

    DISALLOWED = "Contains a disallowed character", \
                 "This character is disallowed"

    INVISIBLE  = "Contains a disallowed invisible character", \
                 "This invisible character is disallowed"

    # FENCED ----------------

    FENCED_LEADING = "Contains a disallowed character at the start of a label", \
                     "This character is disallowed at the start of a label"

    FENCED_MULTI   = "Contains a disallowed consecutive sequence of characters", \
                     "Characters in this sequence cannot be placed next to each other"

    FENCED_TRAILING = "Contains a disallowed character at the end of a label", \
                      "This character is disallowed at the end of a label"

    # CONFUSABLES ----------

    CONF_MIXED = "Contains visually confusing characters from different scripts that are disallowed", \
                 "This character is disallowed because it is visually confusing with another character from a different script"


class NormalizationTransformationType(CurableErrorTypeBase):
    """
    The label is allowed but contains a sequence which has been automatically transformed into a normalized form.
    """

    IGNORED   = "Contains disallowed \"ignored\" characters that have been removed", \
                "This character is ignored during normalization and has been automatically removed"

    MAPPED    = "Contains a disallowed character that has been replaced by a normalized sequence", \
                "This character is disallowed and has been automatically replaced by a normalized sequence"

    FE0F      = "Contains a disallowed variant of an emoji which has been replaced by an equivalent normalized emoji", \
                "This emoji has been automatically fixed to remove an invisible character"

    NFC       = "Contains a disallowed sequence that is not \"NFC normalized\" which has been replaced by an equivalent normalized sequence", \
                "This sequence has been automatically normalized into NFC canonical form"


class DisallowedNameError(Exception):
    def __init__(self, type: DisallowedNameErrorType):
        super().__init__(type.general_info)
        self.type = type

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(code="{self.type.code}")'

    def __str__(self) -> str:
        return self.general_info

    @property
    def code(self) -> str:
        """
        The message code in uppercase string format.
        """
        return self.type.code

    @property
    def general_info(self) -> str:
        """
        Information about the entire name.
        """
        return self.type.general_info


class CurableError(DisallowedNameError):
    def __init__(self,
                 type: CurableErrorType,
                 index: int,
                 disallowed: str,
                 suggested: str):
        super().__init__(type)
        self.type = type
        self.index = index
        self.disallowed = disallowed
        self.suggested = suggested

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(code="{self.type.code}", index={self.index}, disallowed="{self.disallowed}", suggested="{self.suggested}")'

    @property
    def disallowed_sequence_info(self) -> str:
        """
        Information about the disallowed sequence.
        """
        return self.type.disallowed_sequence_info.format(
            disallowed=self.disallowed,
            suggested=self.suggested,
        )


class NormalizationTransformation(CurableError):
    def __init__(self,
                 type: NormalizationTransformationType,
                 index: int,
                 disallowed: str,
                 suggested: str):
        super().__init__(type, index, disallowed, suggested)
        self.type = type


TY_VALID = 'valid'
TY_MAPPED = 'mapped'
TY_IGNORED = 'ignored'
TY_DISALLOWED = 'disallowed'
TY_EMOJI = 'emoji'
TY_STOP = 'stop'
TY_NFC = 'nfc'


CP_STOP = 0x2E
CP_FE0F = 0xFE0F
CP_APOSTROPHE = 8217
CP_SLASH = 8260
CP_MIDDLE_DOT = 12539
CP_XI_SMALL = 0x3BE
CP_XI_CAPITAL = 0x39E


class TokenValid(NamedTuple):
    cps: List[int]
    type: str = TY_VALID


class TokenMapped(NamedTuple):
    cp: int
    cps: List[int]
    type: str = TY_MAPPED


class TokenIgnored(NamedTuple):
    cp: int
    type: str = TY_IGNORED


class TokenDisallowed(NamedTuple):
    cp: int
    type: str = TY_DISALLOWED


class TokenEmoji(NamedTuple):
    emoji: List[int]
    input: List[int]
    cps: List[int]
    type: str = TY_EMOJI


class TokenStop(NamedTuple):
    cp: int = CP_STOP
    type: str = TY_STOP


class TokenNFC(NamedTuple):
    input: List[int]
    cps: List[int]
    type: str = TY_NFC


Token = Union[
    TokenValid,
    TokenMapped,
    TokenIgnored,
    TokenDisallowed,
    TokenEmoji,
    TokenStop,
    TokenNFC,
]


class ENSProcessResult(NamedTuple):
    normalized: Optional[str]
    beautified: Optional[str]
    tokens: Optional[List[Token]]
    cured: Optional[str]
    cures: Optional[List[CurableError]]
    error: Optional[DisallowedNameError]
    transformations: Optional[List[NormalizationTransformation]]


def str2cps(text: str) -> List[int]:
    """
    Convert text to a list of integer codepoints.
    """
    return [ord(c) for c in text]


def cps2str(cps: List[int]) -> str:
    """
    Convert a list of integer codepoints to string.
    """
    return ''.join(chr(cp) for cp in cps)


def filter_fe0f(text: str) -> str:
    """
    Remove all FE0F from text.
    """
    return text.replace('\uFE0F', '')


def add_all_fe0f(emojis: List[str]):
    """
    Find all emoji sequence prefixes that can be followed by FE0F.
    Then, append FE0F to all prefixes that can but do not have it already.
    This emulates adraffy's trie building algorithm, which does not add FE0F nodes,
    but sets a "can be followed by FE0F" flag on the previous node.
    """
    cps_with_fe0f = set()
    for cps in emojis:
        for i in range(1, len(cps)):
            if cps[i] == '\uFE0F':
                # remember the entire prefix to simulate trie behavior
                cps_with_fe0f.add(cps[:i])

    emojis_out = []

    for cps_in in emojis:
        cps_out = ''
        # for all prefixes
        for i in range(len(cps_in)):
            cps_out += cps_in[i]
            # check if the prefix can be followed by FE0F
            if cps_in[:i+1] in cps_with_fe0f and (i == len(cps_in) - 1 or cps_in[i + 1] != '\uFE0F'):
                cps_out += '\uFE0F'
        emojis_out.append(cps_out)

    return emojis_out


def create_emoji_regex_pattern(emojis: List[str]) -> str:
    # add all optional fe0f so that we can match emojis with or without it
    emojis = add_all_fe0f(emojis)
    fe0f = regex.escape('\uFE0F')
    def make_emoji(emoji: str) -> str:
        # make FE0F optional
        return regex.escape(emoji).replace(fe0f, f'{fe0f}?')
    # sort to match the longest first
    return '|'.join(make_emoji(emoji) for emoji in sorted(emojis, key=len, reverse=True))


def create_emoji_fe0f_lookup(emojis: List[str]) -> Dict[str, str]:
    """
    Create a lookup table for recreating FE0F emojis from non-FE0F emojis.
    """
    return {filter_fe0f(emoji): emoji for emoji in emojis}


def compute_valid(groups: List[Dict]) -> Set[int]:
    valid = set()
    for g in groups:
        valid.update(g['V'])
    valid.update(map(ord, NFD(''.join(map(chr, valid)))))
    return valid


def read_groups(groups: List[Dict]) -> List[Dict]:
    return [
        {
            'name': g['name'],
            'P': set(g['primary']),
            'Q': set(g['secondary']),
            'V': set(g['primary'] + g['secondary']),
            'M': 'cm' not in g,
        }
        for g in groups
    ]


def try_str_to_int(x):
    try:
        return int(x)
    except ValueError:
        return x


def dict_keys_to_int(d):
    if isinstance(d, dict):
        return {try_str_to_int(k): dict_keys_to_int(v) for k, v in d.items()}
    return d


def find_group_id(groups, name):
    for i, g in enumerate(groups):
        if g['name'] == name:
            return i


def group_names_to_ids(groups, whole_map):
    for v in whole_map.values():
        if isinstance(v, dict):
            for k in v['M']:
                for i in range(len(v['M'][k])):
                    id = find_group_id(groups, v['M'][k][i])
                    assert id is not None
                    v['M'][k][i] = id


class NormalizationData:
    # Increment VERSION when the spec changes
    # or if the code in this class changes.
    # It will force the cache to be regenerated.
    VERSION = 1

    def __init__(self):
        with open(SPEC_PATH) as f:
            spec = json.load(f)

        self.ignored: Set[int] = set(spec['ignored'])
        self.mapped: Dict[int, List[int]] = {cp_src: mapping for cp_src, mapping in spec['mapped']}
        self.cm: Set[int] = set(spec['cm'])
        self.emoji: List[List[int]] = spec['emoji']
        self.nfc_check: Set[int] = set(spec['nfc_check'])
        self.fenced: Dict[int, str] = {x[0]: x[1] for x in spec['fenced']}
        self.groups: List[Dict] = read_groups(spec['groups'])
        self.valid: Set[int] = compute_valid(self.groups)
        self.whole_map: Dict = dict_keys_to_int(spec['whole_map'])
        group_names_to_ids(self.groups, self.whole_map)
        self.nsm_max: int = spec['nsm_max']
        self.nsm: Set[int] = set(spec['nsm'])

        self.cm.remove(CP_FE0F)

        self.emoji_fe0f_lookup = create_emoji_fe0f_lookup([''.join(chr(cp) for cp in cps) for cps in self.emoji])
        self.emoji_regex = regex.compile(create_emoji_regex_pattern([''.join(chr(cp) for cp in cps) for cps in self.emoji]))

def load_normalization_data() -> NormalizationData:
    """
    Loads `NormalizationData` from cached pickle file if it exists, otherwise creates it.
    Pickle is stored in `$HOME/.cache/ens_normalize/normalization_data.pkl`.
    It contains a version number, so if the version changes, the pickle is recreated.
    """
    cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'ens_normalize')
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, 'normalization_data.pkl')
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            data: NormalizationData = pickle.load(f)
            if data.VERSION == NormalizationData.VERSION:
                return data
    data = NormalizationData()
    # Python >= 3.8 is required for protocol 5
    buf = pickle.dumps(data, protocol=5)
    buf = pickletools.optimize(buf)
    with open(cache_path, 'wb') as f:
        f.write(buf)
    return data


NORMALIZATION = load_normalization_data()


def collapse_valid_tokens(tokens: List[Token]) -> List[Token]:
    """
    Combine cps from continuous valid tokens into single tokens.
    """
    out = []
    i = 0
    while i < len(tokens):
        if tokens[i].type == TY_VALID:
            j = i + 1
            while j < len(tokens) and tokens[j].type == TY_VALID:
                j += 1
            out.append(TokenValid(
                cps = [cp for k in range(i, j) for cp in tokens[k].cps],
            ))
            i = j
        else:
            out.append(tokens[i])
            i += 1
    return out


def cps_requires_check(cps: List[int]) -> bool:
    return any(cp in NORMALIZATION.nfc_check for cp in cps)


def normalize_tokens(tokens: List[Token]) -> List[Token]:
    """
    From https://github.com/adraffy/ens-normalize.js/blob/1571a7d226f564ac379a533a3b04a15977a0ae80/src/lib.js
    """
    i = 0
    start = -1
    while i < len(tokens):
        token = tokens[i]
        if token.type in (TY_VALID, TY_MAPPED):
            if cps_requires_check(token.cps):
                end = i + 1
                for pos in range(end, len(tokens)):
                    if tokens[pos].type in (TY_VALID, TY_MAPPED):
                        if not cps_requires_check(tokens[pos].cps):
                            break
                        end = pos + 1
                    elif tokens[pos].type != TY_IGNORED:
                        break
                if start < 0:
                    start = i
                slice = tokens[start:end]
                cps = [cp for tok in slice if tok.type in (TY_VALID, TY_MAPPED) for cp in tok.cps]
                str0 = cps2str(cps)
                str = NFC(str0)
                if str0 == str:
                    i = end - 1
                else:
                    tokens[start:end] = [TokenNFC(
                        input = cps,
                        cps = str2cps(str),
                    )]
                    i = start
                start = -1
            else:
                start = i
        elif token.type != TY_IGNORED:
            start = -1
        i += 1
    return collapse_valid_tokens(tokens)


def post_check_empty(name: str) -> Optional[Union[DisallowedNameError, CurableError]]:
    if len(name) == 0:
        return DisallowedNameError(DisallowedNameErrorType.EMPTY_NAME)
    if name[0] == '.':
        return CurableError(
            CurableErrorType.EMPTY_LABEL,
            index=0,
            disallowed='.',
            suggested='',
        )
    if name[-1] == '.':
        return CurableError(
            CurableErrorType.EMPTY_LABEL,
            index=len(name) - 1,
            disallowed='.',
            suggested='',
        )
    i = name.find('..')
    if i >= 0:
        return CurableError(
            CurableErrorType.EMPTY_LABEL,
            index=i,
            disallowed='..',
            suggested='.',
        )


def post_check_underscore(label: str) -> Optional[CurableError]:
    in_middle = False
    for i, c in enumerate(label):
        if c != '_':
            in_middle = True
        elif in_middle:
            cnt = 1
            while i + cnt < len(label) and label[i + cnt] == '_':
                cnt += 1
            return CurableError(
                CurableErrorType.UNDERSCORE,
                index=i,
                disallowed='_' * cnt,
                suggested='',
            )


def post_check_hyphen(label: str) -> Optional[CurableError]:
    if len(label) >= 4 and all(ord(cp) < 0x80 for cp in label) and '-' == label[2] == label[3]:
        return CurableError(
            CurableErrorType.HYPHEN,
            index=2,
            disallowed='--',
            suggested='',
        )


def post_check_cm_leading_emoji(cps: List[int]) -> Optional[CurableError]:
    for i in range(len(cps)):
        if cps[i] in NORMALIZATION.cm:
            if i == 0:
                return CurableError(
                    CurableErrorType.CM_START,
                    index=i,
                    disallowed=chr(cps[i]),
                    suggested='',
                )
            else:
                prev = cps[i - 1]
                # emojis were replaced with FE0F
                if prev == CP_FE0F:
                    return CurableError(
                        CurableErrorType.CM_EMOJI,
                        # we cannot report the emoji because it was replaced with FE0F
                        index=i,
                        disallowed=chr(cps[i]),
                        suggested='',
                    )


def make_fenced_error(cps: List[int], start: int, end: int) -> CurableError:
    suggested = ''
    if start == 0:
        type_ = CurableErrorType.FENCED_LEADING
    elif end == len(cps):
        type_ = CurableErrorType.FENCED_TRAILING
    else:
        type_ = CurableErrorType.FENCED_MULTI
        suggested = chr(cps[start])
    return CurableError(
        type_,
        index=start,
        disallowed=''.join(map(chr, cps[start:end])),
        suggested=suggested,
    )


def post_check_fenced(cps: List[int]) -> Optional[CurableError]:
    cp = cps[0]
    prev = NORMALIZATION.fenced.get(cp)
    if prev is not None:
        return make_fenced_error(cps, 0, 1)

    n = len(cps)
    last = -1
    for i in range(1, n):
        cp = cps[i]
        match = NORMALIZATION.fenced.get(cp)
        if match is not None:
            if last == i:
                return make_fenced_error(cps, i - 1, i + 1)
            last = i + 1

    if last == n:
        return make_fenced_error(cps, n - 1, n)


def post_check_group_whole(cps: List[int], is_greek: List[bool]) -> Optional[Union[DisallowedNameError, CurableError]]:
    cps_no_fe0f = [cp for cp in cps if cp != CP_FE0F]
    unique = set(cps_no_fe0f)
    # we pass cps with fe0f to align error position with the original input
    g, e = determine_group(unique, cps)
    if e is not None:
        return e
    g = g[0]
    # pass is_greek up to the caller
    is_greek[0] = g['name'] == 'Greek'
    return (
        post_check_group(g, cps_no_fe0f, cps)
        or post_check_whole(unique)
    )


def determine_group(unique: Iterable[int], cps: List[int]) -> Tuple[Optional[List[Dict]], Optional[CurableError]]:
    groups = NORMALIZATION.groups
    for cp in unique:
        gs = [g for g in groups if cp in g['V']]
        if len(gs) == 0:
            if groups == NORMALIZATION.groups:
                return None, CurableError(
                    CurableErrorType.DISALLOWED,
                    index=cps.index(cp),
                    disallowed=chr(cp),
                    suggested='',
                )
            else:
                return None, CurableError(
                    CurableErrorType.CONF_MIXED,
                    index=cps.index(cp),
                    disallowed=chr(cp),
                    suggested='',
                )
        groups = gs
        if len(groups) == 1:
            break
    return groups, None


def post_check_group(g, cps: List[int], input: List[int]) -> Optional[Union[DisallowedNameError, CurableError]]:
    v, m = g['V'], g['M']
    for cp in cps:
        if cp not in v:
            return CurableError(
                CurableErrorType.CONF_MIXED,
                index=input.index(cp),
                disallowed=chr(cp),
                suggested='',
            )
    if m:
        decomposed = str2cps(NFD(cps2str(cps)))
        i = 1
        e = len(decomposed)
        while i < e:
            if decomposed[i] in NORMALIZATION.nsm:
                j = i + 1
                while j < e and decomposed[j] in NORMALIZATION.nsm:
                    if j - i + 1 > NORMALIZATION.nsm_max:
                        return DisallowedNameError(DisallowedNameErrorType.NSM_TOO_MANY)
                    for k in range(i, j):
                        if decomposed[k] == decomposed[j]:
                            return DisallowedNameError(DisallowedNameErrorType.NSM_REPEATED)
                    j += 1
                i = j
            i += 1


def post_check_whole(cps: Iterable[int]) -> Optional[DisallowedNameError]:
    # Cannot report error index, operating on unique codepoints.
    # Not reporting disallowed sequence, see below.
    maker = None
    shared = []
    for cp in cps:
        whole = NORMALIZATION.whole_map.get(cp)
        if whole == 1:
            return None
        if whole is not None:
            set_ = whole['M'].get(cp)
            if maker is not None:
                maker = [g for g in maker if g in set_]
            else:
                maker = list(set_)
            if len(maker) == 0:
                return None
        else:
            shared.append(cp)
    if maker is not None:
        for g_ind in maker:
            g = NORMALIZATION.groups[g_ind]
            if all(cp in g['V'] for cp in shared):
                return DisallowedNameError(DisallowedNameErrorType.CONF_WHOLE)


def post_check(name: str, label_is_greek: List[bool]) -> Optional[Union[DisallowedNameError, CurableError]]:
    # name has emojis replaced with a single FE0F
    e = post_check_empty(name)
    if e is not None:
        return e
    label_offset = 0
    for label in name.split('.'):
        # will be set inside post_check_group_whole
        is_greek = [False]
        cps = str2cps(label)
        e = (
            post_check_underscore(label)
            or post_check_hyphen(label)
            or post_check_cm_leading_emoji(cps)
            or post_check_fenced(cps)
            or post_check_group_whole(cps, is_greek)
        )
        # was this label greek?
        label_is_greek.append(is_greek[0])
        if e is not None:
            # post_checks are called on a single label and need an offset
            if isinstance(e, CurableError):
                e.index = label_offset + e.index if e.index is not None else None
            return e
        label_offset += len(label) + 1

    return None


def find_normalization_transformations(tokens: List[Token]) -> List[NormalizationTransformation]:
    warnings = []
    warning = None
    start = 0
    disallowed = None
    suggestion = None
    for tok in tokens:
        if tok.type == TY_MAPPED:
            warning = NormalizationTransformationType.MAPPED
            disallowed = chr(tok.cp)
            suggestion = cps2str(tok.cps)
            scanned = 1
        elif tok.type == TY_IGNORED:
            warning = NormalizationTransformationType.IGNORED
            disallowed = chr(tok.cp)
            suggestion = ''
            scanned = 1
        elif tok.type == TY_EMOJI:
            if tok.input != tok.cps:
                warning = NormalizationTransformationType.FE0F
                disallowed = cps2str(tok.input)
                suggestion = cps2str(tok.cps)
            scanned = len(tok.input)
        elif tok.type == TY_NFC:
            warning = NormalizationTransformationType.NFC
            disallowed = cps2str(tok.input)
            suggestion = cps2str(tok.cps)
            scanned = len(tok.input)
        elif tok.type == TY_VALID:
            scanned = len(tok.cps)
        else:  # TY_STOP
            scanned = 1
        if warning is not None:
            warnings.append(NormalizationTransformation(warning, start, disallowed, suggestion))
            warning = None
        start += scanned
    return warnings


def tokens2str(tokens: List[Token], emoji_fn: Callable[[TokenEmoji], str] = lambda tok: cps2str(tok.cps)) -> str:
    t = []
    for tok in tokens:
        if tok.type in (TY_IGNORED, TY_DISALLOWED):
            continue
        elif tok.type == TY_EMOJI:
            t.append(emoji_fn(tok))
        elif tok.type == TY_STOP:
            t.append(chr(tok.cp))
        else:
            t.append(cps2str(tok.cps))
    return ''.join(t)


def tokens2beautified(tokens: List[Token], label_is_greek: List[bool]) -> str:
    s = []
    label_index = 0
    label_start = 0
    for i in range(len(tokens) + 1):
        if i < len(tokens) and tokens[i].type != TY_STOP:
            continue
        label_end = i

        for j in range(label_start, label_end):
            tok = tokens[j]
            if tok.type in (TY_IGNORED, TY_DISALLOWED):
                continue
            elif tok.type == TY_EMOJI:
                s.append(cps2str(tok.emoji))
            elif tok.type == TY_STOP:
                s.append(chr(tok.cp))
            else:
                if not label_is_greek[label_index]:
                    s.append(cps2str([CP_XI_CAPITAL if cp == CP_XI_SMALL else cp for cp in tok.cps]))
                else:
                    s.append(cps2str(tok.cps))

        label_start = i
        label_index += 1

    return ''.join(s)


def ens_process(input: str,
                do_normalize: bool = False,
                do_beautify: bool = False,
                do_tokenize: bool = False,
                do_transformations: bool = False,
                do_cure: bool = False) -> ENSProcessResult:
    """
    Used to compute

    - `ens_normalize`
    - `ens_beautify`
    - `ens_tokenize`
    - `ens_transformations`
    - `ens_cure`

    in one go.

    Returns `ENSProcessResult` with the following fields:
    - `normalized`: normalized name or `None` if input cannot be normalized or `do_normalize` is `False`
    - `beautified`: beautified name or `None` if input cannot be normalized or `do_beautify` is `False`
    - `tokens`: list of `Token` objects or `None` if `do_tokenize` is `False`
    - `cured`: cured name or `None` if input cannot be cured or `do_cure` is `False`
    - `cures`: list of fixed `CurableError` objects or `None` if input cannot be cured or `do_cure` is `False`
    - `error`: `DisallowedNameError` or `CurableError` or `None` if input is valid
    - `transformations`: list of `NormalizationTransformation` objects or `None` if `do_transformations` is `False`
    """
    tokens: List[Token] = []
    error = None

    input_cur = 0
    emoji_iter = NORMALIZATION.emoji_regex.finditer(input)
    next_emoji_match = next(emoji_iter, None)

    while input_cur < len(input):
        # if next emoji is at the current position
        if next_emoji_match is not None and next_emoji_match.start() == input_cur:
            # extract emoji
            emoji = next_emoji_match.group()
            # advance cursor
            input_cur = next_emoji_match.end()
            # prepare next emoji
            next_emoji_match = next(emoji_iter, None)

            emoji_no_fe0f = filter_fe0f(emoji)
            emoji_fe0f = NORMALIZATION.emoji_fe0f_lookup[emoji_no_fe0f]

            tokens.append(TokenEmoji(
                # 'pretty' version
                emoji = str2cps(emoji_fe0f),
                # raw input
                input = str2cps(emoji),
                # text version
                cps = str2cps(emoji_no_fe0f),
            ))

            continue

        c = input[input_cur]
        cp = ord(c)
        input_cur += 1

        if cp == CP_STOP:
            tokens.append(TokenStop())
            continue

        if cp in NORMALIZATION.valid:
            tokens.append(TokenValid(
                cps = [cp],
            ))
            continue

        if cp in NORMALIZATION.ignored:
            tokens.append(TokenIgnored(
                cp = cp,
            ))
            continue

        mapping = NORMALIZATION.mapped.get(cp)
        if mapping is not None:
            tokens.append(TokenMapped(
                cp = cp,
                cps = mapping,
            ))
            continue

        error = error or CurableError(
            CurableErrorType.INVISIBLE
            if c in ('\u200d', '\u200c')
            else CurableErrorType.DISALLOWED,
            index=input_cur - 1,
            disallowed=c,
            suggested='',
        )

        tokens.append(TokenDisallowed(
            cp = cp,
        ))

    tokens = normalize_tokens(tokens)

    transformations = find_normalization_transformations(tokens) if do_transformations else None

    if error is None:
        # run post checks
        emojis_as_fe0f = ''.join(tokens2str(tokens, lambda _: '\uFE0F'))
        # true for each label that is greek
        # will be set by post_check()
        label_is_greek = []
        error = post_check(emojis_as_fe0f, label_is_greek)
        if isinstance(error, CurableError):
            offset_err_start(error, tokens)

    # else:
        # only the result of post_check() is not input aligned
        # so we do not offset the error set by the input scanning loop

    if error is not None:
        normalized = None
        beautified = None
    else:
        normalized = tokens2str(tokens) if do_normalize else None
        beautified = tokens2beautified(tokens, label_is_greek) if do_beautify else None

    # respect the caller's wishes even though we tokenize anyway
    tokens = tokens if do_tokenize else None

    cured = None
    cures = None
    if do_cure:
        try:
            cured, cures = _ens_cure(input)
        except DisallowedNameError:
            pass

    return ENSProcessResult(
        normalized,
        beautified,
        tokens,
        cured,
        cures,
        error,
        transformations,
    )


def offset_err_start(err: Optional[CurableError], tokens: List[Token]):
    """
    Output of post_check() is not input aligned.
    This function offsets the error index (in-place) to match the input characters.
    """
    # index in string that was scanned
    i = 0
    # offset between input and scanned
    offset = 0
    for tok in tokens:
        if i >= err.index:
            # everything before the error is aligned
            break
        if tok.type in (TY_IGNORED, TY_DISALLOWED):
            # input: 1, scanned: 0
            offset += 1
        elif tok.type == TY_EMOJI:
            # input: raw emoji, scanned: FE0F
            offset += len(tok.input) - 1
            i += 1
        elif tok.type == TY_NFC:
            # input: pre NFC, scanned: post NFC
            offset += len(tok.input) - len(tok.cps)
            i += len(tok.cps)
        elif tok.type == TY_MAPPED:
            # input: cp, scanned: mapping
            offset += 1 - len(tok.cps)
            i += len(tok.cps)
        elif tok.type == TY_STOP:
            # input: 1, scanned: 1
            i += 1
        else:
            # input: cps, scanned: cps
            i += len(tok.cps)
    err.index += offset


def ens_normalize(text: str) -> str:
    """
    Apply ENS normalization to a string.

    Raises DisallowedNameError if the input cannot be normalized.
    """
    res = ens_process(text, do_normalize=True)
    if res.error is not None:
        raise res.error
    return res.normalized


def _ens_cure(text: str) -> Tuple[str, List[CurableError]]:
    cures = []
    while True:
        try:
            return ens_normalize(text), cures
        except CurableError as e:
            new_text = text[:e.index] + e.suggested + text[e.index + len(e.disallowed):]
            # protect against infinite loops
            assert new_text != text, 'ens_cure() entered an infinite loop'
            text = new_text
            cures.append(e)


def ens_cure(text: str) -> str:
    """
    Apply ENS normalization to a string. If the result is not normalized then this function
    will try to make the input normalized by removing all disallowed characters.

    Raises `DisallowedNameError` if one is encountered and cannot be cured.
    """
    return _ens_cure(text)[0]


def ens_beautify(text: str) -> str:
    """
    Apply ENS normalization with beautification to a string.

    Raises DisallowedNameError if the input cannot be normalized.
    """
    res = ens_process(text, do_beautify=True)
    if res.error is not None:
        raise res.error
    return res.beautified


def ens_tokenize(input: str) -> List[Token]:
    """
    Tokenize a string using ENS normalization.

    Returns a list of tokens.

    Each token contains a `type` field and other fields depending on the type.
    All codepoints are represented as integers.

    Token types and their fields:
    - valid
        - cps: list of codepoints
    - mapped
        - cp: input codepoint
        - cps: list of output codepoints
    - ignored
        - cp: codepoint
    - disallowed
        - cp: codepoint
    - emoji
        - emoji: 'pretty' version of the emoji codepoints (with FE0F)
        - input: raw input codepoints
        - cps: text version of the emoji codepoints (without FE0F)
    - stop:
        - cp: 0x2E
    - nfc
        - input: input codepoints
        - cps: output codepoints (after NFC normalization)
    """
    return ens_process(input, do_tokenize=True).tokens


def ens_transformations(input: str) -> List[NormalizationTransformation]:
    """
    This function returns a list of `NormalizationTransformation` objects
    that describe the modifications applied by ENS normalization to the input string.

    Raises DisallowedNameError if the input cannot be normalized.
    """
    res = ens_process(input, do_transformations=True)
    if res.error is not None:
        raise res.error
    return res.transformations


def is_ens_normalized(name: str) -> bool:
    """
    Checks if the input string is already ENS normalized
    (i.e. `ens_normalize(name) == name`).
    """
    return ens_process(name, do_normalize=True).normalized == name
