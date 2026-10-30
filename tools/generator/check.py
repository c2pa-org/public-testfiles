#!/usr/bin/env python3
"""Check the 2.4 test files against the C2PA 2.4 embedding rules, without c2pa-rs.

For each file this parses the container directly and checks where and how the
C2PA Manifest Store is embedded, against the "Embedding manifests" sections of
the C2PA Technical Specification 2.4 (specs-core tag 2.4). It also checks that
the active manifest uses the hard binding the specification requires for the
format, and recomputes `c2pa.hash.data` and the per-file hashes of
`c2pa.hash.collection.data` from the file itself.

The active manifest's assertions are read from manifests/<name>/detailed.json,
which build.py writes. Bad files are expected to fail only their hash or
signature checks, so the embedding checks run on them too.

Usage: python3 check.py [FOLDER...]
"""
import base64
import hashlib
import json
import re
import struct
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent / "2.4"

C2PA_STORE = b"jumb"  # followed by a jumd box whose UUID starts with "c2pa"
BMFF_UUID = bytes.fromhex("D8FEC3D61B0E483C92975828877EC481")


class Fail(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise Fail(msg)


def is_store(data):
    """True if `data` starts with a C2PA Manifest Store superbox."""
    return len(data) > 16 and data[4:8] == b"jumb" and data[12:16] == b"jumd" and data[16:20] == b"c2pa"


# ---------------------------------------------------------------- per-format embedding checks
# Each returns the list of rules checked; raise Fail on the first broken one.


def check_jpeg(data):
    need(data[:2] == b"\xff\xd8", "no SOI")
    pos, app11, segs = 2, [], []
    while pos < len(data) and data[pos] == 0xFF:
        marker = data[pos + 1]
        if marker == 0xDA:  # SOS: entropy-coded data follows
            break
        size = struct.unpack(">H", data[pos + 2 : pos + 4])[0]
        segs.append(marker)
        if marker == 0xEB and data[pos + 4 : pos + 6] == b"JP":
            app11.append((len(segs) - 1, data[pos + 4 : pos + 2 + size]))
        pos += 2 + size
    need(app11, "no APP11 JUMBF segment")
    idx = [i for i, _ in app11]
    need(idx == list(range(idx[0], idx[0] + len(idx))), "APP11 segments are not contiguous")
    # JPEG XT / ISO 19566-5 D.2: CI(2) En(2) Z(4), then LBox+TBox repeated after the first segment.
    first = app11[0][1]
    store = first[8:] + b"".join(seg[16:] for _, seg in app11[1:])
    need(is_store(store), "APP11 payload is not a C2PA Manifest Store")
    return ["Manifest Store in APP11 (JPEG XT) segments", f"{len(app11)} APP11 segment(s), contiguous, before SOS"]


def check_png(data):
    need(data[:8] == b"\x89PNG\r\n\x1a\n", "not PNG")
    pos, chunks = 8, []
    while pos < len(data):
        size, kind = struct.unpack(">I4s", data[pos : pos + 8])
        chunks.append((kind, data[pos + 8 : pos + 8 + size]))
        pos += 12 + size
    kinds = [k for k, _ in chunks]
    need(kinds.count(b"caBX") == 1, f"{kinds.count(b'caBX')} caBX chunks")
    need(is_store(chunks[kinds.index(b"caBX")][1]), "caBX is not a C2PA Manifest Store")
    need(kinds.index(b"caBX") < kinds.index(b"IDAT"), "caBX after IDAT (recommended before)")
    return ["one caBX chunk", "caBX precedes IDAT (recommended)"]


def check_svg(data):
    root = ET.fromstring(data)
    need(root.tag == "{http://www.w3.org/2000/svg}svg", "root is not svg")
    found = root.findall("{http://www.w3.org/2000/svg}metadata/{http://c2pa.org/manifest}manifest")
    need(len(found) == 1, f"{len(found)} c2pa:manifest elements in svg/metadata")
    need(is_store(base64.b64decode(found[0].text.strip())), "c2pa:manifest is not a Base64 Manifest Store")
    need(b'xmlns:c2pa="http://c2pa.org/manifest"' in data[: data.index(b">", data.index(b"<svg"))],
         "xmlns:c2pa not declared on svg (should)")
    return ["Base64 store in svg/metadata/c2pa:manifest", "xmlns:c2pa declared on svg element"]


def check_gif(data):
    need(data[:6] in (b"GIF87a", b"GIF89a"), "not GIF")
    flags = data[10]
    pos = 13 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)
    found = []
    while data[pos] == 0x21:  # extensions before the first image descriptor
        label, pos = data[pos + 1], pos + 2
        block = data[pos + 1 : pos + 1 + data[pos]]
        pos += 1 + data[pos]
        payload, sizes = b"", []
        while data[pos]:
            sizes.append(data[pos])
            payload += data[pos + 1 : pos + 1 + data[pos]]
            pos += 1 + data[pos]
        pos += 1
        if label == 0xFF and block[:8] == b"C2PA_GIF":
            need(block[8:11] == b"\x01\x00\x00", "C2PA_GIF authentication code is not 0x010000")
            need(max(sizes) <= 255, "sub-block larger than 255 bytes")
            found.append(payload)
    need(data[pos] == 0x2C, "C2PA block not found before the first image descriptor")
    need(len(found) == 1, f"{len(found)} C2PA_GIF application extensions")
    need(is_store(found[0]), "C2PA_GIF data is not a C2PA Manifest Store")
    return ["one C2PA_GIF application extension, version 1.0", "after the header, before the first image descriptor"]


def check_tiff(data):
    le = data[:2] == b"II"
    need(data[:2] in (b"II", b"MM"), "not TIFF")
    u16, u32 = ("<H", "<I") if le else (">H", ">I")
    ifds, off = [], struct.unpack(u32, data[4:8])[0]
    while off:
        n = struct.unpack(u16, data[off : off + 2])[0]
        entries = [struct.unpack((u16 + "H" + u32[1] + "4s").replace("H" + u32[1], "H" + u32[1]),
                                 data[off + 2 + 12 * i : off + 14 + 12 * i]) for i in range(n)]
        ifds.append(entries)
        off = struct.unpack(u32, data[off + 2 + 12 * n : off + 6 + 12 * n])[0]
    tagged = [i for i, e in enumerate(ifds) if any(t == 52545 for t, *_ in e)]
    need(len(tagged) == 1, f"tag 52545 in {len(tagged)} main IFDs")
    entry = next(e for e in ifds[tagged[0]] if e[0] == 52545)
    need(entry[1] == 7, f"tag 52545 has type {entry[1]}, not 7 (UNDEFINED)")
    need(tagged[0] == len(ifds) - 1, "C2PA IFD entry is not in the last main IFD")
    if len(ifds) > 2 or (len(ifds) == 2 and len(ifds[-1]) != 1):
        need(len(ifds[-1]) == 1, "C2PA IFD entry is not the only entry in its IFD")
    count, value = entry[2], struct.unpack(u32, entry[3])[0]
    need(is_store(data[value : value + count]), "tag 52545 data is not a C2PA Manifest Store")
    return ["tag 52545 (0xCD41), type 7", f"in the last main IFD ({len(ifds)} main IFD(s))"]


def check_riff(data):
    need(data[:4] == b"RIFF", "not RIFF")
    pos, chunks = 12, []
    end = 8 + struct.unpack("<I", data[4:8])[0]
    need(end == len(data), "RIFF size does not match the file size")
    while pos + 8 <= end:
        cid, size = data[pos : pos + 4], struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        chunks.append((cid, data[pos + 8 : pos + 8 + size]))
        pos += 8 + size + (size & 1)
    ids = [c for c, _ in chunks]
    need(ids.count(b"C2PA") == 1, f"{ids.count(b'C2PA')} C2PA chunks")
    need(ids[-1] == b"C2PA", "C2PA chunk is not the last sub-chunk of the RIFF chunk")
    need(is_store(chunks[-1][1]), "C2PA chunk is not a C2PA Manifest Store")
    return ["one C2PA chunk", "last sub-chunk of the first RIFF chunk"]


def bmff_boxes(data, start=0, end=None):
    pos, end = start, len(data) if end is None else end
    while pos + 8 <= end:
        size, kind = struct.unpack(">I4s", data[pos : pos + 8])
        header = 8
        if size == 1:
            size, header = struct.unpack(">Q", data[pos + 8 : pos + 16])[0], 16
        elif size == 0:
            size = end - pos
        yield kind, pos, header, size
        pos += size


def check_jxl(data):
    need(data[:12] == b"\x00\x00\x00\x0cJXL \r\n\x87\n", "not a JPEG XL container (codestream-only cannot carry a manifest)")
    boxes = list(bmff_boxes(data))
    jumbs = [(p, h, s) for k, p, h, s in boxes if k == b"jumb"]
    need(len(jumbs) == 1, f"{len(jumbs)} top-level jumb boxes (at most one)")
    p, h, s = jumbs[0]
    need(is_store(data[p : p + s]), "the jumb box is not a C2PA Manifest Store")
    return ["JPEG XL box structure", "one top-level jumb superbox holding the Manifest Store"]


def check_bmff(data):
    boxes = list(bmff_boxes(data))
    kinds = [k for k, *_ in boxes]
    need(kinds[0] == b"ftyp", "first box is not ftyp")
    manifests = []
    for i, (kind, pos, header, size) in enumerate(boxes):
        if kind == b"uuid" and data[pos + header : pos + header + 16] == BMFF_UUID:
            body = data[pos + header + 16 : pos + size]
            version_flags, rest = body[:4], body[4:]
            purpose, rest = rest.split(b"\0", 1)
            if purpose == b"manifest":
                need(version_flags == b"\0\0\0\0", "C2PA uuid box version/flags are not 0")
                need(rest[:8] == bytes(8), "merkle offset is not 0 (file has no merkle boxes)")
                need(is_store(rest[8:]), "uuid box data is not a C2PA Manifest Store")
                manifests.append(i)
    need(len(manifests) == 1, f"{len(manifests)} C2PA uuid boxes with box_purpose manifest")
    i = manifests[0]
    need(i > kinds.index(b"ftyp"), "C2PA box is not after ftyp")
    for k in (b"mdat", b"moov"):
        if k in kinds:
            need(i < kinds.index(k), f"C2PA box is not before the first {k.decode()}")
    return ["one C2PA uuid box, box_purpose manifest, merkle offset 0", "after ftyp, before the first mdat and moov"]


def check_id3(data):
    need(data[:3] == b"ID3" and data[3] in (3, 4), "no leading ID3v2.3/2.4 tag")
    end = 10 + (data[6] << 21 | data[7] << 14 | data[8] << 7 | data[9])
    pos, found = 10, []
    while pos + 10 <= end and data[pos] != 0:
        fid, raw = data[pos : pos + 4], data[pos + 4 : pos + 8]
        size = (raw[0] << 21 | raw[1] << 14 | raw[2] << 7 | raw[3]) if data[3] == 4 else struct.unpack(">I", raw)[0]
        body = data[pos + 10 : pos + 10 + size]
        if fid == b"GEOB":
            mime, rest = body[1:].split(b"\0", 1)
            if mime == b"application/c2pa":
                # Filename and description end with a terminator sized by the encoding byte.
                term = b"\0\0" if body[0] in (1, 2) else b"\0"
                for _ in range(2):
                    at = rest.index(term)
                    while term == b"\0\0" and at % 2:
                        at = rest.index(term, at + 1)
                    rest = rest[at + len(term) :]
                found.append(rest)
        pos += 10 + size
    need(len(found) == 1, f"{len(found)} application/c2pa GEOB frames")
    need(is_store(found[0]), "GEOB object is not a C2PA Manifest Store")
    return [f"ID3v2.{data[3]} GEOB, MIME type application/c2pa", "one C2PA GEOB frame"]


def check_font(data):
    need(data[:4] in (b"\0\1\0\0", b"OTTO", b"true"), "not an sfnt font")
    n = struct.unpack(">H", data[4:6])[0]
    tables = {}
    for i in range(n):
        tag, _, off, length = struct.unpack(">4sIII", data[12 + 16 * i : 28 + 16 * i])
        tables[tag] = (off, length)
    need(b"C2PA" in tables, "no C2PA table")
    off, length = tables[b"C2PA"]
    t = data[off : off + length]
    major, minor, uri_off, uri_len, _, store_off, store_len = struct.unpack(">HHIHHII", t[:20])
    need(store_off and is_store(t[store_off : store_off + store_len]), "C2PA table holds no embedded Manifest Store")
    total = sum(struct.unpack(">%dI" % (len(data) // 4), data[: len(data) // 4 * 4]))
    total += int.from_bytes(data[len(data) // 4 * 4 :].ljust(4, b"\0"), "big") if len(data) % 4 else 0
    need(total & 0xFFFFFFFF == 0xB1B0AFBA, "head.checkSumAdjustment does not cover the final font")
    return [f"C2PA table v{major}.{minor} with embedded store", "head.checkSumAdjustment includes the C2PA table"]


def check_pdf(path):
    from pypdf import PdfReader

    reader = PdfReader(path)
    root = reader.trailer["/Root"]
    need("/AF" in root, "catalog has no AF entry")
    specs = [s.get_object() for s in root["/AF"]]
    c2pa = [s for s in specs if s.get("/AFRelationship") == "/C2PA_Manifest"]
    need(len(c2pa) == 1, f"{len(c2pa)} AF file specs with AFRelationship C2PA_Manifest")
    # C2PA 2.4 puts Subtype on the file specification dictionary.
    need(c2pa[0].get("/Subtype") == "/application/c2pa", f"file spec Subtype is {c2pa[0].get('/Subtype')}")
    stream = c2pa[0]["/EF"]["/F"].get_object()
    need(is_store(stream.get_data()), "embedded file is not a C2PA Manifest Store")
    names = root.get("/Names", {}).get("/EmbeddedFiles", {}).get("/Names", [])
    in_tree = any(names[i + 1].idnum == root["/AF"][0].idnum for i in range(0, len(names), 2)
                  if hasattr(names[i + 1], "idnum"))
    annots = [a.get_object() for p in reader.pages for a in p.get("/Annots", [])]
    in_annot = any(a.get("/Subtype") == "/FileAttachment" for a in annots)
    need(in_tree or in_annot, "file spec not referenced from EmbeddedFiles or a FileAttachment annotation")
    return ["embedded file stream, Subtype application/c2pa, AFRelationship C2PA_Manifest",
            "catalog AF entry; referenced from " + ("EmbeddedFiles" if in_tree else "a FileAttachment annotation")]


def check_zip(path):
    z = zipfile.ZipFile(path)
    infos = [i for i in z.infolist() if i.filename == "META-INF/content_credential.c2pa"]
    need(len(infos) == 1, f"{len(infos)} META-INF/content_credential.c2pa entries")
    info = infos[0]
    need(info.compress_type == 0, "content_credential.c2pa is compressed")
    need(info.flag_bits == 0, "content_credential.c2pa general purpose flags are not 0")
    need(is_store(z.read(info)), "content_credential.c2pa is not a C2PA Manifest Store")
    first = z.infolist()[0]
    if path.suffix[1:] in ("epub", "odt", "ods", "odp", "odg"):
        need(first.filename == "mimetype" and first.compress_type == 0, "mimetype is no longer the first, stored entry")
    return ["META-INF/content_credential.c2pa, stored, flags 0", "host format's first entry unchanged"]


def check_html(data):
    head = data[: data.index(b"</head>")]
    scripts = [m for m in re.finditer(rb"<script[^>]*type=\"application/c2pa\"[^>]*>(.*?)</script>", data, re.S)]
    need(len(scripts) == 1, f"{len(scripts)} application/c2pa script elements")
    need(b'rel="c2pa-manifest"' not in data, "both a script and a link element")
    m = scripts[0]
    need(m.end() <= len(head), "script element is not in the head")
    need(is_store(base64.b64decode(m.group(1).strip())), "script content is not a Base64 Manifest Store")
    return ["one script type=application/c2pa in head, Base64 store"], [(m.start(), m.end() - m.start())]


def check_txt(data):
    text = data.decode("utf-8")
    m = re.search("﻿([︀-️\U000e0100-\U000e01ef]+)", text)
    need(m and len(re.findall("﻿[︀-️\U000e0100-\U000e01ef]", text)) == 1, "no single FEFF-prefixed wrapper")
    raw = bytes(ord(c) - 0xFE00 if ord(c) <= 0xFE0F else ord(c) - 0xE0100 + 16 for c in m.group(1))
    need(raw[:8] == b"C2PATXT\0" and raw[8] == 1, "wrapper magic/version is not C2PATXT\\0 v1")
    length = struct.unpack(">I", raw[9:13])[0]
    need(is_store(raw[13 : 13 + length]), "wrapper does not hold a Manifest Store of manifestLength bytes")
    need(len(raw) == 13 + length, f"wrapper has {len(raw) - 13 - length} bytes after jumbfContainer[manifestLength]")
    need(unicodedata.is_normalized("NFC", text), "text is not NFC")
    start = len(text[: m.start()].encode())
    length = len(m.group(0).encode())
    at_end = text[m.end() :].strip() == ""
    return (["FEFF + one contiguous variation-selector wrapper, C2PATXT v1",
             "wrapper at the end of the text (recommended)" if at_end else "wrapper not at the end (should)"],
            [(start, length)])


def check_structured(data, ext):
    begin, end = b"-----BEGIN C2PA MANIFEST-----", b"-----END C2PA MANIFEST-----"
    need(data.count(begin) == 1 and data.count(end) == 1, "not exactly one manifest block")
    b, e = data.index(begin), data.index(end) + len(end)
    lines = data.split(b"\n")
    if ext == "md":
        need(data.startswith(b"---\n"), "no front matter")
        fm_end = data.index(b"\n---\n", 3)
        need(b > 0 and e <= fm_end, "manifest block is not inside the front matter")
        need(data[b - 1 : b] == b"\n" and data[e : e + 1] == b"\n", "delimiters are not on their own lines")
        rules = ["manifest block inside the front matter, delimiters on their own lines"]
    else:
        need(lines[0].startswith(b"<?xml"), "first line is not an XML declaration")
        last = [l for l in lines if l.strip()][-1]
        need(end in last and begin in last, "manifest block is not a single comment line on the last line")
        rules = ["single comment line at the end (first line is the XML declaration)"]
    ref = data[b + len(begin) : e - len(end)].strip()
    need(ref.startswith(b"data:application/c2pa;base64,"), "manifest reference is not a data: URI")
    need(is_store(base64.b64decode(ref.split(b",", 1)[1])), "data: URI is not a Manifest Store")
    rules.append("data:application/c2pa;base64 reference")
    # The exclusion covers "the entire manifest block": the delimiters and what lies between.
    if ext == "md":
        block = (b, e - b + 1)  # through the line terminator
    else:
        line_start = data.rindex(b"\n", 0, b) + 1
        block = (line_start, len(data) - line_start)
    return rules, [block]


# ---------------------------------------------------------------- hard binding


HARD_BINDINGS = {
    "data": "c2pa.hash.data",
    "bmff": "c2pa.hash.bmff.v3",
    "collection": "c2pa.hash.collection.data",
    "boxes": "c2pa.hash.boxes",
}

FAMILIES = {
    "jpeg": ("data", check_jpeg), "png": ("data", check_png), "svg": ("data", check_svg),
    "gif": ("data", check_gif), "tiff": ("data", check_tiff), "dng": ("data", check_tiff),
    "webp": ("data", check_riff), "wav": ("data", check_riff), "bwf": ("data", check_riff),
    "avi": ("data", check_riff), "mp3": ("data", check_id3), "flac": ("data", check_id3),
    "jxl": ("data", check_jxl),
    "m4a": ("bmff", check_bmff), "alac": ("bmff", check_bmff), "mp4": ("bmff", check_bmff),
    "mov": ("bmff", check_bmff), "heic": ("bmff", check_bmff), "avif": ("bmff", check_bmff),
    "ttf": ("boxes", check_font), "otf": ("boxes", check_font),
    "pdf": ("data", "pdf"), "html": ("data", check_html), "txt": ("data", check_txt),
    "md": ("data", "structured"), "xml": ("data", "structured"),
    **{z: ("collection", "zip") for z in ["epub", "docx", "xlsx", "pptx", "odt", "ods", "odp", "odg", "oxps"]},
}


def data_hash_ok(data, assertion):
    excl = sorted((e["start"], e["length"]) for e in assertion.get("exclusions", []))
    h, pos = hashlib.new(assertion.get("alg", "sha256")), 0
    for start, length in excl:
        h.update(data[pos:start])
        pos = start + length
    h.update(data[pos:])
    return base64.b64encode(h.digest()).decode() == assertion["hash"], excl


def collection_ok(path, assertion):
    """Recompute each file hash: local file header + compressed data (+ data descriptor)."""
    data = path.read_bytes()
    z = zipfile.ZipFile(path)
    by_name = {i.filename: i for i in z.infolist()}
    for uri, item in assertion["uris"].items():
        info = by_name[uri]
        off = info.header_offset
        n, m = struct.unpack("<HH", data[off + 26 : off + 30])
        end = off + 30 + n + m + info.compress_size + (16 if info.flag_bits & 8 else 0)
        digest = hashlib.new(assertion.get("alg", "sha256"), data[off:end]).digest()
        if base64.b64encode(digest).decode() != item["hash"]:
            return False, uri
    covered = set(assertion["uris"])
    # Directory entries (such as the META-INF/ that c2pa-rs adds) hold no file data; they
    # are covered by the central directory hash below.
    files = {n for n in by_name if not n.endswith("/")}
    missing = files - covered - {"META-INF/content_credential.c2pa"}
    if missing:
        return False, f"files not covered: {sorted(missing)}"
    # Central directory: every header in full, except the crc-32 of the manifest's own
    # header, then the whole end of central directory record.
    eocd = data.rfind(b"PK\x05\x06")
    pos = struct.unpack("<I", data[eocd + 16 : eocd + 20])[0]
    h = hashlib.new(assertion.get("alg", "sha256"))
    while data[pos : pos + 4] == b"PK\x01\x02":
        n, m, k = struct.unpack("<HHH", data[pos + 28 : pos + 34])
        end = pos + 46 + n + m + k
        header = data[pos:end]
        if data[pos + 46 : pos + 46 + n] == b"META-INF/content_credential.c2pa":
            header = header[:16] + header[20:]
        h.update(header)
        pos = end
    h.update(data[pos:])
    ok = base64.b64encode(h.digest()).decode() == assertion["zip_central_directory_hash"]
    return ok, "" if ok else "zip_central_directory_hash"


def active_assertions(path):
    report = path.parent / "manifests" / path.stem / "detailed.json"
    doc = json.loads(report.read_text())
    return doc["manifests"][doc["active_manifest"]]["assertion_store"]


def check_file(path, folder):
    binding, check = FAMILIES[folder]
    data = path.read_bytes()
    expected_excl = None
    if check == "pdf":
        rules = check_pdf(path)
    elif check == "zip":
        rules = check_zip(path)
    elif check == "structured":
        rules, expected_excl = check_structured(data, folder)
    elif check in (check_html, check_txt):
        rules, expected_excl = check(data)
    else:
        rules = check(data)

    store = active_assertions(path)
    bindings = [k for k in store if k.startswith("c2pa.hash.")]
    need(bindings == [HARD_BINDINGS[binding]], f"hard binding is {bindings}, expected {HARD_BINDINGS[binding]}")
    rules.append(f"hard binding {HARD_BINDINGS[binding]}")

    # Only E-dat changes the bound content; E-sig and E-uri keep CA's content.
    content_intact = "E-dat" not in path.name
    if binding == "data":
        ok, excl = data_hash_ok(data, store["c2pa.hash.data"])
        if expected_excl is not None:
            need(excl == expected_excl, f"exclusions {excl} do not match the embedded block {expected_excl}")
            rules.append("exclusion range is exactly the embedded block")
        need(ok == content_intact, "recomputed c2pa.hash.data " + ("does not match" if content_intact else "matches"))
        rules.append("recomputed c2pa.hash.data " + ("matches" if ok else "does not match"))
    elif binding == "collection":
        ok, why = collection_ok(path, store["c2pa.hash.collection.data"])
        need("zip_central_directory_hash" in store["c2pa.hash.collection.data"], "no zip_central_directory_hash")
        need(ok == content_intact, f"recomputed collection hashes: {why or 'match'}")
        rules.append("recomputed file and central directory hashes " + ("match" if ok else "do not match"))
    return rules


def main():
    folders = set(sys.argv[1:])
    failures = 0
    for path in sorted(ROOT.glob("*/*/*/*-*.*")):
        folder = path.parent.name
        if folders and folder not in folders:
            continue
        try:
            rules = check_file(path, folder)
            print(f"ok   {path.relative_to(ROOT)}: " + "; ".join(rules))
        except Exception as e:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL {path.relative_to(ROOT)}: {type(e).__name__ if not isinstance(e, Fail) else ''}{e}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
