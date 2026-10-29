# C2PA 2.4 test files

Test files for the embeddings in version 2.4 of the C2PA Technical Specification ("Embedding manifests"), one folder per format:

| Category | Formats |
| -------- | ------- |
| [Audio](audio/README.md) | MP3, WAV, BWF, FLAC, M4A (AAC), M4A (ALAC) |
| [Image](image/README.md) | JPEG, PNG, SVG, GIF, TIFF, DNG, WebP, JPEG XL, HEIC, AVIF |
| [Video](video/README.md) | MP4, MOV, AVI |
| [Font](font/README.md) | TrueType, OpenType (CFF) |
| [PDF](pdf/README.md) | PDF |
| [Document](document/README.md) | EPUB, DOCX, XLSX, PPTX, ODT, ODS, ODP, ODG, OpenXPS |
| [Text](text/README.md) | Markdown (structured text, front matter) |
| [HTML](html/README.md) | HTML |

Each folder has `good/<format>/` and `bad/<format>/`.

## Naming

Files are named `[supplier]-[YYYYMMDD]-[code].[extension]`, with the codes used for the [2.2 image test files](../2.2/image/README.md):

| Code | Meaning |
| ---- | ------- |
| **C** | Claim |
| **A** | Parent ingredient (acquisition) |
| **I** | Ingredient |
| **E-dat-** | Error: Hard binding hash mismatch |
| **E-sig-** | Error: Signature did not validate |
| **E-uri-** | Error: An assertion has been tampered with (URI hash mismatch) |

Every format has the same six CogProof files (`cogproof-20261029-*`):

| File | What it is | Expected result |
| ---- | ---------- | --------------- |
| `C` | A synthesised asset, `c2pa.created` (`algorithmicMedia`) | Valid |
| `CA` | C after one edit, with C as its parent ingredient (`c2pa.opened`, `c2pa.edited`) | Valid |
| `CAI` | As CA, plus an unsigned component ingredient merged in (`c2pa.placed`) | Valid |
| `E-dat-CA` | CA with its content changed after signing | The format's hard-binding mismatch |
| `E-sig-CA` | CA with the last byte of the claim signature flipped | `claimSignature.mismatch` |
| `E-uri-CA` | CA with one letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only: E-sig and E-uri change only the active manifest (not the parent's), and E-dat changes only the content. For audio, E-dat flips one byte of audio in CA. For every other format, E-dat is CA's manifest store, unchanged, embedded in a copy of CA with one small change (an 8×8 square, one glyph point, one letter). Each category README lists the files and the exact expected failure codes.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.

## How the files were made

All source assets are synthesised, so the files carry no third-party content: images are drawn with Pillow, audio and video come from ffmpeg's generators, fonts are built with fontTools, and the PDF, ZIP-based documents, Markdown and HTML are written directly by [`tools/generator`](../tools/generator).

They are signed by c2pa-rs (0.92.0-dev) with ES256 and no time-stamp. HTML and structured text use c2pa-rs's `unstable_html` and `unstable_structured_text` features, and PDF its `pdf` feature.

### Signing certificate

The signer is the c2pa-rs test certificate (`sdk/tests/fixtures/certs/es256.pub`), valid until 2030-08-26. It is not on any production trust list, so validators report `signingCredential.untrusted` unless they are given its test root (`sdk/tests/fixtures/certs/trust/test_cert_root_bundle.pem`). The reports in `manifests/` were made with that root as the trust anchor.

## How the files were checked

* **c2pa-rs:** with the test root as trust anchor, every good file is Trusted and every bad file reports only its expected failure.
* **Against the 2.4 text, without c2pa-rs:** [`tools/generator/check.py`](../tools/generator/check.py) parses each container itself and checks the 2.4 placement rules for its format (for example: `APP11` segments contiguous and before `SOS`; `caBX` before `IDAT`; the `C2PA` RIFF chunk last; tag 52545 of type 7 in the last IFD; the `C2PA_GIF` block before the first image; the C2PA `uuid` box after `ftyp` and before `moov` and `mdat`; one top-level `jumb` box in JPEG XL; `AFRelationship` `C2PA_Manifest` in the PDF catalog `AF`; `META-INF/content_credential.c2pa` stored with flags 0; the HTML `script` in `head`; the Markdown block inside the front matter). It also checks that each manifest uses the hard binding 2.4 requires for the format. It recomputes `c2pa.hash.data` from the exclusion ranges, and checks that those ranges cover exactly the embedded block for HTML and Markdown. For ZIP formats it recomputes each file hash and the `zip_central_directory_hash`.
* **Readers:** every file opens in an ordinary reader for its format (Pillow, `sips`, `djxl`, ffmpeg, fontTools, pypdf, Python's `zipfile`).

## Regenerating

The generator needs ffmpeg (with libmp3lame, libx264 and libsvtav1), cjxl, macOS `sips` (for HEIC), Pillow, fontTools and pypdf, and c2pa-rs checked out at `../c2pa-rs-integration`, next to this repository (see `tools/generator/Cargo.toml`).

```sh
cd tools/generator
cargo build --release
python3 build.py --date 20261029
python3 check.py
```

ECDSA signatures are randomised, so a rebuild produces different bytes with the same validation results.

## Not included

* **Ogg Vorbis:** c2pa-rs has no Ogg handler.
* **Plain text (`.txt`):** c2pa-rs pads the `C2PATextManifestWrapper` after the manifest store. This is "Deterministic Wrapper Padding", which was added in 2.5. The 2.4 wrapper syntax ends at `jumbfContainer[manifestLength]`.
* **Comment-line structured text (for example `.xml`):** when c2pa-rs places the manifest block at the end of the file, its exclusion range also covers the line feed before the block, which belongs to the original content. Neither 2.4 nor 2.5 describes this.
* **MIDI:** added in 2.5.
