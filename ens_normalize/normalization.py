from typing import Callable, Dict, List, NamedTuple, Set, Optional, Tuple, Union, Iterable
from enum import Enum
import re
import json
import os
import pickle
from pyunormalize import NFC, NFD, UNICODE_VERSION
import warnings


SPEC_PICKLE_PATH = os.path.join(os.path.dirname(__file__), 'spec.pickle')


class DisallowedSequenceTypeBase(Enum):
    '''
    Base class for disallowed sequence types.
    See README: Glossary -> Sequences.
    '''

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


class CurableSequenceTypeBase(Enum):
    '''
    Base class for curable sequence types.
    See README: Glossary -> Sequences.
    '''

    def __new__(cls, *args):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, general_info: str, sequence_info: str):
        self.general_info = general_info
        self.sequence_info = sequence_info

    @property
    def code(self) -> str:
        return self.name


class DisallowedSequenceType(DisallowedSequenceTypeBase):
    """
    The type of a disallowed sequence.
    See README: Glossary -> Sequences.
    """

    # NSM --------------------

    NSM_REPEATED = "Contains a repeated non-spacing mark"

    NSM_TOO_MANY = "Contains too many consecutive non-spacing marks"

    # CONFUSABLES ----------

    CONF_WHOLE = "Contains visually confusing characters from {script1} and {script2} scripts"


class CurableSequenceType(CurableSequenceTypeBase):
    """
    The type of a curable sequence.
    See README: Glossary -> Sequences.
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

    CONF_MIXED = "Contains visually confusing characters from multiple scripts ({scripts})", \
                 "This character{script1} is disallowed because it is visually confusing with another character{script2}"


class NormalizableSequenceType(CurableSequenceTypeBase):
    """
    The type of a normalizable sequence.
    See README: Glossary -> Sequences.
    """

    IGNORED   = "Contains disallowed \"ignored\" characters that have been removed", \
                "This character is ignored during normalization and has been automatically removed"

    MAPPED    = "Contains a disallowed character that has been replaced by a normalized sequence", \
                "This character is disallowed and has been automatically replaced by a normalized sequence"

    FE0F      = "Contains a disallowed variant of an emoji which has been replaced by an equivalent normalized emoji", \
                "This emoji has been automatically fixed to remove an invisible character"

    NFC       = "Contains a disallowed sequence that is not \"NFC normalized\" which has been replaced by an equivalent normalized sequence", \
                "This sequence has been automatically normalized into NFC canonical form"


class DisallowedSequence(Exception):
    '''
    An unnormalized sequence without any normalization suggestion.
    See README: Glossary -> Sequences.
    '''

    def __init__(self, type: DisallowedSequenceType, meta: Dict[str, str] = {}):
        super().__init__(type.general_info)
        self.type = type
        self.meta = meta

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
        return self.type.general_info.format(**self.meta)


class CurableSequence(DisallowedSequence):
    '''
    An unnormalized sequence containing a normalization suggestion that is automatically applied using `ens_cure`.
    See README: Glossary -> Sequences.
    '''

    def __init__(self,
                 type: CurableSequenceType,
                 index: int,
                 sequence: str,
                 suggested: str,
                 meta: Dict[str, str] = {}):
        super().__init__(type, meta)
        self.type = type
        self.index = index
        self.sequence = sequence
        self.suggested = suggested

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(code="{self.type.code}", index={self.index}, sequence="{self.sequence}", suggested="{self.suggested}")'

    @property
    def sequence_info(self) -> str:
        """
        Information about the disallowed sequence.
        """
        return self.type.sequence_info.format(
            sequence=self.sequence,
            suggested=self.suggested,
            **self.meta,
        )


class NormalizableSequence(CurableSequence):
    '''
    An unnormalized sequence containing a normalization suggestion that is automatically applied using `ens_normalize` and `ens_cure`.
    See README: Glossary -> Sequences.
    '''

    def __init__(self,
                 type: NormalizableSequenceType,
                 index: int,
                 sequence: str,
                 suggested: str,
                 meta: Dict[str, str] = {}):
        super().__init__(type, index, sequence, suggested, meta)
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
    cures: Optional[List[CurableSequence]]
    error: Optional[DisallowedSequence]
    normalizations: Optional[List[NormalizableSequence]]


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


def create_emoji_regex_pattern(emojis: List[str]) -> str:
    fe0f = re.escape('\uFE0F')
    def make_emoji(emoji: str) -> str:
        # make FE0F optional
        return re.escape(emoji).replace(fe0f, f'{fe0f}?')
    # sort to match the longest first
    def order(emoji: str) -> int:
        # emojis with FE0F need to be pushed back because the FE0F would trap the regex matching
        # re.search(r'AF?|AB', '_AB_')
        # >>> <re.Match object; span=(1, 2), match='A'>
        return len(filter_fe0f(emoji))
    return '|'.join(make_emoji(emoji) for emoji in sorted(emojis, key=order, reverse=True))


def create_emoji_fe0f_lookup(emojis: List[str]) -> Dict[str, str]:
    """
    Create a lookup table for recreating FE0F emojis from non-FE0F emojis.
    """
    return {filter_fe0f(emoji): emoji for emoji in emojis}


def compute_valid(groups: List[Dict]) -> Set[int]:
    '''
    Compute the set of valid codepoints from the spec.json file.
    '''
    valid = set()
    for g in groups:
        valid.update(g['V'])
    valid.update(map(ord, NFD(''.join(map(chr, valid)))))
    return valid


def read_groups(groups: List[Dict]) -> List[Dict]:
    '''
    Read and parse the groups field from the spec.json file.
    '''
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
    '''
    Recursively convert dictionary keys to integers (for JSON parsing).
    '''
    if isinstance(d, dict):
        return {try_str_to_int(k): dict_keys_to_int(v) for k, v in d.items()}
    return d


def find_group_id(groups, name):
    '''
    Find the index of a group by name.
    '''
    for i, g in enumerate(groups):
        if g['name'] == name:
            return i


def group_names_to_ids(groups, whole_map):
    '''
    Convert group names to group ids in the whole_map for faster lookup.
    '''
    for v in whole_map.values():
        if isinstance(v, dict):
            for k in v['M']:
                for i in range(len(v['M'][k])):
                    id = find_group_id(groups, v['M'][k][i])
                    assert id is not None
                    v['M'][k][i] = id


class NormalizationData:
    def __init__(self, spec_json_path: str):
        with open(spec_json_path, encoding='utf-8') as f:
            spec = json.load(f)

        self.unicode_version: str = spec['unicode']
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
        self.emoji_regex = re.compile(create_emoji_regex_pattern([''.join(chr(cp) for cp in cps) for cps in self.emoji]))


def load_normalization_data_pickle(spec_pickle_path: str) -> NormalizationData:
    """
    Loads `NormalizationData` from a pickle file.
    """
    with open(spec_pickle_path, 'rb') as f:
        return pickle.load(f)


NORMALIZATION = load_normalization_data_pickle(SPEC_PICKLE_PATH)


def check_spec_unicode_version():
    if not NORMALIZATION.unicode_version.startswith(UNICODE_VERSION):
        warnings.warn(
            f'Unicode version mismatch: '
            f'pyunormalize is using {UNICODE_VERSION}, '
            f'but the ENS Normalization spec is for {NORMALIZATION.unicode_version}',
            UnicodeWarning,
        )


check_spec_unicode_version()


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


def post_check_empty(name: str, input: str) -> Optional[CurableSequence]:
    if len(name) == 0:
        # fully ignorable name
        return CurableSequence(
            CurableSequenceType.EMPTY_LABEL,
            index=0,
            sequence=input,
            suggested='',
        )
    if name[0] == '.':
        return CurableSequence(
            CurableSequenceType.EMPTY_LABEL,
            index=0,
            sequence='.',
            suggested='',
        )
    if name[-1] == '.':
        return CurableSequence(
            CurableSequenceType.EMPTY_LABEL,
            index=len(name) - 1,
            sequence='.',
            suggested='',
        )
    i = name.find('..')
    if i >= 0:
        return CurableSequence(
            CurableSequenceType.EMPTY_LABEL,
            index=i,
            sequence='..',
            suggested='.',
        )


def post_check_underscore(label: str) -> Optional[CurableSequence]:
    in_middle = False
    for i, c in enumerate(label):
        if c != '_':
            in_middle = True
        elif in_middle:
            cnt = 1
            while i + cnt < len(label) and label[i + cnt] == '_':
                cnt += 1
            return CurableSequence(
                CurableSequenceType.UNDERSCORE,
                index=i,
                sequence='_' * cnt,
                suggested='',
            )


def post_check_hyphen(label: str) -> Optional[CurableSequence]:
    if len(label) >= 4 and all(ord(cp) < 0x80 for cp in label) and '-' == label[2] == label[3]:
        return CurableSequence(
            CurableSequenceType.HYPHEN,
            index=2,
            sequence='--',
            suggested='',
        )


def post_check_cm_leading_emoji(cps: List[int]) -> Optional[CurableSequence]:
    for i in range(len(cps)):
        if cps[i] in NORMALIZATION.cm:
            if i == 0:
                return CurableSequence(
                    CurableSequenceType.CM_START,
                    index=i,
                    sequence=chr(cps[i]),
                    suggested='',
                )
            else:
                prev = cps[i - 1]
                # emojis were replaced with FE0F
                if prev == CP_FE0F:
                    return CurableSequence(
                        CurableSequenceType.CM_EMOJI,
                        # we cannot report the emoji because it was replaced with FE0F
                        index=i,
                        sequence=chr(cps[i]),
                        suggested='',
                    )


def make_fenced_error(cps: List[int], start: int, end: int) -> CurableSequence:
    suggested = ''
    if start == 0:
        type_ = CurableSequenceType.FENCED_LEADING
    elif end == len(cps):
        type_ = CurableSequenceType.FENCED_TRAILING
    else:
        type_ = CurableSequenceType.FENCED_MULTI
        suggested = chr(cps[start])
    return CurableSequence(
        type_,
        index=start,
        sequence=''.join(map(chr, cps[start:end])),
        suggested=suggested,
    )


def post_check_fenced(cps: List[int]) -> Optional[CurableSequence]:
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


def post_check_group_whole(cps: List[int], is_greek: List[bool]) -> Optional[Union[DisallowedSequence, CurableSequence]]:
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
        or post_check_whole(g, unique)
    )


def meta_for_conf_mixed(g, cp):
    '''
    Create metadata for the CONF_MIXED error.
    '''
    s1 = [g['name'] for g in NORMALIZATION.groups if cp in g['V']]
    s1 = s1[0] if s1 else None
    s2 = g['name']
    if s1 is not None:
        return {
            'scripts': f'{s1}/{s2}',
            'script1': f' from the {s1} script',
            'script2': f' from the {s2} script',
        }
    else:
        return {
            'scripts': f'{s2} plus other scripts',
            'script1': '',
            'script2': f' from the {s2} script',
        }


def determine_group(unique: Iterable[int], cps: List[int]) -> Tuple[Optional[List[Dict]], Optional[CurableSequence]]:
    groups = NORMALIZATION.groups
    for cp in unique:
        gs = [g for g in groups if cp in g['V']]
        if len(gs) == 0:
            if groups == NORMALIZATION.groups:
                return None, CurableSequence(
                    CurableSequenceType.DISALLOWED,
                    index=cps.index(cp),
                    sequence=chr(cp),
                    suggested='',
                )
            else:
                return None, CurableSequence(
                    CurableSequenceType.CONF_MIXED,
                    index=cps.index(cp),
                    sequence=chr(cp),
                    suggested='',
                    meta=meta_for_conf_mixed(groups[0], cp),
                )
        groups = gs
        if len(groups) == 1:
            break
    return groups, None


def post_check_group(g, cps: List[int], input: List[int]) -> Optional[Union[DisallowedSequence, CurableSequence]]:
    v, m = g['V'], g['M']
    for cp in cps:
        if cp not in v:
            return CurableSequence(
                CurableSequenceType.CONF_MIXED,
                index=input.index(cp),
                sequence=chr(cp),
                suggested='',
                meta=meta_for_conf_mixed(g, cp),
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
                        return DisallowedSequence(DisallowedSequenceType.NSM_TOO_MANY)
                    for k in range(i, j):
                        if decomposed[k] == decomposed[j]:
                            return DisallowedSequence(DisallowedSequenceType.NSM_REPEATED)
                    j += 1
                i = j
            i += 1


def post_check_whole(group, cps: Iterable[int]) -> Optional[DisallowedSequence]:
    # Cannot report error index, operating on unique codepoints.
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
                return DisallowedSequence(
                    DisallowedSequenceType.CONF_WHOLE,
                    meta={
                        'script1': group['name'],
                        'script2': g['name'],
                    },
                )


def post_check(name: str, label_is_greek: List[bool], input: str) -> Optional[Union[DisallowedSequence, CurableSequence]]:
    # name has emojis replaced with a single FE0F
    if len(input) == 0:
        return None
    e = post_check_empty(name, input)
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
            if isinstance(e, CurableSequence): # or NormalizableSequence because of inheritance
                e.index = label_offset + e.index if e.index is not None else None
            return e
        label_offset += len(label) + 1

    return None


def find_normalizations(tokens: List[Token]) -> List[NormalizableSequence]:
    warnings = []
    warning = None
    start = 0
    disallowed = None
    suggestion = None
    for tok in tokens:
        if tok.type == TY_MAPPED:
            warning = NormalizableSequenceType.MAPPED
            disallowed = chr(tok.cp)
            suggestion = cps2str(tok.cps)
            scanned = 1
        elif tok.type == TY_IGNORED:
            warning = NormalizableSequenceType.IGNORED
            disallowed = chr(tok.cp)
            suggestion = ''
            scanned = 1
        elif tok.type == TY_EMOJI:
            if tok.input != tok.cps:
                warning = NormalizableSequenceType.FE0F
                disallowed = cps2str(tok.input)
                suggestion = cps2str(tok.cps)
            scanned = len(tok.input)
        elif tok.type == TY_NFC:
            warning = NormalizableSequenceType.NFC
            disallowed = cps2str(tok.input)
            suggestion = cps2str(tok.cps)
            scanned = len(tok.input)
        elif tok.type == TY_VALID:
            scanned = len(tok.cps)
        else:  # TY_STOP
            scanned = 1
        if warning is not None:
            warnings.append(NormalizableSequence(warning, start, disallowed, suggestion))
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


SIMPLE_NAME_REGEX = re.compile(r'^[a-z0-9]+(?:\.[a-z0-9]+)*$')


def ens_process(input: str,
                do_normalize: bool = False,
                do_beautify: bool = False,
                do_tokenize: bool = False,
                do_normalizations: bool = False,
                do_cure: bool = False) -> ENSProcessResult:
    """
    Used to compute

    - `ens_normalize`
    - `ens_beautify`
    - `ens_tokenize`
    - `ens_normalizations`
    - `ens_cure`

    in one go.

    Returns `ENSProcessResult` with the following fields:
    - `normalized`: normalized name or `None` if input cannot be normalized or `do_normalize` is `False`
    - `beautified`: beautified name or `None` if input cannot be normalized or `do_beautify` is `False`
    - `tokens`: list of `Token` objects or `None` if `do_tokenize` is `False`
    - `cured`: cured name or `None` if input cannot be cured or `do_cure` is `False`
    - `cures`: list of fixed `CurableSequence` objects or `None` if input cannot be cured or `do_cure` is `False`
    - `error`: `DisallowedSequence` or `CurableSequence` or `None` if input is valid
    - `normalizations`: list of `NormalizableSequence` objects or `None` if `do_normalizations` is `False`
    """
    if SIMPLE_NAME_REGEX.match(input) is not None:
        if do_tokenize:
            tokens = []
            current_cps = []
            for c in input:
                if ord(c) == CP_STOP:
                    tokens.append(TokenValid(cps=current_cps))
                    tokens.append(TokenStop())
                    current_cps = []
                else:
                    current_cps.append(ord(c))
            tokens.append(TokenValid(cps=current_cps))
        else:
            tokens = None
        return ENSProcessResult(
            normalized=input if do_normalize else None,
            beautified=input if do_beautify else None,
            tokens=tokens,
            cured=input if do_cure else None,
            cures=[] if do_cure else None,
            error=None,
            normalizations=[] if do_normalizations else None,
        )

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

        error = error or CurableSequence(
            CurableSequenceType.INVISIBLE
            if c in ('\u200d', '\u200c')
            else CurableSequenceType.DISALLOWED,
            index=input_cur - 1,
            sequence=c,
            suggested='',
        )

        tokens.append(TokenDisallowed(
            cp = cp,
        ))

    tokens = normalize_tokens(tokens)

    normalizations = find_normalizations(tokens) if do_normalizations else None

    if error is None:
        # run post checks
        emojis_as_fe0f = ''.join(tokens2str(tokens, lambda _: '\uFE0F'))
        # true for each label that is greek
        # will be set by post_check()
        label_is_greek = []
        error = post_check(emojis_as_fe0f, label_is_greek, input)
        if isinstance(error, CurableSequence): # or NormalizableSequence because of inheritance
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
        except DisallowedSequence:
            pass

    return ENSProcessResult(
        normalized,
        beautified,
        tokens,
        cured,
        cures,
        error,
        normalizations,
    )


def offset_err_start(err: Optional[CurableSequence], tokens: List[Token]):
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

    Raises DisallowedSequence if the input cannot be normalized.
    """
    res = ens_process(text, do_normalize=True)
    if res.error is not None:
        raise res.error
    return res.normalized


def _ens_cure(text: str) -> Tuple[str, List[CurableSequence]]:
    cures = []
    # Protect against infinite loops.
    # The assumption is that n iterations are enough to cure the input (2n just in case).
    # +1 is for the last iteration that should raise DisallowedSequence.
    # All cures currently implemented remove a character so this assumption seems reasonable.
    for _ in range(2 * len(text) + 1):
        try:
            return ens_normalize(text), cures
        except CurableSequence as e:
            text = text[:e.index] + e.suggested + text[e.index + len(e.sequence):]
            cures.append(e)
        # DisallowedSequence is not caught here because it is not curable
    # this should never happen
    raise Exception('ens_cure() exceeded max iterations. Please report this as a bug along with the input string.')


def ens_cure(text: str) -> str:
    """
    Apply ENS normalization to a string. If the result is not normalized then this function
    will try to make the input normalized by removing all disallowed characters.

    Raises `DisallowedSequence` if one is encountered and cannot be cured.
    """
    return _ens_cure(text)[0]


def ens_beautify(text: str) -> str:
    """
    Apply ENS normalization with beautification to a string.

    Raises DisallowedSequence if the input cannot be normalized.
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


def ens_normalizations(input: str) -> List[NormalizableSequence]:
    """
    This function returns a list of `NormalizableSequence` objects
    that describe the modifications applied by ENS normalization to the input string.

    Raises DisallowedSequence if the input cannot be normalized.
    """
    res = ens_process(input, do_normalizations=True)
    if res.error is not None:
        raise res.error
    return res.normalizations


def is_ens_normalized(name: str) -> bool:
    """
    Checks if the input string is already ENS normalized
    (i.e. `ens_normalize(name) == name`).
    """
    return ens_process(name, do_normalize=True).normalized == name


def is_ens_normalizable(name: str) -> bool:
    """
    Checks if the input string is ENS normalizable
    (i.e. `ens_normalize(name)` will not raise `DisallowedSequence`).
    """
    return ens_process(name).error is None
