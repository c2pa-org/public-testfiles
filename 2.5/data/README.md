# Data test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a Parquet table with one row, "C2PA test document.", signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the table with the text edited. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a row from an unsigned component table (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| Parquet | `parquet` | Base64 in footer `key_value_metadata` entry `c2pa:manifest` | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.parquet](good/parquet/cogproof-20261029-C.parquet) | Valid, no ingredients |
| [cogproof-20261029-CA.parquet](good/parquet/cogproof-20261029-CA.parquet) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.parquet](good/parquet/cogproof-20261029-CAI.parquet) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.parquet](bad/parquet/cogproof-20261029-E-dat-CA.parquet) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.parquet](bad/parquet/cogproof-20261029-E-sig-CA.parquet) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.parquet](bad/parquet/cogproof-20261029-E-uri-CA.parquet) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
