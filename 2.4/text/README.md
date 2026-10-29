# Structured text test files

See the [2.4 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a Markdown file with YAML front matter, reading "C2PA test document.", signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the file with edited text. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a paragraph from an unsigned component file (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.4) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| Markdown | `md` | `BEGIN`/`END C2PA MANIFEST` block in the front matter, `data:` URI | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.md](good/md/cogproof-20261029-C.md) | Valid, no ingredients |
| [cogproof-20261029-CA.md](good/md/cogproof-20261029-CA.md) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.md](good/md/cogproof-20261029-CAI.md) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.md](bad/md/cogproof-20261029-E-dat-CA.md) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.md](bad/md/cogproof-20261029-E-sig-CA.md) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.md](bad/md/cogproof-20261029-E-uri-CA.md) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

c2pa-rs writes structured text behind its `unstable_structured_text` feature. Plain text (`.txt`) and comment-line structured text (such as `.xml`) are not included; see [the 2.4 README](../README.md#not-included).

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
