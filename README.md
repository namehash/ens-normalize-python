# ens-normalize

* Python implementation of the [ENS Name Normalization Standard](https://github.com/adraffy/ensip-norm/blob/main/draft.md)

* Passes 100% validation tests

* Based on [JavaScript implementation version 1.8.9](https://github.com/adraffy/ens-normalize.js/tree/fa0ad385e77299ad8bddc2287876fbf74a92b8db)

## Usage
```
pip install ens-normalize
```

```python
from ens_normalize import (
    ens_normalize,
    ens_beautify,
    ens_tokenize,
)
```

```python
# str -> str
# raises ValueError for invalid names
# output ready for namehash
ens_normalize('NameHash.ETH')
# 'namehash.eth'
ens_normalize('Name‍Hash.ETH')
# ValueError: Contains a disallowed invisible character
```

```python
# works like ens_normalize()
# output ready for display
ens_beautify('1⃣2⃣.eth')
# '1️⃣2️⃣.eth'
```

```python
# str -> List[Token]
# always returns a tokenization of the input
ens_tokenize('Nàme‍Hash🧙‍♂')
# [TokenMapped(cp=78, cps=[110], type='mapped'),
#  TokenNFC(input=[97, 768], cps=[224], type='nfc'),
#  TokenValid(cps=[109, 101], type='valid'),
#  TokenDisallowed(cp=8205, type='disallowed'),
#  TokenMapped(cp=72, cps=[104], type='mapped'),
#  TokenValid(cps=[97, 115, 104], type='valid'),
#  TokenEmoji(emoji=[129497, 8205, 9794, 65039], input=[129497, 8205, 9794], cps=[129497, 8205, 9794], type='emoji')]
```

```python
# advanced usage
from ens_normalize import ens_process, NormalizationErrorType
# compute many functions in one call
# do_* arguments control what is computed
ens_process('NameHash.ETH',
    # ens_normalize()
    do_normalize=True,
    # ens_beautify()
    do_beautify=True,
    # ens_tokenize()
    do_tokenize=True,
    # the reason why the input is not normalized
    do_reason=True)
# ENSProcessResult(
#     normalized='namehash.eth',
#     beautified='namehash.eth',
#     tokens=[...],
#     # error is None if name is normalized
#     error=NormalizationError(
#         type=NormalizationErrorType.NORM_ERR_MAPPED,
#         # position of the error
#         start=0,
#         # the substring that is disallowed
#         disallowed='N',
#         # how to fix the error
#         suggested='n'),
#     # is the above error fatal (input disallowed)
#     # or is it a warning (input can be normalized)
#     is_fatal=False)
```

```python
# error information
NormalizationErrorType.NORM_ERR_NFC.message
# 'Contains a disallowed sequence that is not "NFC normalized" into canonical form'
NormalizationErrorType.NORM_ERR_NFC.details
# 'This sequence should be correctly "NFC normalized" into its canonical form when it is saved to the blockchain during a valid registration'
```
