# Video test files

See the [2.4 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a 2-second 320×240 ffmpeg `testsrc2` clip, signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the clip with its brightness reduced. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, with an unsigned blue square overlaid as a component ingredient (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.4) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| MP4 (H.264) | `mp4` | BMFF `uuid` box, before `moov` and `mdat` | `c2pa.hash.bmff.v3` |
| MOV (H.264) | `mov` | BMFF `uuid` box, before `moov` and `mdat` | `c2pa.hash.bmff.v3` |
| AVI (Motion JPEG) | `avi` | RIFF `C2PA` chunk, last | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.mp4](good/mp4/cogproof-20261029-C.mp4) | Valid, no ingredients |
| [cogproof-20261029-CA.mp4](good/mp4/cogproof-20261029-CA.mp4) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.mp4](good/mp4/cogproof-20261029-CAI.mp4) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.mov](good/mov/cogproof-20261029-C.mov) | Valid, no ingredients |
| [cogproof-20261029-CA.mov](good/mov/cogproof-20261029-CA.mov) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.mov](good/mov/cogproof-20261029-CAI.mov) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.avi](good/avi/cogproof-20261029-C.avi) | Valid, no ingredients |
| [cogproof-20261029-CA.avi](good/avi/cogproof-20261029-CA.avi) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.avi](good/avi/cogproof-20261029-CAI.avi) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.mp4](bad/mp4/cogproof-20261029-E-dat-CA.mp4) | CA's manifest store on a copy of CA with an 8×8 black box drawn on every frame | `assertion.bmffHash.mismatch` |
| [cogproof-20261029-E-sig-CA.mp4](bad/mp4/cogproof-20261029-E-sig-CA.mp4) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.mp4](bad/mp4/cogproof-20261029-E-uri-CA.mp4) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.mov](bad/mov/cogproof-20261029-E-dat-CA.mov) | CA's manifest store on a copy of CA with an 8×8 black box drawn on every frame | `assertion.bmffHash.mismatch` |
| [cogproof-20261029-E-sig-CA.mov](bad/mov/cogproof-20261029-E-sig-CA.mov) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.mov](bad/mov/cogproof-20261029-E-uri-CA.mov) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.avi](bad/avi/cogproof-20261029-E-dat-CA.avi) | CA's manifest store on a copy of CA with an 8×8 black box drawn on every frame | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.avi](bad/avi/cogproof-20261029-E-sig-CA.avi) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.avi](bad/avi/cogproof-20261029-E-uri-CA.avi) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
