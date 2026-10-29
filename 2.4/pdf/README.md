# PDF test files

See the [2.4 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a one-page PDF reading "C2PA test document.", signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the page with edited text. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a paragraph from an unsigned component PDF (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.4) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| PDF | `pdf` | Embedded file stream, `AFRelationship` `C2PA_Manifest`, in the catalog `AF` and `EmbeddedFiles` | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.pdf](good/pdf/cogproof-20261029-C.pdf) | Valid, no ingredients |
| [cogproof-20261029-CA.pdf](good/pdf/cogproof-20261029-CA.pdf) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.pdf](good/pdf/cogproof-20261029-CAI.pdf) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.pdf](bad/pdf/cogproof-20261029-E-dat-CA.pdf) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.pdf](bad/pdf/cogproof-20261029-E-sig-CA.pdf) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.pdf](bad/pdf/cogproof-20261029-E-uri-CA.pdf) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

c2pa-rs writes PDF behind its `pdf` feature.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
