# ENS Normalize Python

![Tests](https://github.com/namehash/ens-normalize-python/actions/workflows/python-app.yml/badge.svg?branch=main)
![PyPI](https://img.shields.io/pypi/v/ens-normalize)
![Coverage](https://raw.githubusercontent.com/namehash/ens-normalize-python/main/coverage_badge.svg)

* Python implementation of the [ENS Name Normalization Standard](https://github.com/adraffy/ensip-norm/blob/main/draft.md).
  Thanks to [Adraffy](https://github.com/adraffy) for his leadership in coordinating the definition of this standard with the ENS community.
* Passes **100%** of the [official validation tests](https://github.com/adraffy/ens-normalize.js/tree/main/validate) (validated automatically with pytest, see below).
* Passes an [additional suite of further tests](/tools/updater/update-ens.js#L54) for compatibility with the official [Javascript reference implementation](https://github.com/adraffy/ens-normalize.js) and code testing coverage.
* Based on [JavaScript implementation version 1.9.0](https://github.com/adraffy/ens-normalize.js/tree/4873fbe6393e970e186ab57860cc59cbbb1fa162).

## Glossary

* name - a full domain name, e.g. `nick.eth`
* label - a part of a name separated by a dot, e.g. `nick` and `eth` are labels in `nick.eth`
* normalized name - name that is already in normalized form according to the ENS Normalization Standard
* normalizable name - name that is normalized or that can be converted into a normalized name using `ens_normalize`
* disallowed name - name that is not normalized or normalizable
* curable name - name that may be disallowed but can still be converted into a normalized name using `ens_cure`
* fatal error - a `DisallowedNameError` object thrown by `ens_normalize` that contains only general information about the error and no possible fixes
* curable error - a `CurableError` object (inherits from `DisallowedNameError`) thrown by `ens_normalize` that contains information about a possible fix for the error

## Usage

The package is available on [pypi](https://pypi.org/project/ens-normalize/)

```bash
pip install ens-normalize
```

Normalize an ENS name:

```python
from ens_normalize import ens_normalize
# str -> str
# raises DisallowedNameError for disallowed names
# output ready for namehash
ens_normalize('Nick.ETH')
# 'nick.eth'
# note: does not enforce .eth TLD 3-character minimum
```

Inspect issues with names that cannot be normalized:

```python
from ens_normalize import DisallowedNameError
# added a hidden "zero width joiner" character
try:
    ens_normalize('Ni‍ck.ETH')
# Catch the first normalization error (the name we are attempting to normalize could have more than one error).
except DisallowedNameError as e:
    # error code
    print(e.code)
    # INVISIBLE

    # a message about why the input is disallowed
    print(e.general_info)
    # Contains a disallowed invisible character

    if isinstance(e, CurableError):
        # information about the disallowed substring
        print(e.disallowed_sequence_info)
        # 'This invisible character is disallowed'

        # starting index of the disallowed substring in the input string
        # (counting in Unicode code points)
        print(e.index)
        # 2

        # the disallowed substring
        # (use repr() to "see" the invisible character)
        print(repr(e.disallowed))
        # '\u200d'

        # a suggestion for fixing the first error (there might be more errors)
        print(repr(e.suggested))
        # ''
        # replacing the disallowed substring with this empty string represents that the disallowed substring should be removed

        # You may be able to fix this error by replacing e.disallowed
        # with e.suggested in the input string.
        # Fields index, disallowed_sequence_info, disallowed, and suggested are not None only for fixable errors.
        # Other errors might be found even after applying this suggestion.
```

You can attempt conversion of disallowed names into normalized names:

```python
from ens_normalize import ens_cure
# input name with disallowed zero width joiner and '?'
# str -> str
ens_cure('Ni‍ck?.ETH')
# 'nick.eth'
# ZWJ and '?' are removed, no error is raised
# note: this function is not a part of the ENS Normalization Standard

# note: might still raise DisallowedNameError for certain names, which cannot be cured, e.g.
ens_cure('?')
# DisallowedNameError: The name is empty
ens_cure('0χх0.eth')
# DisallowedNameError: Contains visually confusing characters that are disallowed
```

Format names with fully-qualified emoji:

```python
from ens_normalize import ens_beautify
# works like ens_normalize()
# output ready for display
ens_beautify('1⃣2⃣.eth')
# '1️⃣2️⃣.eth'

# note: normalization is unchanged:
# ens_normalize(ens_beautify(x)) == ens_normalize(x)
# note: in addition to beautifying emojis, ens_beautify converts the character 'ξ' (Greek lowercase 'Xi') to 'Ξ' (Greek uppercase 'Xi', a.k.a. the Ethereum symbol) in labels that contain no other Greek characters
```

Generate detailed label analysis:

```python
from ens_normalize import ens_tokenize
# str -> List[Token]
# always returns a tokenization of the input
ens_tokenize('Nàme‍🧙‍♂.eth')
# [TokenMapped(cp=78, cps=[110], type='mapped'),
#  TokenNFC(input=[97, 768], cps=[224], type='nfc'),
#  TokenValid(cps=[109, 101], type='valid'),
#  TokenDisallowed(cp=8205, type='disallowed'),
#  TokenEmoji(emoji=[129497, 8205, 9794, 65039],
#             input=[129497, 8205, 9794],
#             cps=[129497, 8205, 9794],
#             type='emoji'),
#  TokenStop(cp=46, type='stop'),
#  TokenValid(cps=[101, 116, 104], type='valid')]
```

For a normalizable name, you can find out how the input is transformed during normalization:

```python
from ens_normalize import ens_transformations
# Returns a list of transformations (substring -> string)
# that have been applied to the input during normalization.
# NormalizationTransformation has the same fields as CurableError:
# - code
# - general_info
# - disallowed_sequence_info
# - index
# - disallowed
# - suggested
ens_transformations('Nàme🧙‍♂️.eth')
# [NormalizationTransformation(code="MAPPED", index=0, disallowed="N", suggested="n"),
#  NormalizationTransformation(code="FE0F", index=4, disallowed="🧙‍♂️", suggested="🧙‍♂")]
```

An example normalization workflow:

```python
name = 'Nàme🧙‍♂️.eth'
try:
    normalized = ens_normalize(name)
    print('Normalized:', normalized)
    # Normalized: nàme🧙‍♂.eth
    # Success!

     # was the input transformed by the normalization process?
    if name != normalized:
        # Let's check how the input was changed:
        for t in ens_transformations(name):
            print(repr(t)) # use repr() to print more information
        # NormalizationTransformation(code="MAPPED", index=0, disallowed="N", suggested="n")
        # NormalizationTransformation(code="FE0F", index=4, disallowed="🧙‍♂️", suggested="🧙‍♂")
        #                              invisible character inside emoji ^
except DisallowedNameError as e:
    # Even if the name is invalid according to the ENS Normalization Standard,
    # we can try to automatically remove disallowed characters.
    try:
        print(ens_cure(name))
    except DisallowedLabelError as e:
        # The name cannot be automatically fixed.
        print('Fatal error:', e)
```

You can run many of the above functions at once. It is faster than running all of them sequentially.

```python
from ens_normalize import ens_process
# use only the do_* flags you need
ens_process("Nàme🧙‍♂️1⃣.eth",
    do_normalize=True,
    do_beautify=True,
    do_tokenize=True,
    do_transformations=True,
    do_cure=True,
)
# ENSProcessResult(
#   normalized='nàme🧙\u200d♂1⃣.eth',
#   beautified='nàme🧙\u200d♂️1️⃣.eth',
#   tokens=[...],
#   cured='nàme🧙\u200d♂1⃣.eth',
#   cures=[], # This is the list of cures that were applied to the input (in this case, none).
#   error=None, # This is the exception raised by ens_normalize().
#               # It is a DisallowedNameError or CurableError if the error is curable.
#   transformations=[
#     NormalizationTransformation(code="MAPPED", index=0, disallowed="N", suggested="n"),
#     NormalizationTransformation(code="FE0F", index=4, disallowed="🧙‍♂️", suggested="🧙‍♂")
#   ])
```

## List of all `DisallowedNameError` types

For fatal errors (not curable), it is challenging to communicate the normalization error as a problem with a specific substring.

| `DisallowedNameErrorType` | General info |
| ------------------------- | ------------ |
| `EMPTY_NAME`   | The name is empty |
| `NSM_REPEATED` | Contains a repeated non-spacing mark |
| `NSM_TOO_MANY` | Contains too many consecutive non-spacing marks |
| `CONF_WHOLE` | Contains visually confusing characters that are disallowed |

## List of all `CurableError` types

Curable errors contain additional information about the disallowed substring.

| `CurableErrorType` | General info | Disallowed sequence info |
| ------------------ | ------------ | ------------------------ |
| `UNDERSCORE`  | Contains an underscore in a disallowed position | An underscore is only allowed at the start of a label |
| `HYPHEN`      | Contains the sequence '--' in a disallowed position | Hyphens are disallowed at the 2nd and 3rd positions of a label |
| `EMPTY_LABEL` | Contains a disallowed empty label | Empty labels are not allowed, e.g. abc..eth |
| `CM_START`    | Contains a combining mark in a disallowed position at the start of the label | A combining mark is disallowed at the start of a label |
| `CM_EMOJI`    | Contains a combining mark in a disallowed position after an emoji | A combining mark is disallowed after an emoji |
| `DISALLOWED`  | Contains a disallowed character | This character is disallowed |
| `INVISIBLE`   | Contains a disallowed invisible character | This invisible character is disallowed |
| `FENCED_LEADING`  | Contains a disallowed character at the start of a label | This character is disallowed at the start of a label |
| `FENCED_MULTI`    | Contains a disallowed consecutive sequence of characters | Characters in this sequence cannot be placed next to each other |
| `FENCED_TRAILING` | Contains a disallowed character at the end of a label | This character is disallowed at the end of a label |
| `CONF_MIXED` | Contains visually confusing characters from different scripts that are disallowed | This character is disallowed because it is visually confusing with another character from a different script |

## List of all normalization transformations

| `NormalizationTransformationType` | General info | Disallowed sequence info |
| --------------------------------- | ------------ | ------------------------ |
| `IGNORED`    | Contains disallowed "ignored" characters that have been removed | This character is ignored during normalization and has been automatically removed |
| `MAPPED`     | Contains a disallowed character that has been replaced by a normalized sequence | This character is disallowed and has been automatically replaced by a normalized sequence |
| `FE0F`       | Contains a disallowed variant of an emoji which has been replaced by an equivalent normalized emoji | This emoji has been automatically fixed to remove an invisible character |
| `NFC`        | Contains a disallowed sequence that is not "NFC normalized" which has been replaced by an equivalent normalized sequence | This sequence has been automatically normalized into NFC canonical form |

## Develop

### Update this library to the latest ENS normalization specification *(optional)*

This library uses files defining the normalization standard
directly from the [official Javascript implementation](https://github.com/adraffy/ens-normalize.js/tree/main/derive).
When the standard is updated with new characters, this library can
be updated by running the following steps:

1. Requirements:
    * [Node.js](https://nodejs.org) >= 18
    * [npm](https://www.npmjs.com)
2. Set the hash of the latest commit from the [JavaScript library](https://github.com/adraffy/ens-normalize.js) inside [package.json](tools/updater/package.json)
3. Run the updater:

    ```bash
    cd tools/updater
    npm start
    ```

4. Update `NormalizationData.VERSION`:\
   This library keeps cache files in `$HOME/.cache/ens_normalize` to speed up loading.
   To make sure existing users regenerate their cache after a version update,
   please increment the `NormalizationData.VERSION` constant in [normalization.py](/ens_normalize/normalization.py).
   The first import of the new version will automatically regenerate the cache.

### Build and test

Installs dependencies, runs validation tests and builds the wheel.

1. Install requirements:
   * [Python](https://www.python.org)
   * [Poetry](https://python-poetry.org)

2. Install dependencies:

    ```bash
    poetry install
    ```

3. Run tests (including official validation tests):

    ```bash
    poetry run pytest
    ```

4. Build Python wheel:

    ```bash
    poetry build
    ```
