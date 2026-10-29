# Video test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a 2-second 320×240 ffmpeg `testsrc2` clip (MP4 inside `.factv`), signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the clip with its brightness reduced. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, with an unsigned blue square overlaid as a component ingredient (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| BlockFact `.factv` | `factv` | `C2PA` extension block | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.factv](good/factv/cogproof-20261029-C.factv) | Valid, no ingredients |
| [cogproof-20261029-CA.factv](good/factv/cogproof-20261029-CA.factv) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.factv](good/factv/cogproof-20261029-CAI.factv) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.factv](bad/factv/cogproof-20261029-E-dat-CA.factv) | CA's manifest store on a copy of CA with an 8×8 black box drawn on every frame | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.factv](bad/factv/cogproof-20261029-E-sig-CA.factv) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.factv](bad/factv/cogproof-20261029-E-uri-CA.factv) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

c2pa-rs writes `.factv` behind its `unstable_blockfact` feature.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
