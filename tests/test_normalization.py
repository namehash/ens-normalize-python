import pytest
import json
import os
from ens_normalize import *
import ens_normalize as ens_normalize_module


TESTS_PATH = os.path.join(os.path.dirname(__file__), 'ens-normalize-tests.json')


@pytest.mark.parametrize(
    'fn,field',
    [
        (ens_normalize, 'norm'),
        (ens_beautify, 'beautified'),
    ]
)
def test_ens_normalize_full(fn, field):
    with open(TESTS_PATH) as f:
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
            except DisallowedNameError:
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
            except DisallowedNameError as e:
                bad += 1
                print(f'! "{name}" threw "{e}"')

    assert bad == 0, f'{100 * good / (good + bad):.2f}%, {bad} failing'


def test_ens_beautify_xi():
    assert ens_beautify('ξabc') == 'Ξabc'
    assert ens_beautify('ξλφα') == 'ξλφα'
    assert ens_beautify('ξabc.ξλφα.ξabc.ξλφα') == 'Ξabc.ξλφα.Ξabc.ξλφα'


def test_ens_tokenize_full():
    with open(TESTS_PATH) as f:
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


@pytest.mark.parametrize('label,error,start,disallowed,suggested', [
    ('good', None, None, None, None),

    # underscore
    ('a_a', CurableErrorType.UNDERSCORE, 1, '_', ''),
    # --
    ('aa--a', CurableErrorType.HYPHEN, 2, '--', ''),
    # empty
    # TODO should this return empty string?
    ("", DisallowedNameErrorType.EMPTY_NAME, 0, "", ""),
    ("a..b", DisallowedNameErrorType.EMPTY_NAME, 2, '', ''),

    # combining mark at the beginning
    ('\u0327a', CurableErrorType.CM_START, 0, '\u0327', ''),
    ('\u0327\u0327', CurableErrorType.CM_START, 0, '\u0327', ''),
    # combining mark after emoji
    ('a👩🏿‍🦲\u0327\u0327', CurableErrorType.CM_EMOJI, len('a👩🏿‍🦲'), '\u0327', ''),

    # disallowed
    ('a?', CurableErrorType.DISALLOWED, 1, '?', ''),
    # disallowed/ignored invisible
    ('a\u200d', CurableErrorType.INVISIBLE, 1, '\u200d', ''),
    # ignored
    (f'a{chr(173)}', NormalizationTransformationType.IGNORED, 1, chr(173), ''),  # invisible "soft hyphen"
    # mapped
    ('aA', NormalizationTransformationType.MAPPED, 1, 'A', 'a'),
    # FE0F emoji
    ('a🚴‍♂️', NormalizationTransformationType.FE0F, 1, '🚴‍♂️', '🚴‍♂'),
    # not NFC normalized
    ('aa\u0300b', NormalizationTransformationType.NFC, 1, 'a\u0300', 'à'),

    # fenced
    # leading
    ("'ab", CurableErrorType.FENCED_LEADING, 0, "’", ""),
    # ("·ab", CurableErrorType.FENCED_LEADING, 0, "·", ""), # was disallowed
    ("⁄ab", CurableErrorType.FENCED_LEADING, 0, "⁄", ""),
    # multi
    ("a''b", CurableErrorType.FENCED_MULTI, 1, "’’", "’"),
    # ("a··b", CurableErrorType.FENCED_MULTI, 1, "··", "·"),
    ("a⁄⁄b", CurableErrorType.FENCED_MULTI, 1, "⁄⁄", "⁄"),
    ("a'⁄b", CurableErrorType.FENCED_MULTI, 1, "’⁄", "’"),
    # trailing
    ("ab'", CurableErrorType.FENCED_TRAILING, 2, "’", ""),
    # ("ab·", CurableErrorType.FENCED_TRAILING, 2, "·", ""),
    ("ab⁄", CurableErrorType.FENCED_TRAILING, 2, "⁄", ""),

    # confusables
    ('bitcoin.bitcοin.bi̇tcoin.bitсoin', CurableErrorType.CONF_MIXED, 12, 'ο', ''),
    ('0x.0χ.0х', DisallowedNameErrorType.CONF_WHOLE, None, None, None),

    # NSM
    ('-إؐؑؐ-.eth', DisallowedNameErrorType.NSM_REPEATED, None, None, None),
    ('-إؐؑؒؓؔ-.eth', DisallowedNameErrorType.NSM_TOO_MANY, None, None, None),
])
def test_ens_normalization_reason(label, error, start, disallowed, suggested):
    res = ens_process(label, do_transformations=True)
    if error is None:
        assert res.error is None
        assert len(res.transformations) == 0
    else:
        if isinstance(error, NormalizationTransformationType):
            res_error = res.transformations[0]
        else:
            res_error = res.error
        assert res_error.type == error
        if isinstance(error, CurableError):
            assert res_error.index == start
            assert res_error.disallowed == disallowed
            assert res_error.suggested == suggested


@pytest.mark.parametrize(
    'error_type, code',
    [
        (CurableErrorType.UNDERSCORE, 'UNDERSCORE'),
        (CurableErrorType.HYPHEN, 'HYPHEN'),
        (CurableErrorType.CM_START, 'CM_START'),
        (CurableErrorType.CM_EMOJI, 'CM_EMOJI'),
        (CurableErrorType.DISALLOWED, 'DISALLOWED'),
        (CurableErrorType.INVISIBLE, 'INVISIBLE'),
        (NormalizationTransformationType.IGNORED, 'IGNORED'),
        (NormalizationTransformationType.MAPPED, 'MAPPED'),
        (NormalizationTransformationType.FE0F, 'FE0F'),
        (NormalizationTransformationType.NFC, 'NFC'),
    ]
)
def test_normalization_error_type_code(error_type: DisallowedNameErrorType, code: str):
    assert error_type.code == code


@pytest.mark.parametrize('text', [
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
])
def test_ens_norm_error_pos(text):
    ret = ens_process(text + '_')
    assert ret.cure.type == CurableErrorType.UNDERSCORE
    assert ret.cure.index == len(text)
    assert ret.cure.disallowed == '_'
    assert ret.cure.suggested == ''


def test_ens_norm_error_pos_disallowed():
    t = 'abc.abc.abc👩🏿‍🦲.aa\u0300b.a¼b.a\xadb'
    ret = ens_process(t + '?')
    assert ret.cure.type == CurableErrorType.DISALLOWED
    assert ret.cure.index == len(t)
    assert ret.cure.disallowed == '?'
    assert ret.cure.suggested == ''


def test_ens_norm_error_pos_nfc():
    t = 'abc.abc.abc👩🏿‍🦲.ab.ab.ab'
    ret = ens_process(t + 'a\u0300', do_transformations=True)
    e = ret.transformations[0]
    assert e.type == NormalizationTransformationType.NFC
    assert e.index == len(t)
    assert e.disallowed == 'a\u0300'
    assert e.suggested == 'à'


def test_ens_warnings_many():
    t = (
        f'a{chr(173)}' +
        'aA.' +
        'a🚴‍♂️' +
        'aa\u0300b'
    )

    warnings = ens_transformations(t)
    assert len(warnings) == 4

    e = warnings[0]
    assert e.type == NormalizationTransformationType.IGNORED
    assert e.index == 1
    assert e.disallowed == chr(173)
    assert e.suggested == ''

    e = warnings[1]
    assert e.type == NormalizationTransformationType.MAPPED
    assert e.index == 3
    assert e.disallowed == 'A'
    assert e.suggested == 'a'

    e = warnings[2]
    assert e.type == NormalizationTransformationType.FE0F
    assert e.index == 6
    assert e.disallowed == '🚴‍♂️'
    assert e.suggested == '🚴‍♂'

    e = warnings[3]
    assert e.type == NormalizationTransformationType.NFC
    assert e.index == 11
    assert e.disallowed == 'a\u0300'
    assert e.suggested == 'à'


def test_throws():
    t = 'a_b'

    with pytest.raises(CurableError) as e:
        ens_normalize(t)
    assert e.value.type == CurableErrorType.UNDERSCORE
    assert e.value.index == 1
    assert e.value.disallowed == '_'
    assert e.value.suggested == ''

    with pytest.raises(CurableError) as e:
        ens_beautify(t)
    assert e.value.type == CurableErrorType.UNDERSCORE
    assert e.value.index == 1
    assert e.value.disallowed == '_'
    assert e.value.suggested == ''

    with pytest.raises(CurableError) as e:
        ens_transformations(t)
    assert e.value.type == CurableErrorType.UNDERSCORE
    assert e.value.index == 1
    assert e.value.disallowed == '_'
    assert e.value.suggested == ''


def test_ens_is_normalized():
    assert is_ens_normalized('a')
    assert not is_ens_normalized('a_b')
    assert not is_ens_normalized('Abc')
    assert not is_ens_normalized('')


def test_normalization_error_object():
    t = 'a_b'
    try:
        ens_normalize(t)
    except CurableError as e:
        assert e.type == CurableErrorType.UNDERSCORE
        assert e.index == 1
        assert e.disallowed == '_'
        assert e.suggested == ''
        assert e.code == CurableErrorType.UNDERSCORE.code
        assert e.general_info == CurableErrorType.UNDERSCORE.general_info
        assert e.disallowed_sequence_info == CurableErrorType.UNDERSCORE.disallowed_sequence_info
        assert str(e) == e.general_info
        assert repr(e) == 'CurableError(code="UNDERSCORE", index=1, disallowed="_", suggested="")'


def test_error_is_exception():
    with pytest.raises(Exception):
        ens_normalize('')


def test_str_repr():
    e = ens_process('a_').cure

    assert str(e) == CurableErrorType.UNDERSCORE.general_info
    assert repr(e) == 'CurableError(code="UNDERSCORE", index=1, disallowed="_", suggested="")'


def test_pickle_cache():
    pickle_path = os.path.join(os.path.expanduser('~'), '.cache', 'ens_normalize', 'normalization_data.pkl')
    if os.path.exists(pickle_path):
        os.remove(pickle_path)
    # initial load
    ens_normalize_module.normalization.load_normalization_data()
    # load from cache
    ens_normalize_module.normalization.load_normalization_data()


def test_ens_cure():
    assert ens_cure('Ab') == 'ab'
    assert ens_cure('a_b') == 'ab'
    assert ens_cure('a\'\'b') == 'a’b'
    assert ens_cure('bitcoin.bitcοin.bi̇tcoin') == 'bitcoin.bitcin.bitcoin'
    with pytest.raises(DisallowedNameError) as e:
        ens_cure('0x.0χ.0х')
    assert e.value.type == DisallowedNameErrorType.CONF_WHOLE
    with pytest.raises(DisallowedNameError) as e:
        ens_cure('?')
    assert e.value.type == DisallowedNameErrorType.EMPTY_NAME
    for name in ('abc.?', 'abc.?.xyz', '?.xyz', 'abc..?.xyz'):
        with pytest.raises(DisallowedNameError) as e:
            ens_cure(name)
        assert e.value.type == DisallowedNameErrorType.EMPTY_NAME
