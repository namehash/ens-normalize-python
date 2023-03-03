# ENS Normalize Python

![Tests](https://github.com/namehash/ens-normalize-python/actions/workflows/python-app.yml/badge.svg?branch=main)
![PyPI](https://img.shields.io/pypi/v/ens-normalize)

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
# raises NormalizationError for invalid names
# output ready for namehash
ens_normalize('Nick.ETH')
# 'nick.eth'
# note: does not enforce .eth TLD 3-character minimum
```

Catch normalization errors:

```python
# added a hidden "zero width joiner" character
try:
    ens_normalize('Ni‍ck.ETH')
except NormalizationError as e:
    print('Error:', e)
    # Error: Contains a disallowed invisible character
```

Format names with fully-qualified emoji:

```python
# works like ens_normalize()
# output ready for display
ens_beautify('1⃣2⃣.eth')
# '1️⃣2️⃣.eth'

# note: normalization is unchanged:
# ens_normalize(ens_beautify(x)) == ens_normalize(x)
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
# returns a list of "warnings" - modifications
# that have been applied to the input during normalization
ens_warnings('Nàme🧙‍♂️')
# [NormalizationWarning(type=MAPPED, modification="N"->"n"),
#  NormalizationWarning(type=FE0F, modification="🧙‍♂️"->"🧙‍♂")]
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
    for w in ens_warnings(name):
        print(repr(w)) # use repr() to print more information
    # NormalizationWarning(type=MAPPED, modification="N"->"n")
    # NormalizationWarning(type=FE0F, modification="🧙‍♂️"->"🧙‍♂")
    #              invisible character inside emoji ^
except NormalizationError as e:
    print('Error:', e)
```

Speed up your code by running all of the above functions at once:

```python
# use only the do_* flags you need
ens_process("Nàme🧙‍♂️",
    do_normalize=True,
    do_beautify=True,
    do_tokenize=True,
    do_warnings=True,
)
# ENSProcessResult(
#   normalized='nàme🧙\u200d♂',
#   beautified='nàme🧙\u200d♂️',
#   tokens=[...],
#   error=None, # <- this is the exception object thrown by other functions
#   warnings=[
#     NormalizationWarning(type=MAPPED, modification="N"->"n"),
#     NormalizationWarning(type=FE0F, modification="🧙‍♂️"->"🧙‍♂")
#   ])
```

## List of reported errors

| `NormalizationErrorType` | Description | Modified substring reported by `ens_warnings` |
| ---------- | ----------- | --------------- |
| `NORM_ERR_UNDERSCORE` | Contains an underscore in a disallowed position | ✅ |
| `NORM_ERR_HYPHEN`     | Contains the sequence '--' in a disallowed position | ✅ |
| `NORM_ERR_EMPTY`      | Contains a disallowed empty label | ✅ |
| `NORM_ERR_CM_START`   | Contains a combining mark in a disallowed position at the start of the label | ✅ |
| `NORM_ERR_CM_EMOJI`   | Contains a combining mark in a disallowed position after an emoji | ✅ |
| `NORM_ERR_NSM_REPEATED` | *TODO* | ? |
| `NORM_ERR_NSM_TOO_MANY` | *TODO* | ? |
| `NORM_ERR_DISALLOWED` | Contains a disallowed character | ✅ |
| `NORM_ERR_INVISIBLE`  | Contains a disallowed invisible character | ✅ |
| `NORM_ERR_FENCED_LEADING`  | Contains a disallowed character at the start of a label | ✅ |
| `NORM_ERR_FENCED_MULTI`    | Contains a disallowed sequence of 2 characters | ✅ |
| `NORM_ERR_FENCED_TRAILING` | Contains a disallowed character at the end of a label | ✅ |
| `NORM_ERR_CONF_WHOLE` | Contains whole-script confusables | ❌ |
| `NORM_ERR_CONF_MIXED` | Contains mixed-script confusables | ✅ |

## List of reported warnings

| `NormalizationWarningType` | Description | Modified substring reported by `ens_warnings` |
| ---------- | ----------- | --------------- |
| `NORM_ERR_IGNORED`    | Contains a disallowed character that is ignored during normalization | ✅ |
| `NORM_ERR_MAPPED`     | Contains a disallowed character that is changed (mapped) to another sequence during normalization | ✅ |
| `NORM_ERR_FE0F`       | Contains a disallowed invisible character inside an emoji | ✅ |
| `NORM_ERR_NFC`        | Contains a disallowed sequence that is not "NFC normalized" into canonical form | ✅ |

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
