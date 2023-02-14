from typing import Callable, Dict, List, NamedTuple, Set, Optional, Tuple, Union
from enum import Enum
import regex
import json
import os
from pyunormalize import NFC, NFD


SPEC_PATH = os.path.join(os.path.dirname(__file__), 'spec.json')


class NormalizationErrorType(Enum):
    def __new__(cls, *args):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, message: str, details: str):
        self.message = message
        self.details = details

    @property
    def code(self) -> str:
        return self.name.removeprefix('NORM_ERR_')

    # GENERIC ----------------

    NORM_ERR_UNDERSCORE = "Contains an underscore in a disallowed position", \
                          "An underscore is only allowed at the start of a label"

    NORM_ERR_HYPHEN     = "Contains the sequence '--' in a disallowed position", \
                          "Hyphens are disallowed at the 2nd and 3rd positions of a label"

    NORM_ERR_EMPTY      = "Contains a disallowed empty label", \
                          "Empty labels are not allowed, e.g. abc..eth"

    # This should not happen unless there is a bug in the code
    # If an exception is raised this will be returned as the error
    NORM_ERR_OTHER      = "Unknown normalization error", \
                          "Internal error during normalization"

    # CM ---------------------

    NORM_ERR_CM_START   = "Contains a combining mark in a disallowed position at the start of the label", \
                          "A combining mark is disallowed at the start of a label"

    NORM_ERR_CM_EMOJI   = "Contains a combining mark in a disallowed position after an emoji", \
                          "A combining mark is disallowed after an emoji"

    NORM_ERR_CM_MULTI   = "Contains a disallowed sequence of multiple sequential combining marks", \
                          "A sequence of this many combining marks is not allowed in the script used by this label"

    # TOKENS -----------------

    NORM_ERR_DISALLOWED = "Contains a disallowed character", \
                          "This character is disallowed"

    NORM_ERR_INVISIBLE  = "Contains a disallowed invisible character", \
                          "This invisible character is disallowed"

    NORM_ERR_IGNORED    = "Contains a disallowed \"ignored\" sequence that is disallowed from inclusion in a label when it is saved to the blockchain during a valid registration", \
                          "This sequence should be \"ignored\" during normalization and is disallowed from inclusion in a label when it is saved to the blockchain during a valid registration"

    NORM_ERR_MAPPED     = "Contains a disallowed \"mapped\" sequence that is disallowed from inclusion in a label when it is saved to the blockchain during a valid registration", \
                          "This sequence should be \"mapped\" for replacement by the alternative sequence \"{suggested_replacement}\" and is disallowed from inclusion in a label when it is saved to the blockchain during a valid registration"

    NORM_ERR_FE0F       = "Contains a disallowed invisible character inside an emoji", \
                          "This emoji should be correctly encoded to remove the invisible character that is disallowed from inclusion in a label when it is saved to the blockchain during a valid registration"

    NORM_ERR_NFC        = "Contains a disallowed sequence that is not \"NFC normalized\" into canonical form", \
                          "This sequence should be correctly \"NFC normalized\" into its canonical form when it is saved to the blockchain during a valid registration"

    # FENCED ----------------

    NORM_ERR_FENCED_LEADING = "Contains a fenced character at the start of a label", \
                              "There are certain characters (fenced) which cannot be the first character"

    NORM_ERR_FENCED_MULTI   = "Contains a fenced character after another fenced character", \
                              "There are certain characters (fenced) which cannot directly follow another fenced character"
                              
    NORM_ERR_FENCED_TRAILING = "Contains a fenced character at the end of a label", \
                               "There are certain characters (fenced) which cannot be the last character"

    # CONFUSABLES ----------

    NORM_ERR_CONF_WHOLE = "Contains whole-script confusables", \
                          "Contains a combination of characters which look confusable. It is unknown which character should be replaced so a disallowed sequence is not reported"

    NORM_ERR_CONF_MIXED = "Contains mixed-script confusables", \
                          "Contains characters from multiple scripts which look confusable"


class NormalizationError(NamedTuple):
    type: NormalizationErrorType
    start: Optional[int]
    disallowed: Optional[str]
    suggested: Optional[str]

    @property
    def code(self) -> str:
        return self.type.code

    @property
    def message(self) -> str:
        return self.type.message


TY_VALID = 'valid'
TY_MAPPED = 'mapped'
TY_IGNORED = 'ignored'
TY_DISALLOWED = 'disallowed'
TY_ISOLATED = 'isolated'
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
    tokens: List[Token]
    error: Optional[NormalizationError]
    is_fatal: bool


def str2cps(text: str) -> List[int]:
    '''
    Convert text to a list of integer codepoints.
    '''
    return [ord(c) for c in text]


def cps2str(cps: List[int]) -> str:
    '''
    Convert a list of integer codepoints to string.
    '''
    return ''.join(chr(cp) for cp in cps)


def filter_fe0f(text: str) -> str:
    '''
    Remove all FE0F from text.
    '''
    return text.replace('\uFE0F', '')


def add_all_fe0f(emojis: List[str]):
    '''
    Find all emoji sequence prefixes that can be followed by FE0F.
    Then, append FE0F to all prefixes that can but do not have it already.
    This emulates adraffy's trie building algorithm, which does not add FE0F nodes,
    but sets a "can be followed by FE0F" flag on the previous node.
    '''
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
    # sort to match longest first
    return '|'.join(make_emoji(emoji) for emoji in sorted(emojis, key=len, reverse=True))


def create_emoji_fe0f_lookup(emojis: List[str]) -> Dict[str, str]:
    '''
    Create a lookup table for recreating FE0F emojis from non-FE0F emojis.
    '''
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
            'M': int(g['cm']) if isinstance(g['cm'], int) else -1,
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
    raise ValueError(f'Group {name} not found')


def group_names_to_ids(groups, whole_map):
    for k, v in whole_map.items():
        if isinstance(v, dict):
            for k in v['M']:
                for i in range(len(v['M'][k])):
                    v['M'][k][i] = find_group_id(groups, v['M'][k][i])


class NormalizationData:
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

        self.cm.remove(CP_FE0F)

        self.emoji_fe0f_lookup = create_emoji_fe0f_lookup([''.join(chr(cp) for cp in cps) for cps in self.emoji])
        self.emoji_regex = regex.compile(create_emoji_regex_pattern([''.join(chr(cp) for cp in cps) for cps in self.emoji]))


NORMALIZATION = NormalizationData()


def restore_fe0f_in_emoji(emoji: str) -> str:
    '''
    Restore missing FE0Fs in emoji.
    Equivalent to ens_beautify on a single emoji.
    '''
    return NORMALIZATION.emoji_fe0f_lookup.get(filter_fe0f(emoji), emoji)


def collapse_valid_tokens(tokens: List[Token]) -> List[Token]:
    '''
    Combine cps from continuous valid tokens into single tokens.
    '''
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
    '''
    From https://github.com/adraffy/ens-normalize.js/blob/1571a7d226f564ac379a533a3b04a15977a0ae80/src/lib.js
    '''
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


def post_check_null_label(label: str) -> Optional[NormalizationError]:
    if len(label) == 0:
        return NormalizationError(
            NormalizationErrorType.NORM_ERR_EMPTY,
            start=0,
            disallowed='',
            suggested='',
        )


def post_check_underscore(label: str) -> Optional[NormalizationError]:
    in_middle = False
    for i, c in enumerate(label):
        if c != '_':
            in_middle = True
        elif in_middle:
            cnt = 1
            while i + cnt < len(label) and label[i + cnt] == '_':
                cnt += 1
            return NormalizationError(
                NormalizationErrorType.NORM_ERR_UNDERSCORE,
                start=i,
                disallowed='_' * cnt,
                suggested='',
            )


def post_check_hyphen(label: str) -> Optional[NormalizationError]:
    if len(label) >= 4 and all(ord(cp) < 0x80 for cp in label) and '-' == label[2] == label[3]:
        return NormalizationError(
            NormalizationErrorType.NORM_ERR_HYPHEN,
            start=2,
            disallowed='--',
            suggested='',
        )


def post_check_cm_leading_emoji(cps: List[int]) -> Optional[NormalizationError]:
    for i in range(len(cps)):
        if cps[i] in NORMALIZATION.cm:
            if i == 0:
                return NormalizationError(
                    NormalizationErrorType.NORM_ERR_CM_START,
                    start=i,
                    disallowed=chr(cps[i]),
                    suggested='',
                )
            else:
                prev = cps[i - 1]
                # emojis were replaced with FE0F
                if prev == CP_FE0F:
                    return NormalizationError(
                        NormalizationErrorType.NORM_ERR_CM_EMOJI,
                        # we cannot report the emoji because it was replaced with FE0F
                        start=i,
                        disallowed=chr(cps[i]),
                        suggested='',
                    )


def make_fenced_error(cps: List[int], start: int, end: int) -> NormalizationError:
    type_ = None
    suggested = ''
    if start == 0:
        type_ = NormalizationErrorType.NORM_ERR_FENCED_LEADING
    elif end == len(cps):
        type_ = NormalizationErrorType.NORM_ERR_FENCED_TRAILING
    else:
        type_ = NormalizationErrorType.NORM_ERR_FENCED_MULTI
        suggested = chr(cps[start])
    return NormalizationError(
        type_,
        start=start,
        disallowed=''.join(map(chr, cps[start:end])),
        suggested=suggested,
    )


def post_check_fenced(cps: List[int]) -> Optional[NormalizationError]:
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


def post_check_group_whole(cps: List[int], is_greek: List[bool]) -> Optional[NormalizationError]:
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


def determine_group(unique: List[int], cps: List[int]) -> Tuple[Optional[List[Dict]], Optional[NormalizationError]]:
    groups = NORMALIZATION.groups
    for cp in unique:
        gs = [g for g in groups if cp in g['V']]
        if len(gs) == 0:
            if groups == NORMALIZATION.groups:
                return None, NormalizationError(
                    NormalizationErrorType.NORM_ERR_DISALLOWED,
                    start=cps.index(cp),
                    disallowed=chr(cp),
                    suggested='',
                )
            else:
                return None, NormalizationError(
                    NormalizationErrorType.NORM_ERR_CONF_MIXED,
                    start=cps.index(cp),
                    disallowed=chr(cp),
                    suggested='',
                )
        groups = gs
        if len(groups) == 1:
            break
    return groups, None


def post_check_group(g, cps: List[int], input: List[int]) -> Optional[NormalizationError]:
    v, m = g['V'], g['M']
    for cp in cps:
        if cp not in v:
            return NormalizationError(
                NormalizationErrorType.NORM_ERR_CONF_MIXED,
                start=input.index(cp),
                disallowed=chr(cp),
                suggested='',
            )
    if m >= 0:
        decomposed = [ord(c) for c in NFD(''.join(chr(cp) for cp in cps))]
        i = 1
        e = len(decomposed)
        while i < e:
            if decomposed[i] in NORMALIZATION.cm:
                j = i + 1
                while j < e and decomposed[j] in NORMALIZATION.cm:
                    j += 1
                if j - i > m:
                    # We cannot report the entire sequence because it might contain codepoints that are not in the input (NFD).
                    # There must be at least one extra CM in the input because the NFC form of a character will never throw CM_MULTI by itself.
                    bad_cp_i = None
                    for k in range(i, j):
                        if decomposed[k] in input:
                            bad_cp_i = input.index(decomposed[k])
                            break
                    # will raise exception if bad_cp_i is None
                    return NormalizationError(
                        NormalizationErrorType.NORM_ERR_CM_MULTI,
                        start=bad_cp_i,
                        disallowed=chr(input[bad_cp_i]),
                        suggested='',
                    )
                i = j
            i += 1


def post_check_whole(g, cps: List[int]) -> Optional[NormalizationError]:
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
                return NormalizationError(
                    NormalizationErrorType.NORM_ERR_CONF_WHOLE,
                    start=None,
                    # could sometimes return shared[0] but shared can be empty
                    disallowed=None,
                    suggested=None,
                )


def post_check(name: str, label_is_greek: List[bool]) -> Optional[NormalizationError]:
    # name has emojis replaced with a single FE0F
    label_offset = 0
    for label in name.split('.'):
        # will be set inside post_check_group_whole
        is_greek = [False]
        cps = str2cps(label)
        e = (
            post_check_null_label(label)
            or post_check_underscore(label)
            or post_check_hyphen(label)
            or post_check_cm_leading_emoji(cps)
            or post_check_fenced(cps)
            or post_check_group_whole(cps, is_greek)
        )
        # was this label greek?
        label_is_greek.append(is_greek[0])
        if e is not None:
            return NormalizationError(
                e.type,
                # post_checks are called on a single label and need an offset
                start=label_offset + e.start if e.start is not None else None,
                disallowed=e.disallowed,
                suggested=e.suggested,
            )
        label_offset += len(label) + 1

    return None


def analyze_normalization_reason(tokens: List[Token]) -> Optional[NormalizationError]:
    error = None
    start = 0
    disallowed = None
    suggestion = None
    # find the first token that modified the input
    for tok in tokens:
        if tok.type == TY_MAPPED:
            error = NormalizationErrorType.NORM_ERR_MAPPED
            disallowed = chr(tok.cp)
            suggestion = cps2str(tok.cps)
            break
        elif tok.type == TY_IGNORED:
            error = NormalizationErrorType.NORM_ERR_IGNORED
            disallowed = chr(tok.cp)
            suggestion = ''
            break
        elif tok.type == TY_DISALLOWED:
            disallowed = chr(tok.cp)
            suggestion = ''
            if disallowed == '\u200d' or disallowed == '\u200c':
                error = NormalizationErrorType.NORM_ERR_INVISIBLE
            else:
                error = NormalizationErrorType.NORM_ERR_DISALLOWED
            break
        elif tok.type == TY_EMOJI:
            if tok.input != tok.cps:
                error = NormalizationErrorType.NORM_ERR_FE0F
                disallowed = cps2str(tok.input)
                suggestion = cps2str(tok.cps)
                break
            else:
                start += len(tok.input)
        elif tok.type == TY_NFC:
            error = NormalizationErrorType.NORM_ERR_NFC
            disallowed = cps2str(tok.input)
            suggestion = cps2str(tok.cps)
            break
        elif tok.type == TY_VALID:
            start += len(tok.cps)
        else:  # TY_STOP
            start += 1
    if error is not None:
        return NormalizationError(error, start, disallowed, suggestion)
    return None


def tokens2str(tokens: List[Token], emoji_fn: Callable[[TokenEmoji], str] = lambda tok: cps2str(tok.cps)) -> str:
    t = []
    for tok in tokens:
        if tok.type in (TY_IGNORED, TY_DISALLOWED):
            continue
        elif tok.type == TY_EMOJI:
            t.append(emoji_fn(tok))
        elif tok.type in (TY_ISOLATED, TY_STOP):
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

        for i in range(label_start, label_end):
            tok = tokens[i]
            if tok.type in (TY_IGNORED, TY_DISALLOWED):
                continue
            elif tok.type == TY_EMOJI:
                s.append(cps2str(tok.emoji))
            elif tok.type in (TY_ISOLATED, TY_STOP):
                s.append(chr(tok.cp))
            else:
                if not label_is_greek[label_index]:
                    s.append(cps2str([CP_XI_CAPITAL if cp == CP_XI_SMALL else cp for cp in tok.cps]))
                else:
                    s.append(cps2str(tok.cps))

        label_start = i + 1
        label_index += 1

    return ''.join(s)


def ens_process(input: str,
                do_normalize: bool = False,
                do_beautify: bool = False,
                do_tokenize: bool = False,
                do_reason: bool = False) -> ENSProcessResult:
    tokens: List[Token] = []
    err_fatal = None

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

        err_fatal = err_fatal or NormalizationError(
            NormalizationErrorType.NORM_ERR_INVISIBLE
            if c in ('\u200d', '\u200c')
            else NormalizationErrorType.NORM_ERR_DISALLOWED,
            start=input_cur - 1,
            disallowed=c,
            suggested='',
        )

        tokens.append(TokenDisallowed(
            cp = cp,
        ))

    tokens = normalize_tokens(tokens)

    try:
        err_soft = analyze_normalization_reason(tokens) if do_reason else None

        emojis_as_fe0f = ''.join(tokens2str(tokens, lambda _: '\uFE0F'))
        # true for each label that is greek
        # will be set by post_check()
        label_is_greek = []
        err_fatal = err_fatal or offset_err_start(post_check(emojis_as_fe0f, label_is_greek), tokens)

        err_soft = err_fatal or err_soft
        is_fatal = err_fatal is not None

        if is_fatal:
            normalized = None
            beautified = None
        else:
            normalized = tokens2str(tokens) if do_normalize else None
            beautified = tokens2beautified(tokens, label_is_greek) if do_beautify else None

        return ENSProcessResult(normalized, beautified, tokens, err_soft, is_fatal)
    except:
        e = NormalizationError(
            NormalizationErrorType.NORM_ERR_OTHER,
            start=None,
            disallowed=None,
            suggested=None,
        )
        return ENSProcessResult(None, None, tokens, e, True)


def offset_err_start(err: Optional[NormalizationError], tokens: List[Token]) -> Optional[NormalizationError]:
    '''
    Output of post_check() is not input aligned.
    This function offsets the error start to match the input characters.
    '''
    if err is None or err.start is None:
        return err
    # index in string that was scanned
    i = 0
    # offset between input and scanned
    offset = 0
    for tok in tokens:
        if i >= err.start:
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
    return NormalizationError(
        err.type,
        start=err.start + offset,
        disallowed=err.disallowed,
        suggested=err.suggested,
    )


def ens_normalize(text: str) -> str:
    res = ens_process(text, do_normalize=True)
    if res.is_fatal:
        raise ValueError(res.error.message)
    return res.normalized


def ens_beautify(text: str) -> str:
    res = ens_process(text, do_beautify=True)
    if res.is_fatal:
        raise ValueError(res.error.message)
    return res.beautified


def ens_tokenize(input: str) -> List[Token]:
    return ens_process(input, do_tokenize=True).tokens


def is_ens_normalized(name: str) -> bool:
    try:
        return ens_normalize(name) == name
    except ValueError:
        return False
