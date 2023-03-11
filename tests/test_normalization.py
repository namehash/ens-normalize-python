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
            except ValueError:
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
            except ValueError as e:
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
    ('a_a', NormalizationErrorType.NORM_ERR_UNDERSCORE, 1, '_', ''),
    # --
    ('aa--a', NormalizationErrorType.NORM_ERR_HYPHEN, 2, '--', ''),
    # empty
    # TODO should this return empty string?
    ("", NormalizationErrorType.NORM_ERR_EMPTY, 0, "", ""),
    ("a..b", NormalizationErrorType.NORM_ERR_EMPTY, 2, '', ''),

    # combining mark at the beginning
    ('\u0327a', NormalizationErrorType.NORM_ERR_CM_START, 0, '\u0327', ''),
    ('\u0327\u0327', NormalizationErrorType.NORM_ERR_CM_START, 0, '\u0327', ''),
    # combining mark after emoji
    ('a👩🏿‍🦲\u0327\u0327', NormalizationErrorType.NORM_ERR_CM_EMOJI, len('a👩🏿‍🦲'), '\u0327', ''),

    # disallowed
    ('a?', NormalizationErrorType.NORM_ERR_DISALLOWED, 1, '?', ''),
    # disallowed/ignored invisible
    ('a\u200d', NormalizationErrorType.NORM_ERR_INVISIBLE, 1, '\u200d', ''),
    # ignored
    (f'a{chr(173)}', NormalizationWarningType.NORM_WARN_IGNORED, 1, chr(173), ''),  # invisible "soft hyphen"
    # mapped
    ('aA', NormalizationWarningType.NORM_WARN_MAPPED, 1, 'A', 'a'),
    # FE0F emoji
    ('a🚴‍♂️', NormalizationWarningType.NORM_WARN_FE0F, 1, '🚴‍♂️', '🚴‍♂'),
    # not NFC normalized
    ('aa\u0300b', NormalizationWarningType.NORM_WARN_NFC, 1, 'a\u0300', 'à'),

    # fenced
    # leading
    ("'ab", NormalizationErrorType.NORM_ERR_FENCED_LEADING, 0, "’", ""),
    # ("·ab", NormalizationErrorType.NORM_ERR_FENCED_LEADING, 0, "·", ""), # was disallowed
    ("⁄ab", NormalizationErrorType.NORM_ERR_FENCED_LEADING, 0, "⁄", ""),
    # multi
    ("a''b", NormalizationErrorType.NORM_ERR_FENCED_MULTI, 1, "’’", "’"),
    # ("a··b", NormalizationErrorType.NORM_ERR_FENCED_MULTI, 1, "··", "·"),
    ("a⁄⁄b", NormalizationErrorType.NORM_ERR_FENCED_MULTI, 1, "⁄⁄", "⁄"),
    ("a'⁄b", NormalizationErrorType.NORM_ERR_FENCED_MULTI, 1, "’⁄", "’"),
    # trailing
    ("ab'", NormalizationErrorType.NORM_ERR_FENCED_TRAILING, 2, "’", ""),
    # ("ab·", NormalizationErrorType.NORM_ERR_FENCED_TRAILING, 2, "·", ""),
    ("ab⁄", NormalizationErrorType.NORM_ERR_FENCED_TRAILING, 2, "⁄", ""),

    # confusables
    ('bitcoin.bitcοin.bi̇tcoin.bitсoin', NormalizationErrorType.NORM_ERR_CONF_MIXED, 12, 'ο', ''),
    ('0x.0χ.0х', NormalizationErrorType.NORM_ERR_CONF_WHOLE, None, None, None),

    # NSM
    ('-إؐؑؐ-.eth', NormalizationErrorType.NORM_ERR_NSM_REPEATED, None, None, None),
    ('-إؐؑؒؓؔ-.eth', NormalizationErrorType.NORM_ERR_NSM_TOO_MANY, None, None, None),
])
def test_ens_normalization_reason(label, error, start, disallowed, suggested):
    res = ens_process(label, do_warnings=True)
    if error is None:
        assert res.error is None
        assert len(res.warnings) == 0
    else:
        if isinstance(error, NormalizationWarningType):
            res_error = res.warnings[0]
        else:
            res_error = res.error
        assert res_error.type == error
        assert res_error.start == start
        assert res_error.disallowed == disallowed
        assert res_error.suggested == suggested


@pytest.mark.parametrize(
    'error_type, code',
    [
        (NormalizationErrorType.NORM_ERR_UNDERSCORE, 'NORM_ERR_UNDERSCORE'),
        (NormalizationErrorType.NORM_ERR_HYPHEN, 'NORM_ERR_HYPHEN'),
        (NormalizationErrorType.NORM_ERR_CM_START, 'NORM_ERR_CM_START'),
        (NormalizationErrorType.NORM_ERR_CM_EMOJI, 'NORM_ERR_CM_EMOJI'),
        (NormalizationErrorType.NORM_ERR_DISALLOWED, 'NORM_ERR_DISALLOWED'),
        (NormalizationErrorType.NORM_ERR_INVISIBLE, 'NORM_ERR_INVISIBLE'),
        (NormalizationWarningType.NORM_WARN_IGNORED, 'NORM_WARN_IGNORED'),
        (NormalizationWarningType.NORM_WARN_MAPPED, 'NORM_WARN_MAPPED'),
        (NormalizationWarningType.NORM_WARN_FE0F, 'NORM_WARN_FE0F'),
        (NormalizationWarningType.NORM_WARN_NFC, 'NORM_WARN_NFC'),
    ]
)
def test_normalization_error_type_code(error_type: NormalizationErrorType, code: str):
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
    assert ret.error.type == NormalizationErrorType.NORM_ERR_UNDERSCORE
    assert ret.error.start == len(text)
    assert ret.error.disallowed == '_'
    assert ret.error.suggested == ''


def test_ens_norm_error_pos_disallowed():
    t = 'abc.abc.abc👩🏿‍🦲.aa\u0300b.a¼b.a\xadb'
    ret = ens_process(t + '?')
    assert ret.error.type == NormalizationErrorType.NORM_ERR_DISALLOWED
    assert ret.error.start == len(t)
    assert ret.error.disallowed == '?'
    assert ret.error.suggested == ''


def test_ens_norm_error_pos_nfc():
    t = 'abc.abc.abc👩🏿‍🦲.ab.ab.ab'
    ret = ens_process(t + 'a\u0300', do_warnings=True)
    e = ret.warnings[0]
    assert e.type == NormalizationWarningType.NORM_WARN_NFC
    assert e.start == len(t)
    assert e.disallowed == 'a\u0300'
    assert e.suggested == 'à'


def test_ens_warnings_many():
    t = (
        f'a{chr(173)}' +
        'aA.' +
        'a🚴‍♂️' +
        'aa\u0300b'
    )

    warnings = ens_warnings(t)
    assert len(warnings) == 4

    e = warnings[0]
    assert e.type == NormalizationWarningType.NORM_WARN_IGNORED
    assert e.start == 1
    assert e.disallowed == chr(173)
    assert e.suggested == ''

    e = warnings[1]
    assert e.type == NormalizationWarningType.NORM_WARN_MAPPED
    assert e.start == 3
    assert e.disallowed == 'A'
    assert e.suggested == 'a'

    e = warnings[2]
    assert e.type == NormalizationWarningType.NORM_WARN_FE0F
    assert e.start == 6
    assert e.disallowed == '🚴‍♂️'
    assert e.suggested == '🚴‍♂'

    e = warnings[3]
    assert e.type == NormalizationWarningType.NORM_WARN_NFC
    assert e.start == 11
    assert e.disallowed == 'a\u0300'
    assert e.suggested == 'à'


def test_throws():
    t = 'a_b'

    with pytest.raises(NormalizationError) as e:
        ens_normalize(t)
    assert e.value.type == NormalizationErrorType.NORM_ERR_UNDERSCORE
    assert e.value.start == 1
    assert e.value.disallowed == '_'
    assert e.value.suggested == ''

    with pytest.raises(NormalizationError) as e:
        ens_beautify(t)
    assert e.value.type == NormalizationErrorType.NORM_ERR_UNDERSCORE
    assert e.value.start == 1
    assert e.value.disallowed == '_'
    assert e.value.suggested == ''

    with pytest.raises(NormalizationError) as e:
        ens_warnings(t)
    assert e.value.type == NormalizationErrorType.NORM_ERR_UNDERSCORE
    assert e.value.start == 1
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
    except NormalizationError as e:
        assert e.type == NormalizationErrorType.NORM_ERR_UNDERSCORE
        assert e.start == 1
        assert e.disallowed == '_'
        assert e.suggested == ''
        assert e.code == NormalizationErrorType.NORM_ERR_UNDERSCORE.code
        assert e.message == NormalizationErrorType.NORM_ERR_UNDERSCORE.message
        assert e.details == NormalizationErrorType.NORM_ERR_UNDERSCORE.details
        assert str(e) == e.message
        assert repr(e) == 'NormalizationError(code=NORM_ERR_UNDERSCORE, modification="_"->"")'


def test_pickle_cache():
    pickle_path = os.path.join(os.path.expanduser('~'), '.cache', 'ens_normalize', 'normalization_data.pkl')
    if os.path.exists(pickle_path):
        os.remove(pickle_path)
    # initial load
    ens_normalize_module.normalization.load_normalization_data()
    # load from cache
    ens_normalize_module.normalization.load_normalization_data()


def test_ens_force_normalize():
    assert ens_force_normalize('Ab') == 'ab'
    assert ens_force_normalize('a_b') == 'ab'
    assert ens_force_normalize('a\'\'b') == 'a’b'
    assert ens_force_normalize('bitcoin.bitcοin.bi̇tcoin') == 'bitcoin.bitcin.bitcoin'
    with pytest.raises(NormalizationError) as e:
        ens_force_normalize('0x.0χ.0х')
    assert e.value.type == NormalizationErrorType.NORM_ERR_CONF_WHOLE
    with pytest.raises(NormalizationError) as e:
        ens_force_normalize('?')
    assert e.value.type == NormalizationErrorType.NORM_ERR_EMPTY
    for name in ('abc.?', 'abc.?.xyz', '?.xyz', 'abc..?.xyz'):
        with pytest.raises(NormalizationError) as e:
            ens_force_normalize(name)
        assert e.value.type == NormalizationErrorType.NORM_ERR_EMPTY
