# Text test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a text file reading "C2PA test document.", signed with a `c2pa.created` action (`algorithmicMedia`). The WebVTT files hold the same text as cues.
* **CA**: the file with edited text. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a paragraph from an unsigned component file (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| Plain text | `txt` | `C2PATextManifestWrapper` (variation selectors) at the end, with deterministic padding | `c2pa.hash.data` |
| WebVTT | `vtt` | `NOTE` comment with the `BEGIN`/`END C2PA MANIFEST` block, right after the `WEBVTT` header | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.txt](good/txt/cogproof-20261029-C.txt) | Valid, no ingredients |
| [cogproof-20261029-CA.txt](good/txt/cogproof-20261029-CA.txt) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.txt](good/txt/cogproof-20261029-CAI.txt) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.vtt](good/vtt/cogproof-20261029-C.vtt) | Valid, no ingredients |
| [cogproof-20261029-CA.vtt](good/vtt/cogproof-20261029-CA.vtt) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.vtt](good/vtt/cogproof-20261029-CAI.vtt) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.txt](bad/txt/cogproof-20261029-E-dat-CA.txt) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.txt](bad/txt/cogproof-20261029-E-sig-CA.txt) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.txt](bad/txt/cogproof-20261029-E-uri-CA.txt) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.vtt](bad/vtt/cogproof-20261029-E-dat-CA.vtt) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.vtt](bad/vtt/cogproof-20261029-E-sig-CA.vtt) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.vtt](bad/vtt/cogproof-20261029-E-uri-CA.vtt) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

c2pa-rs writes plain and structured text behind its `unstable_plain_text` and `unstable_structured_text` features.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
