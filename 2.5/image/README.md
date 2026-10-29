# Image test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a 256×192 colour gradient, signed with a `c2pa.created` action (`algorithmicMedia`). The `.facti` files wrap it as a PNG.
* **CA**: the gradient at 80% brightness. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, with an unsigned blue circle placed on it as a component ingredient (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| JPEG, Exif | `jpeg-exif` | `APP11` segments after the Exif `APP1` | `c2pa.hash.data` |
| JPEG, MPF | `jpeg-mpf` | `APP11` segments in the first image, after `APP1`, before the MPF `APP2` | `c2pa.hash.data` |
| BlockFact `.facti` | `facti` | `C2PA` extension block | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.jpg](good/jpeg-exif/cogproof-20261029-C.jpg) | Valid, no ingredients |
| [cogproof-20261029-CA.jpg](good/jpeg-exif/cogproof-20261029-CA.jpg) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.jpg](good/jpeg-exif/cogproof-20261029-CAI.jpg) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.jpg](good/jpeg-mpf/cogproof-20261029-C.jpg) | Valid, no ingredients |
| [cogproof-20261029-CA.jpg](good/jpeg-mpf/cogproof-20261029-CA.jpg) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.jpg](good/jpeg-mpf/cogproof-20261029-CAI.jpg) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.facti](good/facti/cogproof-20261029-C.facti) | Valid, no ingredients |
| [cogproof-20261029-CA.facti](good/facti/cogproof-20261029-CA.facti) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.facti](good/facti/cogproof-20261029-CAI.facti) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.jpg](bad/jpeg-exif/cogproof-20261029-E-dat-CA.jpg) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.jpg](bad/jpeg-exif/cogproof-20261029-E-sig-CA.jpg) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.jpg](bad/jpeg-exif/cogproof-20261029-E-uri-CA.jpg) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.jpg](bad/jpeg-mpf/cogproof-20261029-E-dat-CA.jpg) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.jpg](bad/jpeg-mpf/cogproof-20261029-E-sig-CA.jpg) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.jpg](bad/jpeg-mpf/cogproof-20261029-E-uri-CA.jpg) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.facti](bad/facti/cogproof-20261029-E-dat-CA.facti) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.facti](bad/facti/cogproof-20261029-E-sig-CA.facti) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.facti](bad/facti/cogproof-20261029-E-uri-CA.facti) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

The `jpeg-exif` files are strict Exif JPEGs (APP1 first, no JFIF APP0), and the `jpeg-mpf` files are two-image MPF files whose second image is the first inverted. 2.5 applies the JPEG 1 embedding to both, with the manifest in an APP11 segment of the first image.

c2pa-rs writes these with contentauth/c2pa-rs#2962. The BlockFact `.facti` handler is behind c2pa-rs's `unstable_blockfact` feature.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
