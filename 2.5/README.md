# C2PA 2.5 test files

Test files for the embeddings that version 2.5 of the C2PA Technical Specification adds ("Embedding manifests"). Formats already covered by 2.4 are in [`2.4`](../2.4/README.md), except where 2.5 changed the rules (see [Not included](#not-included)).

| Category | Formats |
| -------- | ------- |
| [Audio](audio/README.md) | Standard MIDI File |
| [Text](text/README.md) | Plain text (with deterministic wrapper padding), WebVTT |
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
| `E-dat-CA` | CA's manifest store on a copy of CA with one small change | `assertion.dataHash.mismatch` |
| `E-sig-CA` | CA with the last byte of the claim signature flipped | `claimSignature.mismatch` |
| `E-uri-CA` | CA with one letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only. Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.

## How the files were made

All source assets are synthesised by [`tools/generator`](../tools/generator) (`build.py --version 2.5`): MIDI and text are written directly, ONNX with the `onnx` package, SafeTensors with `safetensors`, and Parquet with `pyarrow`.

They are signed by c2pa-rs (0.92.0-dev) with ES256 and no time-stamp, using the same c2pa-rs test certificate as [2.4](../2.4/README.md#signing-certificate). MIDI, plain text and structured text use c2pa-rs's `unstable_midi`, `unstable_plain_text` and `unstable_structured_text` features.

## How the files were checked

* **c2pa-rs:** with the test root as trust anchor, every good file is Trusted and every bad file reports only its expected failure.
* **Against the 2.5 text, without c2pa-rs:** [`tools/generator/check.py --version 2.5`](../tools/generator/check.py) checks each file:
  * **MIDI:** one `FF 7F` event with manufacturer `00 43 32`, at delta 0, immediately before End of Track in the designated track.
  * **ONNX, SafeTensors and Parquet:** exactly one `c2pa:manifest` entry. For SafeTensors, the header length matches the tensor data.
  * **Plain text:** the wrapper is exactly `3 + (13 + M) * 4 + 6` UTF-8 bytes, padded with `0x00` bytes then up to two `0x10` bytes, and the exclusion includes the `U+FEFF` and the padding.
  * **WebVTT:** the `NOTE` block comes right after the `WEBVTT` header, separated by blank lines.

  For every format, the checker also confirms that the exclusion range is exactly the Base64 value or embedded block, and recomputes `c2pa.hash.data`.
* **Readers:** every ONNX file passes `onnx.checker` and runs in the ONNX reference evaluator, every SafeTensors file loads with `safetensors`, and every Parquet file reads with `pyarrow`.

## Regenerating

As for [2.4](../2.4/README.md#regenerating), plus the `onnx`, `safetensors`, `pyarrow` and `numpy` Python packages:

```sh
cd tools/generator
cargo build --release
python3 build.py --version 2.5 --date 20261029
python3 check.py --version 2.5
```

## Not included

These 2.5 embeddings have no c2pa-rs handler yet: TTML, Ogg Vorbis, `.facti`/`.facta`/`.factv`, WARC, and append-only text files (logs and JSONL).

These need a change in c2pa-rs first:

* **PDF:** 2.5 moves `Subtype application/c2pa` from the file specification dictionary to the embedded file stream dictionary. c2pa-rs still writes it on the file specification dictionary, which is the 2.4 rule.
* **Comment-line structured text at the end of a file (for example `.xml`):** the exclusion range also covers the line feed before the block, which belongs to the original content. 2.5 doesn't describe this, as in 2.4.

Not yet made: **JPEG Exif-compressed and MPF files**, which 2.5 adds rules for. The generator does not yet make such sources.
