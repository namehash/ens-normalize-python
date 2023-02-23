import unicodedata
import ens_normalize
import argparse
import dask.bag as db


def find_char_cm(num_cm):
    valid = db.from_sequence(ens_normalize.normalization.NORMALIZATION.valid).map(chr)
    chars = valid.filter(lambda c: unicodedata.combining(c) == 0)
    combining = valid.filter(lambda c: unicodedata.combining(c) != 0)
    char_cm = chars.product(combining).map(lambda x: x[0] + x[1] * num_cm)
    valid_char_cm = char_cm.filter(lambda x: ens_normalize.ens_process(x, do_reason=True).error is None)
    return valid_char_cm


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cm', type=int, default=1)
    parser.add_argument('-n', type=int, default=None)
    args = parser.parse_args()

    valid_char_cm = find_char_cm(args.cm)
    if args.n is not None:
        valid_char_cm = valid_char_cm.take(args.n)
        for x in valid_char_cm:
            print(f'"{x}"')
    else:
        valid_char_cm.map(lambda x: print(f'"{x}"')).compute()
