import pytest
import json
import os
from ens_normalize import (
    ens_process,
    ens_normalize,
    ens_cure,
    ens_beautify,
    ens_tokenize,
    ens_normalizations,
    is_ens_normalized,
    is_ens_normalizable,
    DisallowedSequence,
    DisallowedSequenceType,
    CurableSequence,
    CurableSequenceType,
    NormalizableSequenceType,
)
import ens_normalize as ens_normalize_module
import warnings
import pickle
import pickletools


TESTS_PATH = os.path.join(os.path.dirname(__file__), 'ens-normalize-tests.json')


@pytest.mark.parametrize(
    'fn,field',
    [
        (ens_normalize, 'norm'),
        (ens_beautify, 'beautified'),
    ],
)
def test_ens_normalize_full(fn, field):
    with open(TESTS_PATH, encoding='utf-8') as f:
        data = json.load(f)

    good = 0
    bad = 0

    for test in data:
        name = test['name']

        if 'error' in test:
            try:
                fn(name)
                bad += 1
                print(f'! "{name}" did not throw "{test["comment"]}"')
            except DisallowedSequence:
                good += 1
        else:
            test['norm'] = test.get('norm', name)
            expected = test[field]

            try:
                actual = fn(name)
                if actual == expected:
                    good += 1
                else:
                    bad += 1
                    print(f'! "{name}" -> "{actual}" != "{expected}"')
            except DisallowedSequence as e:
                bad += 1
                print(f'! "{name}" threw "{e}"')

    assert bad == 0, f'{100 * good / (good + bad):.2f}%, {bad} failing'


def test_ens_beautify_xi():
    assert ens_beautify('ξabc') == 'Ξabc'
    assert ens_beautify('ξλφα') == 'ξλφα'
    assert ens_beautify('ξabc.ξλφα.ξabc.ξλφα') == 'Ξabc.ξλφα.Ξabc.ξλφα'


def test_ens_tokenize_full():
    with open(TESTS_PATH, encoding='utf-8') as f:
        data = json.load(f)

    good = 0
    bad = 0

    for test in data:
        if 'tokenized' not in test:
            continue

        name = test['name']
        expected = test['tokenized']

        # we do not keep track of which tokens were changed
        for t in expected:
            if t['type'] == 'nfc':
                del t['tokens']
                del t['tokens0']

        res = [t._asdict() for t in ens_tokenize(name)]

        if res == expected:
            good += 1
        else:
            bad += 1
            print(f'! "{name}" tokenized incorrectly')

    assert bad == 0, f'{100 * good / (good + bad):.2f}%, {bad} failing'


@pytest.mark.parametrize(
    'label,error,start,disallowed,suggested',
    [
        ('good', None, None, None, None),
        # underscore
        ('a_a', CurableSequenceType.UNDERSCORE, 1, '_', ''),
        # --
        ('aa--a', CurableSequenceType.HYPHEN, 2, '--', ''),
        # empty
        ('a..b', CurableSequenceType.EMPTY_LABEL, 1, '..', '.'),
        ('.ab', CurableSequenceType.EMPTY_LABEL, 0, '.', ''),
        ('ab.', CurableSequenceType.EMPTY_LABEL, 2, '.', ''),
        # combining mark at the beginning
        ('\u0327a', CurableSequenceType.CM_START, 0, '\u0327', ''),
        ('\u0327\u0327', CurableSequenceType.CM_START, 0, '\u0327', ''),
        # combining mark after emoji
        ('a👩🏿‍🦲\u0327\u0327', CurableSequenceType.CM_EMOJI, len('a👩🏿‍🦲'), '\u0327', ''),
        # disallowed
        ('a?', CurableSequenceType.DISALLOWED, 1, '?', ''),
        # disallowed/ignored invisible
        ('a\u200d', CurableSequenceType.INVISIBLE, 1, '\u200d', ''),
        # ignored
        (f'a{chr(173)}', NormalizableSequenceType.IGNORED, 1, chr(173), ''),  # invisible "soft hyphen"
        # mapped
        ('aA', NormalizableSequenceType.MAPPED, 1, 'A', 'a'),
        # FE0F emoji
        ('a🚴‍♂️', NormalizableSequenceType.FE0F, 1, '🚴‍♂️', '🚴‍♂'),
        # not NFC normalized
        ('aa\u0300b', NormalizableSequenceType.NFC, 1, 'a\u0300', 'à'),
        # fenced
        # leading
        ("'ab", CurableSequenceType.FENCED_LEADING, 0, '’', ''),
        # ("·ab", CurableSequenceType.FENCED_LEADING, 0, "·", ""), # was disallowed
        ('⁄ab', CurableSequenceType.FENCED_LEADING, 0, '⁄', ''),
        # multi
        ("a''b", CurableSequenceType.FENCED_MULTI, 1, '’’', '’'),
        # ("a··b", CurableSequenceType.FENCED_MULTI, 1, "··", "·"),
        ('a⁄⁄b', CurableSequenceType.FENCED_MULTI, 1, '⁄⁄', '⁄'),
        ("a'⁄b", CurableSequenceType.FENCED_MULTI, 1, '’⁄', '’'),
        # trailing
        ("ab'", CurableSequenceType.FENCED_TRAILING, 2, '’', ''),
        # ("ab·", CurableSequenceType.FENCED_TRAILING, 2, "·", ""),
        ('ab⁄', CurableSequenceType.FENCED_TRAILING, 2, '⁄', ''),
        # confusables
        ('bitcoin.bitcοin.bi̇tcoin.bitсoin', CurableSequenceType.CONF_MIXED, 12, 'ο', ''),
        ('0x.0χ.0х', DisallowedSequenceType.CONF_WHOLE, None, None, None),
        # NSM
        ('-إؐؑؐ-.eth', DisallowedSequenceType.NSM_REPEATED, None, None, None),
        ('-إؐؑؒؓؔ-.eth', DisallowedSequenceType.NSM_TOO_MANY, None, None, None),
    ],
)
def test_ens_normalization_reason(label, error, start, disallowed, suggested):
    res = ens_process(label, do_normalizations=True)
    if error is None:
        assert res.error is None
        assert len(res.normalizations) == 0
    else:
        if isinstance(error, NormalizableSequenceType):
            res_error = res.normalizations[0]
        else:
            res_error = res.error
        assert res_error.type == error
        if isinstance(error, CurableSequence):
            assert res_error.index == start
            assert res_error.sequence == disallowed
            assert res_error.suggested == suggested


@pytest.mark.parametrize(
    'error_type, code',
    [
        (CurableSequenceType.UNDERSCORE, 'UNDERSCORE'),
        (CurableSequenceType.HYPHEN, 'HYPHEN'),
        (CurableSequenceType.CM_START, 'CM_START'),
        (CurableSequenceType.CM_EMOJI, 'CM_EMOJI'),
        (CurableSequenceType.DISALLOWED, 'DISALLOWED'),
        (CurableSequenceType.INVISIBLE, 'INVISIBLE'),
        (NormalizableSequenceType.IGNORED, 'IGNORED'),
        (NormalizableSequenceType.MAPPED, 'MAPPED'),
        (NormalizableSequenceType.FE0F, 'FE0F'),
        (NormalizableSequenceType.NFC, 'NFC'),
    ],
)
def test_normalization_error_type_code(error_type: DisallowedSequenceType, code: str):
    assert error_type.code == code


@pytest.mark.parametrize(
    'text',
    [
        # multi char emoji
        'abc👩🏿‍🦲',
        # NFC
        'aa\u0300b',
        # mapped
        'a¼b'
        # ignored
        'a\xadb',
        # multi label
        'abc.abc.abc.abc',
        'abc.abc.abc👩🏿‍🦲.aa\u0300b.a¼b.a\xadb',
    ],
)
def test_ens_norm_error_pos(text):
    ret = ens_process(text + '_')
    assert ret.error.type == CurableSequenceType.UNDERSCORE
    assert ret.error.index == len(text)
    assert ret.error.sequence == '_'
    assert ret.error.suggested == ''


def test_ens_norm_error_pos_disallowed():
    t = 'abc.abc.abc👩🏿‍🦲.aa\u0300b.a¼b.a\xadb'
    ret = ens_process(t + '?')
    assert ret.error.type == CurableSequenceType.DISALLOWED
    assert ret.error.index == len(t)
    assert ret.error.sequence == '?'
    assert ret.error.suggested == ''


def test_ens_norm_error_pos_nfc():
    t = 'abc.abc.abc👩🏿‍🦲.ab.ab.ab'
    ret = ens_process(t + 'a\u0300', do_normalizations=True)
    e = ret.normalizations[0]
    assert e.type == NormalizableSequenceType.NFC
    assert e.index == len(t)
    assert e.sequence == 'a\u0300'
    assert e.suggested == 'à'


def test_ens_warnings_many():
    t = f'a{chr(173)}' + 'aA.' + 'a🚴‍♂️' + 'aa\u0300b'

    warnings = ens_normalizations(t)
    assert len(warnings) == 4

    e = warnings[0]
    assert e.type == NormalizableSequenceType.IGNORED
    assert e.index == 1
    assert e.sequence == chr(173)
    assert e.suggested == ''

    e = warnings[1]
    assert e.type == NormalizableSequenceType.MAPPED
    assert e.index == 3
    assert e.sequence == 'A'
    assert e.suggested == 'a'

    e = warnings[2]
    assert e.type == NormalizableSequenceType.FE0F
    assert e.index == 6
    assert e.sequence == '🚴‍♂️'
    assert e.suggested == '🚴‍♂'

    e = warnings[3]
    assert e.type == NormalizableSequenceType.NFC
    assert e.index == 11
    assert e.sequence == 'a\u0300'
    assert e.suggested == 'à'


def test_throws():
    t = 'a_b'

    with pytest.raises(CurableSequence) as e:
        ens_normalize(t)
    assert e.value.type == CurableSequenceType.UNDERSCORE
    assert e.value.index == 1
    assert e.value.sequence == '_'
    assert e.value.suggested == ''

    with pytest.raises(CurableSequence) as e:
        ens_beautify(t)
    assert e.value.type == CurableSequenceType.UNDERSCORE
    assert e.value.index == 1
    assert e.value.sequence == '_'
    assert e.value.suggested == ''

    with pytest.raises(CurableSequence) as e:
        ens_normalizations(t)
    assert e.value.type == CurableSequenceType.UNDERSCORE
    assert e.value.index == 1
    assert e.value.sequence == '_'
    assert e.value.suggested == ''


def test_ens_is_normalized():
    assert is_ens_normalized('a')
    assert not is_ens_normalized('a_b')
    assert not is_ens_normalized('Abc')
    assert is_ens_normalized('')


def test_normalization_error_object():
    t = 'a_b'
    try:
        ens_normalize(t)
    except CurableSequence as e:
        assert e.type == CurableSequenceType.UNDERSCORE
        assert e.index == 1
        assert e.sequence == '_'
        assert e.suggested == ''
        assert e.code == CurableSequenceType.UNDERSCORE.code
        assert e.general_info == CurableSequenceType.UNDERSCORE.general_info
        assert e.sequence_info == CurableSequenceType.UNDERSCORE.sequence_info
        assert str(e) == e.general_info
        assert repr(e) == 'CurableSequence(code="UNDERSCORE", index=1, sequence="_", suggested="")'
    try:
        ens_normalize('0х0')
    except DisallowedSequence as e:
        assert e.type == DisallowedSequenceType.CONF_WHOLE
        assert e.code == DisallowedSequenceType.CONF_WHOLE.code
        assert e.general_info == DisallowedSequenceType.CONF_WHOLE.general_info.format(
            script1='Cyrillic', script2='Latin'
        )
        assert str(e) == e.general_info
        assert repr(e) == 'DisallowedSequence(code="CONF_WHOLE")'


def test_error_is_exception():
    with pytest.raises(Exception):
        ens_normalize('0х0')


def test_str_repr():
    e = ens_process('a_').error

    assert str(e) == CurableSequenceType.UNDERSCORE.general_info
    assert repr(e) == 'CurableSequence(code="UNDERSCORE", index=1, sequence="_", suggested="")'


def test_ens_cure():
    assert ens_cure('Ab') == 'ab'
    assert ens_cure('a_b') == 'ab'
    assert ens_cure("a''b") == 'a’b'
    assert ens_cure('bitcoin.bitcοin.bi̇tcoin') == 'bitcoin.bitcin.bitcoin'
    with pytest.raises(DisallowedSequence) as e:
        ens_cure('0x.0χ.0х')
    assert e.value.type == DisallowedSequenceType.CONF_WHOLE
    assert ens_cure('?') == ''
    assert ens_cure('abc.?') == 'abc'
    assert ens_cure('abc.?.xyz') == 'abc.xyz'
    assert ens_cure('?.xyz') == 'xyz'
    assert ens_cure('abc..?.xyz') == 'abc.xyz'


def test_ens_process_cure():
    ret = ens_process('a_..b', do_cure=True)
    assert ret.cured == 'a.b'
    assert [e.code for e in ret.cures] == ['EMPTY_LABEL', 'UNDERSCORE']
    ret = ens_process('', do_cure=True)
    assert ret.cured == ''
    assert ret.cures == []
    ret = ens_process('0х0', do_cure=True)
    assert ret.cured is None
    assert ret.cures is None


def test_error_meta():
    # mixed
    e: CurableSequence = ens_process('bitcoin.bitcοin.bi̇tcoin.bitсoin').error
    assert e.general_info == 'Contains visually confusing characters from multiple scripts (Greek/Latin)'
    assert (
        e.sequence_info
        == 'This character from the Greek script is disallowed because it is visually confusing with another character from the Latin script'
    )
    assert e.sequence == 'ο'

    # whole
    e = ens_process('0x.0χ.0х').error
    assert e.general_info == 'Contains visually confusing characters from Cyrillic and Latin scripts'


@pytest.mark.skip(reason='there are no such characters anymore')
def test_error_meta_other_scripts():
    # unknown script for character
    c = chr(771)
    e: CurableSequence = ens_process(f'bitcoin.bitcin.bi̇tcin.bitсin{c}').error
    assert e.general_info == 'Contains visually confusing characters from multiple scripts (Latin plus other scripts)'
    assert (
        e.sequence_info
        == 'This character is disallowed because it is visually confusing with another character from the Latin script'
    )


def test_unicode_version_check(mocker):
    mocker.patch('ens_normalize.normalization.UNICODE_VERSION', '15.0.1')
    warnings.filterwarnings('error')
    with pytest.raises(UnicodeWarning, match=r'Unicode version mismatch'):
        ens_normalize_module.normalization.check_spec_unicode_version()


def test_ens_cure_max_iters(mocker):
    mocker.patch('ens_normalize.normalization.ens_normalize', lambda _: ens_normalize('?'))
    with pytest.raises(Exception, match=r'ens_cure\(\) exceeded max iterations'):
        ens_cure('???')


def test_data_creation():
    data = ens_normalize_module.normalization.NormalizationData(
        os.path.join(os.path.dirname(__file__), '..', 'tools', 'updater', 'spec.json')
    )
    buf1 = pickletools.optimize(pickle.dumps(data, protocol=5))
    with open(ens_normalize_module.normalization.SPEC_PICKLE_PATH, 'rb') as f:
        buf2 = f.read()
    assert buf1 == buf2


def test_empty_name():
    assert ens_normalize('') == ''
    assert ens_beautify('') == ''
    assert ens_tokenize('') == []
    assert ens_cure('') == ''


def test_ignorable_name():
    assert ens_process('').error is None
    e = ens_process('\ufe0f\ufe0f').error
    assert e.type == CurableSequenceType.EMPTY_LABEL
    assert e.index == 0
    assert e.sequence == '\ufe0f\ufe0f'


def test_is_normalizable():
    assert is_ens_normalizable('nick.eth')
    assert not is_ens_normalizable('ni_ck.eth')
    assert is_ens_normalizable('')


def test_simple_name_optimization():
    r = ens_process(
        'abc123.eth',
        do_normalize=False,
        do_beautify=False,
        do_tokenize=False,
        do_normalizations=False,
        do_cure=False,
    )
    assert r.normalized is None
    assert r.beautified is None
    assert r.tokens is None
    assert r.cured is None
    assert r.cures is None
    assert r.error is None
    assert r.normalizations is None

    r = ens_process(
        'abc123.eth',
        do_normalize=True,
        do_beautify=False,
        do_tokenize=False,
        do_normalizations=False,
        do_cure=False,
    )
    assert r.normalized == 'abc123.eth'
    assert r.beautified is None
    assert r.tokens is None
    assert r.cured is None
    assert r.cures is None
    assert r.error is None
    assert r.normalizations is None

    r = ens_process(
        'abc123.eth',
        do_normalize=False,
        do_beautify=True,
        do_tokenize=False,
        do_normalizations=False,
        do_cure=False,
    )
    assert r.normalized is None
    assert r.beautified == 'abc123.eth'
    assert r.tokens is None
    assert r.cured is None
    assert r.cures is None
    assert r.error is None
    assert r.normalizations is None

    r = ens_process(
        'abc123.eth',
        do_normalize=False,
        do_beautify=False,
        do_tokenize=True,
        do_normalizations=False,
        do_cure=False,
    )
    assert r.normalized is None
    assert r.beautified is None
    assert r.tokens is not None
    assert r.cured is None
    assert r.cures is None
    assert r.error is None
    assert r.normalizations is None

    r = ens_process(
        'abc123.eth',
        do_normalize=False,
        do_beautify=False,
        do_tokenize=False,
        do_normalizations=True,
        do_cure=False,
    )

    assert r.normalized is None
    assert r.beautified is None
    assert r.tokens is None
    assert r.cured is None
    assert r.cures is None
    assert r.error is None
    assert r.normalizations is not None
    assert len(r.normalizations) == 0

    r = ens_process(
        'abc123.eth',
        do_normalize=False,
        do_beautify=False,
        do_tokenize=False,
        do_normalizations=False,
        do_cure=True,
    )
    assert r.normalized is None
    assert r.beautified is None
    assert r.tokens is None
    assert r.cured == 'abc123.eth'
    assert r.cures is not None
    assert len(r.cures) == 0
    assert r.error is None
    assert r.normalizations is None


@pytest.mark.parametrize(
    'input_str, expected_code, expected_index, expected_sequence, expected_suggested',
    [
        ('nick.\ufe0f\ufe0f.eth', 'EMPTY_LABEL', 4, '.\ufe0f\ufe0f.', '.'),
        ('01\ufe0f--345', 'HYPHEN', 3, '--', ''),
        ('01-\ufe0f-345', 'HYPHEN', 2, '-\ufe0f-', ''),
        ("\ufe0f'b", 'FENCED_LEADING', 1, '’', ''),
    ],
)
def test_suggestions_with_ignored(input_str, expected_code, expected_index, expected_sequence, expected_suggested):
    e = ens_process(input_str).error
    assert e.code == expected_code
    assert e.index == expected_index
    assert e.sequence == expected_sequence
    assert e.suggested == expected_suggested
