# Image test files

See the [2.4 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a 256×192 colour gradient, signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the gradient at 80% brightness. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, with an unsigned blue circle placed on it as a component ingredient (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.4) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| JPEG | `jpeg` | `APP11` (JPEG XT) segments | `c2pa.hash.data` |
| PNG | `png` | `caBX` chunk, before `IDAT` | `c2pa.hash.data` |
| SVG | `svg` | Base64 in `metadata/c2pa:manifest` | `c2pa.hash.data` |
| GIF | `gif` | `C2PA_GIF` application extension, before the first image | `c2pa.hash.data` |
| TIFF | `tiff` | Tag 52545 (`0xCD41`), type 7 | `c2pa.hash.data` |
| DNG | `dng` | Tag 52545 (`0xCD41`), type 7 | `c2pa.hash.data` |
| WebP | `webp` | RIFF `C2PA` chunk, last | `c2pa.hash.data` |
| JPEG XL | `jxl` | Top-level `jumb` box (container format) | `c2pa.hash.data` |
| HEIC | `heic` | BMFF `uuid` box | `c2pa.hash.bmff.v3` |
| AVIF | `avif` | BMFF `uuid` box | `c2pa.hash.bmff.v3` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.jpg](good/jpeg/cogproof-20261029-C.jpg) | Valid, no ingredients |
| [cogproof-20261029-CA.jpg](good/jpeg/cogproof-20261029-CA.jpg) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.jpg](good/jpeg/cogproof-20261029-CAI.jpg) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.png](good/png/cogproof-20261029-C.png) | Valid, no ingredients |
| [cogproof-20261029-CA.png](good/png/cogproof-20261029-CA.png) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.png](good/png/cogproof-20261029-CAI.png) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.svg](good/svg/cogproof-20261029-C.svg) | Valid, no ingredients |
| [cogproof-20261029-CA.svg](good/svg/cogproof-20261029-CA.svg) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.svg](good/svg/cogproof-20261029-CAI.svg) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.gif](good/gif/cogproof-20261029-C.gif) | Valid, no ingredients |
| [cogproof-20261029-CA.gif](good/gif/cogproof-20261029-CA.gif) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.gif](good/gif/cogproof-20261029-CAI.gif) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.tif](good/tiff/cogproof-20261029-C.tif) | Valid, no ingredients |
| [cogproof-20261029-CA.tif](good/tiff/cogproof-20261029-CA.tif) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.tif](good/tiff/cogproof-20261029-CAI.tif) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.dng](good/dng/cogproof-20261029-C.dng) | Valid, no ingredients |
| [cogproof-20261029-CA.dng](good/dng/cogproof-20261029-CA.dng) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.dng](good/dng/cogproof-20261029-CAI.dng) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.webp](good/webp/cogproof-20261029-C.webp) | Valid, no ingredients |
| [cogproof-20261029-CA.webp](good/webp/cogproof-20261029-CA.webp) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.webp](good/webp/cogproof-20261029-CAI.webp) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.jxl](good/jxl/cogproof-20261029-C.jxl) | Valid, no ingredients |
| [cogproof-20261029-CA.jxl](good/jxl/cogproof-20261029-CA.jxl) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.jxl](good/jxl/cogproof-20261029-CAI.jxl) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.heic](good/heic/cogproof-20261029-C.heic) | Valid, no ingredients |
| [cogproof-20261029-CA.heic](good/heic/cogproof-20261029-CA.heic) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.heic](good/heic/cogproof-20261029-CAI.heic) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.avif](good/avif/cogproof-20261029-C.avif) | Valid, no ingredients |
| [cogproof-20261029-CA.avif](good/avif/cogproof-20261029-CA.avif) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.avif](good/avif/cogproof-20261029-CAI.avif) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.jpg](bad/jpeg/cogproof-20261029-E-dat-CA.jpg) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.jpg](bad/jpeg/cogproof-20261029-E-sig-CA.jpg) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.jpg](bad/jpeg/cogproof-20261029-E-uri-CA.jpg) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.png](bad/png/cogproof-20261029-E-dat-CA.png) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.png](bad/png/cogproof-20261029-E-sig-CA.png) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.png](bad/png/cogproof-20261029-E-uri-CA.png) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.svg](bad/svg/cogproof-20261029-E-dat-CA.svg) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.svg](bad/svg/cogproof-20261029-E-sig-CA.svg) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.svg](bad/svg/cogproof-20261029-E-uri-CA.svg) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.gif](bad/gif/cogproof-20261029-E-dat-CA.gif) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.gif](bad/gif/cogproof-20261029-E-sig-CA.gif) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.gif](bad/gif/cogproof-20261029-E-uri-CA.gif) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.tif](bad/tiff/cogproof-20261029-E-dat-CA.tif) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.tif](bad/tiff/cogproof-20261029-E-sig-CA.tif) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.tif](bad/tiff/cogproof-20261029-E-uri-CA.tif) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.dng](bad/dng/cogproof-20261029-E-dat-CA.dng) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.dng](bad/dng/cogproof-20261029-E-sig-CA.dng) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.dng](bad/dng/cogproof-20261029-E-uri-CA.dng) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.webp](bad/webp/cogproof-20261029-E-dat-CA.webp) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.webp](bad/webp/cogproof-20261029-E-sig-CA.webp) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.webp](bad/webp/cogproof-20261029-E-uri-CA.webp) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.jxl](bad/jxl/cogproof-20261029-E-dat-CA.jxl) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.jxl](bad/jxl/cogproof-20261029-E-sig-CA.jxl) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.jxl](bad/jxl/cogproof-20261029-E-uri-CA.jxl) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.heic](bad/heic/cogproof-20261029-E-dat-CA.heic) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.bmffHash.mismatch` |
| [cogproof-20261029-E-sig-CA.heic](bad/heic/cogproof-20261029-E-sig-CA.heic) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.heic](bad/heic/cogproof-20261029-E-uri-CA.heic) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.avif](bad/avif/cogproof-20261029-E-dat-CA.avif) | CA's manifest store on a copy of CA with an 8×8 black square drawn on it | `assertion.bmffHash.mismatch` |
| [cogproof-20261029-E-sig-CA.avif](bad/avif/cogproof-20261029-E-sig-CA.avif) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.avif](bad/avif/cogproof-20261029-E-uri-CA.avif) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
