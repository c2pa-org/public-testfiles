# Font test files

See the [2.4 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a font with one glyph, a square `A`, signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the font with `A` scaled down. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a triangle `B` from an unsigned component font (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.4) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| TrueType (`glyf`) | `ttf` | `C2PA` table, embedded store | `c2pa.hash.boxes` |
| OpenType (`CFF`) | `otf` | `C2PA` table, embedded store | `c2pa.hash.boxes` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.ttf](good/ttf/cogproof-20261029-C.ttf) | Valid, no ingredients |
| [cogproof-20261029-CA.ttf](good/ttf/cogproof-20261029-CA.ttf) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.ttf](good/ttf/cogproof-20261029-CAI.ttf) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.otf](good/otf/cogproof-20261029-C.otf) | Valid, no ingredients |
| [cogproof-20261029-CA.otf](good/otf/cogproof-20261029-CA.otf) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.otf](good/otf/cogproof-20261029-CAI.otf) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.ttf](bad/ttf/cogproof-20261029-E-dat-CA.ttf) | CA's manifest store on a copy of CA with one point of `A` moved by one unit | `assertion.boxesHash.mismatch` |
| [cogproof-20261029-E-sig-CA.ttf](bad/ttf/cogproof-20261029-E-sig-CA.ttf) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.ttf](bad/ttf/cogproof-20261029-E-uri-CA.ttf) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.otf](bad/otf/cogproof-20261029-E-dat-CA.otf) | CA's manifest store on a copy of CA with one point of `A` moved by one unit | `assertion.boxesHash.mismatch` |
| [cogproof-20261029-E-sig-CA.otf](bad/otf/cogproof-20261029-E-sig-CA.otf) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.otf](bad/otf/cogproof-20261029-E-uri-CA.otf) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
