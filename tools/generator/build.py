#!/usr/bin/env python3
"""Regenerate the test files in 2.4 and 2.5.

For each format this script:
  1. synthesises the unsigned source variants (see sources.py)
  2. signs them with `make_testfile` (c2pa-rs) into the good/ files:
       C    created asset
       CA   edited asset, with C as its parent ingredient
       CAI  as CA, plus an unsigned component ingredient merged in
  3. damages copies of CA for the bad/ files:
       E-dat-CA  content changed after signing (hard-binding hash mismatch)
       E-sig-CA  last byte of the claim signature flipped
       E-uri-CA  one letter of the c2pa.edited description changed (hashed URI mismatch)
  4. writes manifests/<name>/manifest_store.json and detailed.json for each file

For sampled audio, E-dat-CA flips one byte of audio in the signed file. For every
other format it is CA's manifest store, unchanged, embedded in the
"tampered" source: the edited asset with one small change.

ECDSA signatures are randomised, so a rebuild produces different bytes with
the same validation results.

Usage: python3 build.py [--version 2.4|2.5] [--supplier NAME] [--date YYYYMMDD] [--only FOLDER[,FOLDER...]]
"""
import argparse
import datetime
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

import sources as s

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
C2PA_RS = (HERE / "../../../c2pa-rs-integration").resolve()
CERTS = C2PA_RS / "sdk/tests/fixtures/certs"

# (category, folder, extension, kind)
FORMATS_2_4 = [
    ("audio", "mp3", "mp3", s.Audio("mp3")),
    ("audio", "wav", "wav", s.Audio("wav")),
    ("audio", "flac", "flac", s.Audio("flac")),
    ("audio", "m4a", "m4a", s.Audio("m4a")),
    ("audio", "alac", "m4a", s.Audio("alac")),
    ("audio", "bwf", "wav", s.Audio("wav", bwf=True)),
    ("image", "jpeg", "jpg", s.Image()),
    ("image", "png", "png", s.Image()),
    ("image", "svg", "svg", s.Svg()),
    ("image", "gif", "gif", s.Image()),
    ("image", "tiff", "tif", s.Image()),
    ("image", "dng", "dng", s.Image()),
    ("image", "webp", "webp", s.Image()),
    ("image", "jxl", "jxl", s.Image()),
    ("image", "heic", "heic", s.Image()),
    ("image", "avif", "avif", s.Image()),
    ("video", "mp4", "mp4", s.Video()),
    ("video", "mov", "mov", s.Video()),
    ("video", "avi", "avi", s.Video()),
    ("font", "ttf", "ttf", s.Font()),
    ("font", "otf", "otf", s.Font()),
    ("pdf", "pdf", "pdf", s.Document()),
    *[("document", ext, ext, s.Document()) for ext in s.ZIPS],
    # Plain text (.txt) and comment-line structured text (.xml) are left out:
    # c2pa-rs pads the text wrapper (a 2.5 rule) and widens the end-of-file
    # exclusion to the preceding line feed (in no spec version).
    ("text", "md", "md", s.Document()),
    ("html", "html", "html", s.Document()),
]

# Embeddings added in 2.5 that c2pa-rs can write.
FORMATS_2_5 = [
    ("audio", "midi", "mid", s.Midi()),
    ("text", "txt", "txt", s.Document()),
    ("text", "vtt", "vtt", s.Document()),
    ("model", "onnx", "onnx", s.Model()),
    ("model", "safetensors", "safetensors", s.Model()),
    ("data", "parquet", "parquet", s.Table()),
]

FORMATS = {"2.4": FORMATS_2_4, "2.5": FORMATS_2_5}


# ---------------------------------------------------------------- audio byte flips


def flip(data, offset):
    data[offset] ^= 0xFF
    return data


def manifest_store_range(data):
    """(start, end) of the first C2PA Manifest Store superbox in the file."""
    at = data.find(b"jumdc2pa")
    assert at >= 12, "no C2PA Manifest Store found"
    start = at - 12
    return start, start + struct.unpack(">I", data[start : start + 4])[0]


def audio_offset(ext, data):
    """An offset inside the hashed audio, well away from the manifest store."""
    if ext == "wav":
        pos = 12
        while pos + 8 <= len(data):
            cid, size = data[pos : pos + 4], struct.unpack("<I", data[pos + 4 : pos + 8])[0]
            if cid == b"data":
                return pos + 8 + size // 2
            pos += 8 + size + (size & 1)
    elif ext == "m4a":
        pos = 0
        while pos + 8 <= len(data):
            size, kind = struct.unpack(">I4s", data[pos : pos + 8])
            if kind == b"mdat":
                return pos + size // 2
            pos += size
    else:
        # MP3 and FLAC carry the manifest in a leading ID3 tag.
        return len(data) - 512
    raise AssertionError(f"no audio found in {ext} file")


def flip_audio(ext, data):
    offset = audio_offset(ext, data)
    start, end = manifest_store_range(data)
    assert not start <= offset < end, "offset falls inside the manifest store"
    return flip(data, offset)


# ---------------------------------------------------------------- build


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", choices=FORMATS, default="2.4")
    parser.add_argument("--supplier", default="cogproof")
    parser.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    parser.add_argument("--only", help="comma-separated format folders to build (default: all)")
    parser.add_argument("--signer", type=Path, default=HERE / "target/release/make_testfile")
    args = parser.parse_args()
    only = set(args.only.split(",")) if args.only else None

    env = dict(os.environ, C2PA_CERTS=str(CERTS))

    def run(*cmd):
        subprocess.run([str(args.signer), *map(str, cmd)], check=True, env=env)

    root = REPO / args.version
    for category, folder, ext, kind in FORMATS[args.version]:
        if only and folder not in only:
            continue
        good, bad = root / category / "good" / folder, root / category / "bad" / folder
        for d in (good, bad):
            shutil.rmtree(d / "manifests", ignore_errors=True)
            for old in d.glob(f"{args.supplier}-*.{ext}"):
                old.unlink()
            d.mkdir(parents=True, exist_ok=True)

        def name(code):
            return f"{args.supplier}-{args.date}-{code}.{ext}"

        c, ca, cai = good / name("C"), good / name("CA"), good / name("CAI")
        with tempfile.TemporaryDirectory(prefix="c2pa-testfile-") as tmp:
            src = {v: Path(tmp) / f"{v}.{ext}" for v in s.VARIANTS}
            for variant, path in src.items():
                kind.write(ext, variant, path)

            run("create", src["created"], c, kind.created)
            run("edit", src["edited"], c, ca, kind.edited)
            run("edit", src["mixed"], c, cai, f"{kind.edited}; {kind.mixed}", src["component"])

            if isinstance(kind, s.Audio):
                (bad / name("E-dat-CA")).write_bytes(flip_audio(ext, bytearray(ca.read_bytes())))
            else:
                run("embed", ca, src["tampered"], bad / name("E-dat-CA"))
        run("embed", ca, ca, bad / name("E-sig-CA"), "sig")
        run("embed", ca, ca, bad / name("E-uri-CA"), "uri", kind.edited)

        for d in (good, bad):
            for asset in sorted(d.glob(f"{args.supplier}-*.{ext}")):
                run("read", asset, d / "manifests" / asset.stem)


if __name__ == "__main__":
    main()
