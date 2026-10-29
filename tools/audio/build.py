#!/usr/bin/env python3
"""Regenerate the audio test files in 2.4/audio.

For each format (MP3, WAV, FLAC, M4A) this script:
  1. synthesises source audio with ffmpeg (sine tones)
  2. signs it with `make_audio` (c2pa-rs) into the good/ files:
       C    created asset
       CA   edited asset, with C as its parent ingredient
       CAI  as CA, plus an unsigned component ingredient mixed in
  3. damages a copy of CA at the byte level for the bad/ files:
       E-dat-CA  one byte of audio flipped (hard-binding hash mismatch)
       E-sig-CA  one byte of the claim signature flipped
       E-uri-CA  one byte of the actions assertion changed (hashed URI mismatch)
  4. writes manifests/<name>/manifest_store.json and detailed.json for each file

ECDSA signatures are randomised, so a rebuild produces different bytes with
the same validation results.

Usage: python3 build.py [--supplier NAME] [--date YYYYMMDD] [--only FORMAT]
"""
import argparse
import datetime
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
AUDIO = REPO / "2.4" / "audio"
C2PA_RS = (HERE / "../../../c2pa-rs-integration").resolve()
CERTS = C2PA_RS / "sdk/tests/fixtures/certs"

FORMATS = ["mp3", "wav", "flac", "m4a"]
SECONDS = 3
CREATED = "Synthesised test tone"
EDITED = "Reduced the volume by 6 dB"
MIXED = "Mixed in a second tone"


# ---------------------------------------------------------------- sources


ENCODERS = {
    "mp3": ["-c:a", "libmp3lame", "-b:a", "128k", "-write_xing", "0"],
    "wav": ["-c:a", "pcm_s16le"],
    "flac": ["-c:a", "flac", "-sample_fmt", "s16"],
    "m4a": ["-c:a", "aac", "-b:a", "128k"],
}


def ffmpeg(ext, *args, dest):
    """Run ffmpeg to a 44.1 kHz mono file, dropping all metadata."""
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, "-ac", "1", "-ar", "44100",
         "-map_metadata", "-1", "-fflags", "+bitexact", *ENCODERS[ext], str(dest)],
        check=True,
    )


def tone(ext, freq, dest):
    ffmpeg(ext, "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={SECONDS}", dest=dest)


def edited(ext, signed_c, dest):
    ffmpeg(ext, "-i", str(signed_c), "-af", "volume=-6dB", dest=dest)


def mixed(ext, signed_c, component, dest):
    graph = "[0:a]volume=-6dB[a];[a][1:a]amix=inputs=2:duration=first"
    ffmpeg(ext, "-i", str(signed_c), "-i", str(component), "-filter_complex", graph, dest=dest)


# ---------------------------------------------------------------- tampering


def flip(data, offset):
    data[offset] ^= 0xFF
    return data


def manifest_store_range(data):
    """(start, end) of the first C2PA Manifest Store superbox in the file."""
    at = data.find(b"jumdc2pa")
    assert at >= 12, "no C2PA Manifest Store found"
    start = at - 12
    return start, start + struct.unpack(">I", data[start : start + 4])[0]


def box_after_jumd(data, label):
    """(start, end) of the content box that follows the last jumd with `label`."""
    at = data.rfind(label.encode() + b"\0")
    assert at > 0, f"no {label} box"
    jumd = at - 25  # LBox, TBox, 16-byte UUID, toggles
    assert data[jumd + 4 : jumd + 8] == b"jumd"
    start = jumd + struct.unpack(">I", data[jumd : jumd + 4])[0]
    return start, start + struct.unpack(">I", data[start : start + 4])[0]


def bad_signature(data):
    """Flip the last byte of the active manifest's COSE_Sign1, which is the signature."""
    start, end = box_after_jumd(data, "c2pa.signature")
    assert data[start + 4 : start + 8] == b"cbor"
    return flip(data, end - 1)


def bad_assertion(data):
    """Change one letter of the active manifest's c2pa.edited description."""
    at = data.rfind(EDITED.encode())
    assert at > 0, "no edited description"
    data[at] ^= 0x20  # "R" -> "r": still valid CBOR, different hash
    return data


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


def bad_data(ext):
    def mutate(data):
        offset = audio_offset(ext, data)
        start, end = manifest_store_range(data)
        assert not start <= offset < end, "offset falls inside the manifest store"
        return flip(data, offset)

    return mutate


# ---------------------------------------------------------------- build


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--supplier", default="cogproof")
    parser.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    parser.add_argument("--only", choices=FORMATS, help="build only this format")
    parser.add_argument("--signer", type=Path, default=HERE / "target/release/make_audio")
    args = parser.parse_args()

    env = dict(os.environ, C2PA_CERTS=str(CERTS))

    def run(*cmd):
        subprocess.run([str(args.signer), *map(str, cmd)], check=True, env=env)

    for ext in FORMATS:
        if args.only and args.only != ext:
            continue
        good, bad = AUDIO / "good" / ext, AUDIO / "bad" / ext
        for d in (good, bad):
            shutil.rmtree(d / "manifests", ignore_errors=True)
            for old in d.glob(f"{args.supplier}-*.{ext}"):
                old.unlink()
            d.mkdir(parents=True, exist_ok=True)

        def name(code):
            return f"{args.supplier}-{args.date}-{code}.{ext}"

        c, ca, cai = good / name("C"), good / name("CA"), good / name("CAI")
        with tempfile.TemporaryDirectory(prefix="c2pa-audio-") as tmp:
            tmp = Path(tmp)
            created, component = tmp / f"created.{ext}", tmp / f"component.{ext}"
            tone(ext, 440, created)
            tone(ext, 660, component)
            run("create", created, c, CREATED)

            edited(ext, c, tmp / f"edited.{ext}")
            run("edit", tmp / f"edited.{ext}", c, ca, EDITED)

            mixed(ext, c, component, tmp / f"mixed.{ext}")
            run("edit", tmp / f"mixed.{ext}", c, cai, f"{EDITED}; {MIXED}", component)

        signed = ca.read_bytes()
        for code, mutate in [("E-dat-CA", bad_data(ext)), ("E-sig-CA", bad_signature), ("E-uri-CA", bad_assertion)]:
            (bad / name(code)).write_bytes(mutate(bytearray(signed)))

        for d in (good, bad):
            for asset in sorted(d.glob(f"{args.supplier}-*.{ext}")):
                run("read", asset, d / "manifests" / asset.stem)


if __name__ == "__main__":
    main()
