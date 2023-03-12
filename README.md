# ENS Normalize Python

![Tests](https://github.com/namehash/ens-normalize-python/actions/workflows/python-app.yml/badge.svg?branch=main)
![PyPI](https://img.shields.io/pypi/v/ens-normalize)
![Coverage](coverage_badge.svg)

* Python implementation of the [ENS Name Normalization Standard](https://github.com/adraffy/ensip-norm/blob/main/draft.md).
  Thanks to [Adraffy](https://github.com/adraffy) for his leadership in coordinating the definition of this standard.
* Passes **100%** of the [official validation tests](https://github.com/adraffy/ens-normalize.js/tree/main/validate) (validated automatically with pytest, see below).
* Passes an [additional suite of further tests](/tools/updater/update-ens.js#L54) for compatibility with the official [Javascript reference implementation](https://github.com/adraffy/ens-normalize.js) and code testing coverage.
* Based on [JavaScript implementation version 1.9.0](https://github.com/adraffy/ens-normalize.js/tree/4873fbe6393e970e186ab57860cc59cbbb1fa162).

## Usage

The package is available on [pypi](https://pypi.org/project/ens-normalize/)

```bash
pip install ens-normalize
```

Import the main functions provided by this library:

```python
from ens_normalize import ens_normalize, ens_beautify
```

Normalize an ENS name:

```python
# str -> str
# raises DisallowedLabelError for disallowed names according to the ENS Name Normalization Standard
# output ready for namehash
ens_normalize('Nick.ETH')
# 'nick.eth'
# note: does not enforce .eth TLD 3-character minimum
```

Catch disallowed names:

```python
# added a hidden "zero width joiner" character
try:
    ens_normalize('Ni‍ck.ETH')
# Catch the first disallowed substring (there might be more).
except DisallowedLabelError as e:
    # error code
    print(e.code)
    # INVISIBLE
    
    # a message about why the input is disallowed
    print(e.general_info)
    # Contains a disallowed invisible character
    
    # starting index of the disallowed substring in the input string
    # (counting in Unicode code points)
    print(e.index)
    # 2

    # information about the disallowed substring
    print(e.disallowed_sequence_info)
    # 'This invisible character is disallowed'

    # the disallowed substring
    # (use repr() to "see" the invisible character)
    print(repr(e.disallowed))
    # '\u200d'

    # a suggestion for fixing the error
    print(repr(e.suggested))
    # ''
    # empty string means that the disallowed substring has to be removed

    # You may be able to fix this error by replacing e.disallowed
    # with e.suggested in the input string.
    # Other errors might be found even after applying this suggestion.
```

You can force the normalization of invalid names:

```python
# input name with disallowed zero width joiner and '?'
# str -> str
ens_force_normalize('Ni‍ck?.ETH')
# 'nick.eth'
# ZWJ and '?' are removed, no error is raised
# note: ens_normalize() is preferred over ens_force_normalize()
#       because ens_force_normalize() might destroy the input
#       by removing too many characters

# note: might still raise DisallowedLabelError for certain names, which can't be force normalized
ens_force_normalize('abc..eth')
# DisallowedLabelError: Contains a disallowed empty label
```

Format names with fully-qualified emoji:

```python
# works like ens_normalize()
# output ready for display
ens_beautify('1⃣2⃣.eth')
# '1️⃣2️⃣.eth'

# note: normalization is unchanged:
# ens_normalize(ens_beautify(x)) == ens_normalize(x)
# note: except beautifying emojis, it capitalizes the letter 'ξ' to 'Ξ' (Ethereum symbol) in non-Greek labels
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

For a valid name, you can find out how the input was modified during normalization:

```python
# Returns a list of transformations (substring -> string)
# that have been applied to the input during normalization.
# NormalizationTransformation has the same fields as DisallowedLabelError:
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

A typical normalization workflow:

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
except DisallowedLabelError as e:
    # Even if the name cannot be normalized
    # we can still suggest a possible fix.
    print('Error:', e)
    print('Try removing', e.disallowed, 'at index', e.start)
```

You can run all of the above functions at once:

```python
# use only the do_* flags you need
ens_process("Nàme🧙‍♂️1⃣.eth",
    do_normalize=True,
    do_beautify=True,
    do_tokenize=True,
    do_transformations=True,
)
# ENSProcessResult(
#   normalized='nàme🧙\u200d♂1⃣.eth',
#   beautified='nàme🧙\u200d♂️1️⃣.eth',
#   tokens=[...],
#   disallowed_label_error=None, # this is the exception raised by ens_normalize()
#   transformations=[
#     NormalizationTransformation(code="MAPPED", index=0, disallowed="N", suggested="n"),
#     NormalizationTransformation(code="FE0F", index=4, disallowed="🧙‍♂️", suggested="🧙‍♂")
#   ])
```

## List of all `DisallowedLabelError` types

For some errors it is difficult to find the substring of the input which caused the error.
For these errors (see 3rd table column) the `index`, `disallowed_sequence_info`, `disallowed` and `suggested` fields will be `None`.

| `DisallowedLabelErrorType` | General info | Disallowed substring reported |
| ---------- | ----------- | --------------- |
| `UNDERSCORE` | Contains an underscore in a disallowed position | ✅ |
| `HYPHEN`     | Contains the sequence '--' in a disallowed position | ✅ |
| `EMPTY`      | Contains a disallowed empty label | ✅ |
| `CM_START`   | Contains a combining mark in a disallowed position at the start of the label | ✅ |
| `CM_EMOJI`   | Contains a combining mark in a disallowed position after an emoji | ✅ |
| `NSM_REPEATED` | Contains a repeated non-spacing mark | ❌ |
| `NSM_TOO_MANY` | Contains too many consecutive non-spacing marks | ❌ |
| `DISALLOWED` | Contains a disallowed character | ✅ |
| `INVISIBLE`  | Contains a disallowed invisible character | ✅ |
| `FENCED_LEADING`  | Contains a disallowed character at the start of a label | ✅ |
| `FENCED_MULTI`    | Contains a disallowed consecutive sequence of characters | ✅ |
| `FENCED_TRAILING` | Contains a disallowed character at the end of a label | ✅ |
| `CONF_WHOLE` | Contains visually confusing characters that are disallowed | ❌ |
| `CONF_MIXED` | Contains visually confusing characters from different scripts that are disallowed | ✅ |

## List of all normalization transformations

| `NormalizationTransformationType` | General info | Disallowed substring reported |
| ---------- | ----------- | --------------- |
| `IGNORED`    | Contains disallowed "ignored" characters that have been removed | ✅ |
| `MAPPED`     | Contains a disallowed character that has been replaced by a normalized sequence | ✅ |
| `FE0F`       | Contains a disallowed variant of an emoji which has been replaced by an equivalent normalized emoji | ✅ |
| `NFC`        | Contains a disallowed sequence that is not "NFC normalized" which has been replaced by an equivalent normalized sequence | ✅ |

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
