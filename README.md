# ENS Normalize Python

![Tests](https://github.com/namehash/ens-normalize-python/actions/workflows/python-app.yml/badge.svg?branch=main)
![PyPI](https://img.shields.io/pypi/v/ens-normalize)
![Coverage](coverage_badge.svg)

* Python implementation of the [ENS Name Normalization Standard](https://github.com/adraffy/ensip-norm/blob/main/draft.md) as led by [Adraffy](https://github.com/adraffy).
* Passes **100%** of the [official validation tests](https://github.com/adraffy/ens-normalize.js/tree/main/validate) (validated automatically with pytest, see below)
* Passes an [additional suite of further tests](/tools/updater/update-ens.js#L54) for compatibility with the [official Javascript library](https://github.com/adraffy/ens-normalize.js)
* Based on [JavaScript implementation version 1.9.0](https://github.com/adraffy/ens-normalize.js/tree/4873fbe6393e970e186ab57860cc59cbbb1fa162)

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
# raises InvalidLabelError for invalid names according to the ENS Name Normalization Standard
# output ready for namehash
ens_normalize('Nick.ETH')
# 'nick.eth'
# note: does not enforce .eth TLD 3-character minimum
```

Catch invalid names:

```python
# added a hidden "zero width joiner" character
try:
    ens_normalize('Ni‍ck.ETH')
# Catch the first normalization error encountered (there might be more).
except InvalidLabelError as e:
    # error code
    print(e.code)
    # INVISIBLE
    
    # a message about why the input is invalid
    print(e.general_info)
    # Contains a disallowed invisible character
    
    # starting index of the disallowed substring in the input string
    print(e.index)
    # 2
    
    # Other useful fields:
    # - e.disallowed_sequence_info: str
    #   A message about the disallowed sequence.
    #
    # - e.disallowed: str
    #   A substring containing the disallowed sequence,
    #   '\200D' (zero width joiner) in this case.
    #
    # - e.suggested: str
    #   You can fix this error by replacing e.disallowed
    #   with e.suggested in the input string.
    #   In this case this field is '' (empty string).
    #   It means that the disallowed sequence has to be removed.
    #   Other errors might be found even after applying this suggestion.
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

# note: might still raise NormalizationError for certain names, which can't be force normalized
ens_force_normalize('abc..eth')
# NormalizationError: Contains a disallowed empty label
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
ens_tokenize('Nàme‍🧙‍♂')
# [TokenMapped(cp=78, cps=[110], type='mapped'),
#  TokenNFC(input=[97, 768], cps=[224], type='nfc'),
#  TokenValid(cps=[109, 101], type='valid'),
#  TokenDisallowed(cp=8205, type='disallowed'),
#  TokenEmoji(emoji=[129497, 8205, 9794, 65039],
#             input=[129497, 8205, 9794],
#             cps=[129497, 8205, 9794],
#             type='emoji')]
```

Find out how the input was modified during normalization:

```python
# Returns a list of modifications (substring -> string)
# that have been applied to the input during normalization.
# Has the same fields as InvalidLabelError:
# - code
# - general_info
# - disallowed_sequence_info
# - disallowed
# - suggested
ens_transformations('Nàme🧙‍♂️')
# [NormalizationTransformation(code=MAPPED, modification="N"->"n"),
#  NormalizationTransformation(code=FE0F, modification="🧙‍♂️"->"🧙‍♂")]
```

A typical normalization workflow:

```python
name = 'Nàme🧙‍♂️'
try:
    normalized = ens_normalize(name)
    print('Normalized:', normalized)
    # Normalized: nàme🧙‍♂
    # Success!
    # Let's check how the input was changed:
    for w in ens_transformations(name):
        print(repr(w)) # use repr() to print more information
    # NormalizationTransformation(code=MAPPED, modification="N"->"n")
    # NormalizationTransformation(code=FE0F, modification="🧙‍♂️"->"🧙‍♂")
    #                     invisible character inside emoji ^
except InvalidLabelError as e:
    # Even if the label cannot be normalized
    # we can still suggest a fix.
    print('Error:', e)
    print('Try removing', e.disallowed, 'at index', e.start)
```

Speed up your code by running all of the above functions at once:

```python
# use only the do_* flags you need
ens_process("Nàme🧙‍♂️1⃣",
    do_normalize=True,
    do_beautify=True,
    do_tokenize=True,
    do_transformations=True,
)
# ENSProcessResult(
#   normalized='nàme🧙\u200d♂1⃣',
#   beautified='nàme🧙\u200d♂️1️⃣',
#   tokens=[...],
#   invalid_label_error=None, <- this is the exception raised by ens_normalize()
#   transformations=[
#     NormalizationTransformation(code=MAPPED, modification="N"->"n"),
#     NormalizationTransformation(code=FE0F, modification="🧙‍♂️"->"🧙‍♂")
#   ])
```

## List of all normalization errors

For some errors it is not possible to show a substring of the input which caused
the error. For these errors (see 3rd table column) the `index`, `disallowed` and `suggested` fields will be `None`.

| `InvalidLabelErrorType` | Description | Disallowed substring reported |
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
| `FENCED_MULTI`    | Contains a disallowed sequence of 2 characters | ✅ |
| `FENCED_TRAILING` | Contains a disallowed character at the end of a label | ✅ |
| `CONF_WHOLE` | This label can be visually confusing | ❌ |
| `CONF_MIXED` | This label contains characters from different scripts which look confusing | ✅ |

## List of all reported normalization warnings

| `NormalizationTransformationType` | Description | Disallowed substring reported |
| ---------- | ----------- | --------------- |
| `IGNORED`    | Contains a disallowed character that is ignored during normalization | ✅ |
| `MAPPED`     | Contains a disallowed character that is changed (mapped) to another sequence during normalization | ✅ |
| `FE0F`       | Contains a disallowed invisible character inside an emoji | ✅ |
| `NFC`        | Contains a disallowed sequence that is not "NFC normalized" into canonical form | ✅ |

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
