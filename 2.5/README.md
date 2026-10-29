# C2PA 2.5 test files

Test files for the embeddings that version 2.5 of the C2PA Technical Specification adds or changes ("Embedding manifests"). Formats 2.5 leaves unchanged are in [`2.4`](../2.4/README.md).

| Category | Formats |
| -------- | ------- |
| [Image](image/README.md) | JPEG (Exif), JPEG (MPF), BlockFact `.facti` |
| [Audio](audio/README.md) | Standard MIDI File, Ogg Vorbis, BlockFact `.facta` |
| [Video](video/README.md) | BlockFact `.factv` |
| [PDF](pdf/README.md) | PDF (`Subtype` on the embedded file stream) |
| [Text](text/README.md) | Plain text (with deterministic wrapper padding), WebVTT, TTML |
| [Archive](archive/README.md) | WARC |
| [Model](model/README.md) | ONNX, SafeTensors |
| [Data](data/README.md) | Parquet |

Each folder has `good/<format>/` and `bad/<format>/`.

## Naming

Files are named `[supplier]-[YYYYMMDD]-[code].[extension]`, with the same codes and the same six files per format as [2.4](../2.4/README.md#naming):

| File | What it is | Expected result |
| ---- | ---------- | --------------- |
| `C` | A synthesised asset, `c2pa.created` (`algorithmicMedia`) | Valid |
| `CA` | C after one edit, with C as its parent ingredient (`c2pa.opened`, `c2pa.edited`) | Valid |
| `CAI` | As CA, plus an unsigned component ingredient merged in (`c2pa.placed`) | Valid |
| `E-dat-CA` | CA with its content changed after signing | The format's hard-binding mismatch |
| `E-sig-CA` | CA with the last byte of the claim signature flipped | `claimSignature.mismatch` |
| `E-uri-CA` | CA with one letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

The hard-binding mismatch is `assertion.dataHash.mismatch` for most formats, `assertion.boxesHash.mismatch` for Ogg (General Box Hash) and `assertion.collectionHash.mismatch` for WARC (collection data hash). Each category README lists the files and the exact expected failure codes.

Each bad file fails for one reason only. Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.

## How the files were made

All source assets are synthesised by [`tools/generator`](../tools/generator) (`build.py --version 2.5`):

* **Pillow:** Exif and MPF JPEGs.
* **ffmpeg:** Ogg Vorbis (its native, stereo-only Vorbis encoder), and the WAV and MP4 inside `.facta` and `.factv`.
* **The `onnx`, `safetensors` and `pyarrow` packages:** the model and data files.
* **Written directly:** MIDI, text, TTML, PDF, WARC and the BlockFact containers.

They are signed by c2pa-rs (0.92.0-dev) with ES256 and no time-stamp, using the same c2pa-rs test certificate as [2.4](../2.4/README.md#signing-certificate). Several formats need c2pa-rs changes that aren't upstream yet:

| Formats | c2pa-rs change | Feature |
| ------- | -------------- | ------- |
| PDF | contentauth/c2pa-rs#2960 | `pdf` |
| JPEG (Exif, MPF) | contentauth/c2pa-rs#2962 | |
| TTML | contentauth/c2pa-rs#2963 | `unstable_ttml` |
| WARC | contentauth/c2pa-rs#2964 | `unstable_warc` |
| Ogg Vorbis | `mrappard/c2pa-rs-text-support:feat/ogg-vorbis`, on contentauth/c2pa-rs#2768 | `unstable_ogg` |
| BlockFact | `mrappard/c2pa-rs-text-support:feat/blockfact` | `unstable_blockfact` |
| MIDI, plain text, WebVTT | `integration/all-prs` | `unstable_midi`, `unstable_plain_text`, `unstable_structured_text` |

Two of these formats have other implementations under review in c2pa-rs: Ogg in contentauth/c2pa-rs#2073 and BlockFact in contentauth/c2pa-rs#2179. These test files follow the 2.5 text, not one implementation. For example, the Ogg box hash has one box per logical bitstream.

## How the files were checked

* **c2pa-rs:** with the test root as trust anchor, every good file is Trusted and every bad file reports only its expected failure.
* **Against the 2.5 text, without c2pa-rs:** [`tools/generator/check.py --version 2.5`](../tools/generator/check.py) checks each file:
  * **JPEG:** the Exif `APP1` is still first after `SOI`. For MPF, the `APP11` is in the first image and every image still decodes.
  * **PDF:** `Subtype application/c2pa` is on the embedded file stream, with `AFRelationship` `C2PA_Manifest`, the catalog `AF` entry and `EmbeddedFiles`.
  * **MIDI:** one `FF 7F` event with manufacturer `00 43 32`, at delta 0, immediately before End of Track in the designated track.
  * **Ogg:**
    * one logical bitstream whose first packet is `\x00c2pa` + store, from a BOS to an EOS page, with valid page CRCs;
    * every BOS page first;
    * every `Stream-[serial]` box hash recomputed over that stream's pages, in order.
  * **ONNX, SafeTensors and Parquet:** exactly one `c2pa:manifest` entry. For SafeTensors, the header length matches the tensor data.
  * **Plain text:** the wrapper is exactly `3 + (13 + M) * 4 + 6` UTF-8 bytes, padded with `0x00` bytes then up to two `0x10` bytes, and the exclusion includes the `U+FEFF` and the padding.
  * **WebVTT:** the `NOTE` block comes right after the `WEBVTT` header, separated by blank lines.
  * **TTML:** one store at `/tt:tt/tt:head/tt:metadata/c2pa:manifest`, `xmlns:c2pa` on the root, and an exclusion of exactly that element.
  * **BlockFact:** format version 2, and one `C2PA` extension block whose data is the store and exactly the exclusion.
  * **WARC:**
    * the C2PA record last, with `c2pa-provenance`, `application/c2pa` and no `WARC-Target-URI`;
    * every other record hashed whole and keyed by `WARC-Record-ID`, one to one with the collection's `uris`.

  For every data-hash format, the checker confirms that the exclusion range is exactly the embedded block (on files whose content is intact) and recomputes `c2pa.hash.data`.
* **Readers:**
  * **Models and data:** every ONNX file passes `onnx.checker` and runs in the ONNX reference evaluator, every SafeTensors file loads with `safetensors`, and every Parquet file reads with `pyarrow`.
  * **JPEG:** every Exif and MPF image decodes in Pillow.
  * **PDF:** every PDF reads with pypdf.
  * **TTML:** every TTML file parses as XML.
  * **Ogg and BlockFact:** the good Ogg files decode in ffmpeg, which lists the C2PA stream as an unknown stream and skips it. The PNG, WAV and MP4 inside every BlockFact file decode.

## Regenerating

As for [2.4](../2.4/README.md#regenerating), plus the `onnx`, `safetensors`, `pyarrow` and `numpy` Python packages, and a c2pa-rs build with the changes listed above:

```sh
cd tools/generator
cargo build --release
python3 build.py --version 2.5 --date 20261029
python3 check.py --version 2.5
```

## Not included

* **No c2pa-rs handler yet:** append-only text files (logs and JSONL), which use their own checkpoint and segment hash model.
* **XML (comment-line structured text):** the `-----BEGIN C2PA MANIFEST-----` delimiters contain `--`, which XML 1.0 forbids in a comment, so a file signed this way is not well-formed XML (c2pa-org/specs-core#2590). 2.5 also gives two placements for a file that starts with an XML declaration: at the end of the file, and immediately after the declaration.
* **Compressed WARC:** the WARC files here are uncompressed. c2pa-rs#2964 also reads and writes gzip-compressed WARC (`.warc.gz`), but not WARC-zstd.
