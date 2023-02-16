import { ens_normalize, ens_tokenize, ens_beautify, WHOLE_MAP } from '@adraffy/ens-normalize';
import { readFile, writeFile } from 'fs/promises';

const package_json = JSON.parse(await readFile("package.json"));
const COMMIT_HASH = package_json["dependencies"]["@adraffy/ens-normalize"].replace("github:adraffy/ens-normalize.js#", "");

const SPEC_URL = "https://raw.githubusercontent.com/adraffy/ens-normalize.js/" + COMMIT_HASH + "/derive/output/spec.json"
const SPEC_PATH = "../../ens_normalize/spec.json";

const TESTS_URL = "https://raw.githubusercontent.com/adraffy/ens-normalize.js/" + COMMIT_HASH + "/validate/tests.json"
const TESTS_PATH = "../../tests/ens-normalize-tests.json";

function parse_whole_map(whole_map) {
    const new_whole_map = {};
    for (const [cp, value] of whole_map) {
        const key1 = cp.toString();

        if (typeof value === "number") {
            new_whole_map[key1] = value;
            continue;
        }

        const { V, M } = value;

        new_whole_map[key1] = {};
        new_whole_map[key1]["V"] = V;
        new_whole_map[key1]["M"] = {};

        for (const [cp, set] of M) {
            const key2 = cp.toString();
            new_whole_map[key1]["M"][key2] = [];
            for (let {N} of set) {
                if (N.startsWith("Restricted")) {
                    N = N.slice(11, -1);
                }
                new_whole_map[key1]["M"][key2].push(N);
            }
        }
    }
    return new_whole_map;
}

async function download_files() {
    console.log("Downloading spec...");
    const spec = await (await fetch(SPEC_URL)).json();
    spec["whole_map"] = parse_whole_map(WHOLE_MAP)
    await writeFile(SPEC_PATH, JSON.stringify(spec));

    console.log("Downloading tests...");
    const tests = await (await fetch(TESTS_URL)).json();
    await writeFile(TESTS_PATH, JSON.stringify(tests));
}

async function generate_tests() {
    console.log("Generating tests...");
    const raw_tests = JSON.parse(await readFile(TESTS_PATH));
    const new_tests = [];
    for (const test of raw_tests) {
        if (test.error === undefined) {
            let expected_norm = test.norm === undefined ? test.name : test.norm
            if (ens_normalize(test.name) !== expected_norm) {
                throw new Error(`Test ${test.name} should be normalized to ${test.norm}`);
            }
            new_tests.push({
                name: test.name,
                norm: ens_normalize(test.name),
                beautified: ens_beautify(test.name),
                tokenized: ens_tokenize(test.name),
            });
        }
        else {
            new_tests.push({
                name: test.name,
                tokenized: ens_tokenize(test.name),
                error: test.error,
                comment: test.comment,
            });
        }
    }
    await writeFile(TESTS_PATH, JSON.stringify(new_tests));
}

await download_files();
await generate_tests();
console.log("Done!");
