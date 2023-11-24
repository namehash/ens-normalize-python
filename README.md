# ENS Normalize Python

![Tests](https://github.com/namehash/ens-normalize-python/actions/workflows/python-app.yml/badge.svg?branch=main)
![PyPI](https://img.shields.io/pypi/v/ens-normalize)
![Coverage](https://raw.githubusercontent.com/namehash/ens-normalize-python/main/coverage_badge.svg)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/namehash/ens-normalize-python/blob/main/examples/notebook.ipynb)

* Python implementation of [ENSIP-15 - the ENS Name Normalization Standard](https://docs.ens.domains/ens-improvement-proposals/ensip-15-normalization-standard).
  *  Thanks to [raffy.eth](https://github.com/adraffy) for his leadership in coordinating the definition of this standard with the ENS community.
  *  This library is being maintained by the team at [NameHash Labs](https://namehashlabs.org) as part of the greater [NameGuard](https://nameguard.io) solution to help protect the ENS community.
* Passes **100%** of the [official validation tests](https://github.com/adraffy/ens-normalize.js/tree/main/validate) (validated automatically with pytest on Linux, MacOS, and Windows, see below for details).
* Passes an [additional suite of further tests](/tools/updater/update-ens.js#L54) for compatibility with the official [Javascript reference implementation](https://github.com/adraffy/ens-normalize.js) and code testing coverage.
* Based on [JavaScript implementation version 1.9.0](https://github.com/adraffy/ens-normalize.js/tree/4873fbe6393e970e186ab57860cc59cbbb1fa162).

## Glossary

**Foundations**
* **sequence** - a Unicode string containing any number of characters.
* **label separator** - a full stop character (also known as a period), e.g. `.` .
* **label** - a sequence of any length (including 0) that does not contain a label separator, e.g.  `abc` or `eth`.
* **name** - a series of any number of labels (including 0) separated by label separators, e.g. `abc.eth`.

**Names**
* **normalized name** - a name that is in normalized form according to the ENS Normalization Standard. This means `name == ens_normalize(name)`. A normalized name contains 0 or more labels. All labels in a normalized name always contain a sequence of at least 1 valid character. An empty string contains 0 labels and is a normalized name.
* **normalizable name** - a name that is normalized or that can be converted into a normalized name using `ens_normalize`.
* **beautiful name** - a name that is normalizable and is equal to itself when using `ens_beautify`. This means `name == ens_beautify(name)`. For all normalizable names `ens_normalize(ens_beautify(name)) == ens_normalize(name)`.
* **disallowed name** - a name that is not normalizable. This means `ens_normalize(name)` raises a `DisallowedSequence`.
* **curable name** - a name that is normalizable, or a name in the subset of disallowed names that can still be converted into a normalized name using `ens_cure`.
* **empty name** - a name that is the empty string. An empty string is a name with 0 labels. It is a *normalized name*.
* **namehash ready name** - a name that is ready for for use with the ENS `namehash` function. Only normalized names are namehash ready. Empty names represent the ENS namespace root for use with the ENS `namehash` function. Using the ENS `namehash` function on any name that is not namehash ready will return a node that is unreachable by ENS client applications that use a proper implementation of `ens_normalize`.

**Sequences**
* **unnormalized sequence** - a sequence from a name that is not in normalized form according to the ENS Normalization Standard.
* **normalization suggestion** - a sequence suggested as an in-place replacement for an unnormalized sequence.
* **normalizable sequence** - an unnormalized sequence containing a normalization suggestion that is automatically applied using `ens_normalize` and `ens_cure`.
* **curable sequence** - an unnormalized sequence containing a normalization suggestion that is automatically applied using `ens_cure`.
* **disallowed sequence** - an unnormalized sequence without any normalization suggestion.

The following Venn diagram is not to scale, but may help to communicate how some of the classifications of names relate to each other conceptually.

![ENS Normalize Venn Diagram](https://raw.githubusercontent.com/namehash/ens-normalize-python/main/docs/ENS_Normalize_-_Venn_Diagram.png  "ENS Normalize Venn Diagram")

## Usage

The package is available on [pypi](https://pypi.org/project/ens-normalize/)

```bash
pip install ens-normalize
```

You can also try it in Google Colab\
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/namehash/ens-normalize-python/blob/main/examples/notebook.ipynb)

### ens_normalize

Normalize an ENS name:

```python
from ens_normalize import ens_normalize
# str -> str
# raises DisallowedSequence for disallowed names
# output is namehash ready
ens_normalize('Nick.ETH')
# 'nick.eth'
# note: ens_normalize does not enforce any constraints that might be applied by a particular registrar. For example, the registrar for names that are a subname of '.eth' enforces a 3-character minimum and this constraint is not enforced by ens_normalize.
```

Check if a name is *normalizable* (see Glossary):

```python
from ens_normalize import is_ens_normalizable
# str -> bool
is_ens_normalizable('Nick.ETH')
# True
```

Inspect issues with disallowed names:

```python
from ens_normalize import DisallowedSequence, CurableSequence
try:
    # added a hidden "zero width joiner" character
    ens_normalize('Ni‍ck.ETH')
# Catch the first disallowed sequence (the name we are attempting to normalize could have more than one).
except DisallowedSequence as e:
    # error code
    print(e.code)
    # INVISIBLE

    # a message about why the sequence is disallowed
    print(e.general_info)
    # Contains a disallowed invisible character

    if isinstance(e, CurableSequence):
        # information about the curable sequence
        print(e.sequence_info)
        # 'This invisible character is disallowed'

        # starting index of the disallowed sequence in the input string
        # (counting in Unicode code points)
        print(e.index)
        # 2

        # the disallowed sequence
        # (use repr() to "see" the invisible character)
        print(repr(e.sequence))
        # '\u200d'

        # a normalization suggestion for fixing the disallowed sequence (there might be more disallowed sequences)
        print(repr(e.suggested))
        # ''
        # replacing the disallowed sequence with this suggestion (an empty string) represents the idea that the disallowed sequence is suggested to be removed

        # You may be able to fix this disallowed sequence by replacing e.sequence with e.suggested in the input string.
        # Fields index, sequence_info, sequence, and suggested are available only for curable errors.
        # Other disallowed sequences might be found even after applying this suggestion.
```
### ens_cure

You can attempt conversion of disallowed names into normalized names using `ens_cure`. This algorithm can “cure” many normalization errors that would fail `ens_normalize`. This can be useful in some situations. For example, if a user input fails `ens_normalize`, a user could be prompted with a more helpful error message such as: “Did you mean curedname.eth?”.

Some names are not curable. For example, if it is challenging to provide a specific normalization suggestion that might be needed to replace a disallowed sequence.

Note: This function is *NOT* a part of the ENS Normalization Standard.

```python
from ens_normalize import ens_cure
# input name with disallowed zero width joiner and '?'
# str -> str
ens_cure('Ni‍ck?.ETH')
# 'nick.eth'
# ZWJ and '?' are removed, no error is raised

# note: might remove all characters from the input, which would result in an empty name
ens_cure('?')
# '' (empty string)
# reason: '?' is disallowed and no replacement can be suggested

# note: might still raise DisallowedSequence for certain names, which cannot be cured, e.g.
ens_cure('0х0.eth')
# DisallowedSequence: Contains visually confusing characters from Cyrillic and Latin scripts
# reason: The "х" is actually a Cyrillic character that is visually confusing with the Latin "x".
#         However, the "0"s are standard Latin digits and it is not clear which characters should be removed.
#         They conflict with each other because it is not known if the user intended to use Cyrillic or Latin.
```

### ens_beautify

Get a beautiful name that is optimized for display:

```python
from ens_normalize import ens_beautify
# works like ens_normalize()
# output ready for display
ens_beautify('1⃣2⃣.eth')
# '1️⃣2️⃣.eth'

# note: normalization is unchanged:
# ens_normalize(ens_beautify(x)) == ens_normalize(x)
# note: in addition to beautifying emojis with fully-qualified emoji, ens_beautify converts the character 'ξ' (Greek lowercase 'Xi') to 'Ξ' (Greek uppercase 'Xi', a.k.a. the Ethereum symbol) in labels that contain no other Greek characters
```

### ens_tokenize

Generate detailed name analysis:

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

### ens_normalizations

For a normalizable name, you can find out how the input is transformed during normalization:

```python
from ens_normalize import ens_normalizations
# Returns a list of transformations (unnormalized sequence -> normalization suggestion)
# that have been applied to the input during normalization.
# NormalizableSequence has the same fields as CurableSequence:
# - code
# - general_info
# - sequence_info
# - index
# - sequence
# - suggested
ens_normalizations('Nàme🧙‍♂️.eth')
# [NormalizableSequence(code="MAPPED", index=0, sequence="N", suggested="n"),
#  NormalizableSequence(code="FE0F", index=4, sequence="🧙‍♂️", suggested="🧙‍♂")]
```

### Example Workflow

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
        for t in ens_normalizations(name):
            print(repr(t)) # use repr() to print more information
        # NormalizableSequence(code="MAPPED", index=0, sequence="N", suggested="n")
        # NormalizableSequence(code="FE0F", index=4, sequence="🧙‍♂️", suggested="🧙‍♂")
        #                                     invisible character inside emoji ^
except DisallowedSequence as e:
    # Even if the name is invalid according to the ENS Normalization Standard,
    # we can try to automatically cure disallowed sequences.
    try:
        print('Cured:', ens_cure(name))
    except DisallowedSequence as e:
        # The name cannot be automatically cured.
        print('Disallowed name error:', e)
```

You can run many of the above functions at once. It is faster than running all of them sequentially.

```python
from ens_normalize import ens_process
# use only the do_* flags you need
ens_process("Nàme🧙‍♂️1⃣.eth",
    do_normalize=True,
    do_beautify=True,
    do_tokenize=True,
    do_normalizations=True,
    do_cure=True,
)
# ENSProcessResult(
#   normalized='nàme🧙\u200d♂1⃣.eth',
#   beautified='nàme🧙\u200d♂️1️⃣.eth',
#   tokens=[...],
#   cured='nàme🧙\u200d♂1⃣.eth',
#   cures=[], # This is the list of cures that were applied to the input (in this case, none).
#   error=None, # This is the exception raised by ens_normalize().
#               # It is a DisallowedSequence or CurableSequence if the error is curable.
#   normalizations=[
#     NormalizableSequence(code="MAPPED", index=0, sequence="N", suggested="n"),
#     NormalizableSequence(code="FE0F", index=4, sequence="🧙‍♂️", suggested="🧙‍♂")
#   ])
```

## Exceptions

These Python classes are used by the library to communicate information about unnormalized sequences.

| Exception class               |  `ens_normalize` handling  | `ens_cure` handling       | normalization<br>suggestion  | Inherits From         |
|-------------------------------|----------------------------|---------------------------|------------------------------|-----------------------|
| `NormalizableSequence`        |  ✅ automatically resolves | ✅ automatically resolves | ✅ included                  | `CurableSequence`     |
| `CurableSequence`             |  ❌ throws error           | ✅ automatically resolves | ✅ included                  | `DisallowedSequence`  |
| `DisallowedSequence`          |  ❌ throws error           | ❌ throws error           | ❌ none                      | `Exception`           |

### List of all `NormalizableSequence` types

| `NormalizableSequenceType` | General info | Sequence info |
| --------------------------------- | ------------ | ------------------------ |
| `IGNORED`    | Contains a disallowed "ignored" character that has been removed | This character is ignored during normalization and has been automatically removed |
| `MAPPED`     | Contains a disallowed character that has been replaced by a normalized sequence | This character is disallowed and has been automatically replaced by a normalized sequence |
| `FE0F`       | Contains a disallowed variant of an emoji which has been replaced by an equivalent normalized emoji | This emoji has been automatically fixed to remove an invisible character |
| `NFC`        | Contains a disallowed sequence that is not "NFC normalized" which has been replaced by an equivalent normalized sequence | This sequence has been automatically normalized into NFC canonical form |

### List of all `CurableSequence` types

Curable errors contain additional information about the disallowed sequence and a normalization suggestion that might help to cure the name.

| `CurableSequenceType` | General info | Sequence info |
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
| `CONF_MIXED` | Contains visually confusing characters from multiple scripts ({script1}/{script2}) | This character from the {script1} script is disallowed because it is visually confusing with another character from the {script2} script |

### List of all `DisallowedSequence` types

Disallowed name errors are not considered curable because it may be challenging to suggest a specific normalization suggestion that might resolve the problem.

| `DisallowedSequenceType` | General info | Explanation |
| ------------------------- | ------------ | ------------------------ |
| `NSM_REPEATED` | Contains a repeated non-spacing mark | Non-spacing marks can be encoded as one codepoint with the preceding character, which makes it difficult to suggest a normalization suggestion |
| `NSM_TOO_MANY` | Contains too many consecutive non-spacing marks | Non-spacing marks can be encoded as one codepoint with the preceding character, which makes it difficult to suggest a normalization suggestion |
| `CONF_WHOLE` | Contains visually confusing characters from {script1} and {script2} scripts | Both characters are equally likely to be the correct character to use and a normalization suggestion cannot be provided |

## Development

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
