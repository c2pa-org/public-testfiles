# Audio test files

See the [2.4 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a 3-second 440 Hz sine tone, signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the tone at -6 dB. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, with an unsigned 660 Hz tone mixed in as a component ingredient (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.4) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| MP3 | `mp3` | ID3v2 `GEOB` frame, MIME type `application/c2pa` | `c2pa.hash.data` |
| WAV | `wav` | RIFF `C2PA` chunk, last | `c2pa.hash.data` |
| BWF (WAV with a `bext` chunk) | `bwf` | RIFF `C2PA` chunk, last | `c2pa.hash.data` |
| FLAC (ID3-prefixed) | `flac` | ID3v2 `GEOB` frame, MIME type `application/c2pa` | `c2pa.hash.data` |
| M4A (AAC) | `m4a` | BMFF `uuid` box | `c2pa.hash.bmff.v3` |
| M4A (ALAC) | `alac` | BMFF `uuid` box | `c2pa.hash.bmff.v3` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.mp3](good/mp3/cogproof-20261029-C.mp3) | Valid, no ingredients |
| [cogproof-20261029-CA.mp3](good/mp3/cogproof-20261029-CA.mp3) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.mp3](good/mp3/cogproof-20261029-CAI.mp3) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.wav](good/wav/cogproof-20261029-C.wav) | Valid, no ingredients |
| [cogproof-20261029-CA.wav](good/wav/cogproof-20261029-CA.wav) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.wav](good/wav/cogproof-20261029-CAI.wav) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.wav](good/bwf/cogproof-20261029-C.wav) | Valid, no ingredients |
| [cogproof-20261029-CA.wav](good/bwf/cogproof-20261029-CA.wav) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.wav](good/bwf/cogproof-20261029-CAI.wav) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.flac](good/flac/cogproof-20261029-C.flac) | Valid, no ingredients |
| [cogproof-20261029-CA.flac](good/flac/cogproof-20261029-CA.flac) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.flac](good/flac/cogproof-20261029-CAI.flac) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.m4a](good/m4a/cogproof-20261029-C.m4a) | Valid, no ingredients |
| [cogproof-20261029-CA.m4a](good/m4a/cogproof-20261029-CA.m4a) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.m4a](good/m4a/cogproof-20261029-CAI.m4a) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.m4a](good/alac/cogproof-20261029-C.m4a) | Valid, no ingredients |
| [cogproof-20261029-CA.m4a](good/alac/cogproof-20261029-CA.m4a) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.m4a](good/alac/cogproof-20261029-CAI.m4a) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.mp3](bad/mp3/cogproof-20261029-E-dat-CA.mp3) | One audio byte of CA flipped | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.mp3](bad/mp3/cogproof-20261029-E-sig-CA.mp3) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.mp3](bad/mp3/cogproof-20261029-E-uri-CA.mp3) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.wav](bad/wav/cogproof-20261029-E-dat-CA.wav) | One audio byte of CA flipped | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.wav](bad/wav/cogproof-20261029-E-sig-CA.wav) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.wav](bad/wav/cogproof-20261029-E-uri-CA.wav) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.wav](bad/bwf/cogproof-20261029-E-dat-CA.wav) | One audio byte of CA flipped | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.wav](bad/bwf/cogproof-20261029-E-sig-CA.wav) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.wav](bad/bwf/cogproof-20261029-E-uri-CA.wav) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.flac](bad/flac/cogproof-20261029-E-dat-CA.flac) | One audio byte of CA flipped | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.flac](bad/flac/cogproof-20261029-E-sig-CA.flac) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.flac](bad/flac/cogproof-20261029-E-uri-CA.flac) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.m4a](bad/m4a/cogproof-20261029-E-dat-CA.m4a) | One audio byte of CA flipped | `assertion.bmffHash.mismatch` |
| [cogproof-20261029-E-sig-CA.m4a](bad/m4a/cogproof-20261029-E-sig-CA.m4a) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.m4a](bad/m4a/cogproof-20261029-E-uri-CA.m4a) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.m4a](bad/alac/cogproof-20261029-E-dat-CA.m4a) | One audio byte of CA flipped | `assertion.bmffHash.mismatch` |
| [cogproof-20261029-E-sig-CA.m4a](bad/alac/cogproof-20261029-E-sig-CA.m4a) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.m4a](bad/alac/cogproof-20261029-E-uri-CA.m4a) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

In the FLAC and M4A (AAC) E-dat files the flipped byte falls in a compressed frame, so decoders may report one damaged frame.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
