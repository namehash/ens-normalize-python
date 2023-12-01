import shutil
import os
import pickle
import pickletools
from ens_normalize.normalization import NormalizationData


SPEC_JSON_PATH = os.path.join(os.path.dirname(__file__), "spec.json")
SPEC_PICKLE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "ens_normalize", "spec.pickle"
)
INDEX_JS_PATH = os.path.join(
    os.path.dirname(__file__),
    "node_modules",
    "@adraffy",
    "ens-normalize",
    "dist",
    "index.mjs",
)


def generate_pickle():
    data = NormalizationData(SPEC_JSON_PATH)
    # Python >= 3.8 is required for protocol 5
    buf = pickle.dumps(data, protocol=5)
    buf = pickletools.optimize(buf)
    with open(SPEC_PICKLE_PATH, "wb") as f:
        f.write(buf)


def add_whole_map_export():
    with open(INDEX_JS_PATH, encoding="utf-8") as f:
        content = f.read()

    content += "\n\n// added by update_ens.py\ninit();\nexport {WHOLE_MAP};\n"

    with open(INDEX_JS_PATH, "w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    shutil.rmtree("node_modules", ignore_errors=True)
    os.system("npm install")
    add_whole_map_export()
    os.system("node update-ens.js")
    generate_pickle()
