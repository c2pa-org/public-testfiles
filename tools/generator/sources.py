"""Synthesise the unsigned source assets for build.py.

Every format has the same five variants:
  created    the original asset (signed as C)
  edited     the original after one simple edit (signed as CA)
  mixed      the edited asset with the component merged in (signed as CAI)
  tampered   the edited asset with one small change (carries CA's manifest in E-dat-CA)
  component  a second asset, used as CAI's component ingredient

Nothing here comes from a third party: images are drawn with Pillow, audio and
video come from ffmpeg's generators, fonts are built with fontTools, and the
documents and text files are written directly.
"""
import io
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

VARIANTS = ["created", "edited", "mixed", "tampered", "component"]


class Kind:
    """A family of formats that share variants and action descriptions."""

    created = edited = mixed = ""

    def write(self, ext, variant, dest):
        raise NotImplementedError


# ---------------------------------------------------------------- raster images


def picture(variant):
    from PIL import Image, ImageDraw, ImageEnhance

    if variant == "component":
        img = Image.new("RGB", (64, 64), "white")
        ImageDraw.Draw(img).ellipse((4, 4, 60, 60), fill=(32, 64, 224))
        return img
    img = Image.new("RGB", (256, 192))
    img.putdata([(x, y * 4 // 3, 128) for y in range(192) for x in range(256)])
    if variant != "created":
        img = ImageEnhance.Brightness(img).enhance(0.8)
    if variant == "mixed":
        img.paste(picture("component"), (96, 64))
    if variant == "tampered":
        ImageDraw.Draw(img).rectangle((16, 16, 23, 23), fill="black")
    return img


def tiff_ifd(entries, data_at):
    """Little-endian TIFF IFD bytes and the out-of-line data placed at `data_at`.

    `entries` is a list of (tag, type, values). Types: 1 BYTE, 2 ASCII, 3 SHORT,
    4 LONG, 5 RATIONAL, 10 SRATIONAL.
    """
    fmt = {1: "B", 2: "B", 3: "H", 4: "I", 5: "II", 10: "ii"}
    size = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 10: 8}
    ifd, extra = struct.pack("<H", len(entries)), b""
    end = data_at + 2 + 12 * len(entries) + 4
    for tag, typ, values in sorted(entries):
        if typ == 2:
            values = list(values.encode() + b"\0")
        flat = [v for pair in values for v in pair] if typ in (5, 10) else values
        raw = struct.pack("<" + fmt[typ][0] * len(flat), *flat)
        count = len(values)
        if len(raw) <= 4:
            value = raw.ljust(4, b"\0")
        else:
            value = struct.pack("<I", end + len(extra))
            extra += raw + (b"\0" if len(raw) & 1 else b"")
        ifd += struct.pack("<HHI", tag, typ, count) + value
    return ifd + struct.pack("<I", 0), extra


def write_dng(img, dest):
    """A minimal DNG 1.4: one uncompressed 16-bit LinearRaw RGB IFD."""
    w, h = img.size
    pixels = b"".join(struct.pack("<3H", *(c * 257 for c in p)) for p in img.getdata())
    entries = [
        (254, 4, [0]), (256, 4, [w]), (257, 4, [h]), (258, 3, [16, 16, 16]), (259, 3, [1]),
        (262, 3, [34892]), (271, 2, "C2PA"), (272, 2, "Synthetic"), (273, 4, [0]), (274, 3, [1]),
        (277, 3, [3]), (278, 4, [h]), (279, 4, [len(pixels)]), (284, 3, [1]),
        (50706, 1, [1, 4, 0, 0]), (50707, 1, [1, 1, 0, 0]), (50708, 2, "C2PA Synthetic"),
        (50721, 10, [(1, 1), (0, 1), (0, 1), (0, 1), (1, 1), (0, 1), (0, 1), (0, 1), (1, 1)]),
        (50728, 5, [(1, 1), (1, 1), (1, 1)]), (50778, 3, [21]),
    ]
    # Lay out: header, IFD and its data, then the strip.
    ifd, extra = tiff_ifd(entries, 8)
    strip = 8 + len(ifd) + len(extra)
    entries = [(t, ty, [strip]) if t == 273 else (t, ty, v) for t, ty, v in entries]
    ifd, extra = tiff_ifd(entries, 8)
    dest.write_bytes(b"II*\0" + struct.pack("<I", 8) + ifd + extra + pixels)


class Image(Kind):
    created = "Synthesised test image"
    edited = "Reduced the brightness"
    mixed = "Placed a blue circle"

    def write(self, ext, variant, dest):
        img = picture(variant)
        if ext == "dng":
            write_dng(img, dest)
        elif ext in ("heic", "jxl"):
            with tempfile.TemporaryDirectory() as tmp:
                png = Path(tmp) / "src.png"
                img.save(png)
                if ext == "heic":
                    subprocess.run(["sips", "-s", "format", "heic", str(png), "--out", str(dest)], check=True, stdout=subprocess.DEVNULL)
                else:
                    # --container=1: a codestream-only JPEG XL cannot carry a manifest.
                    run("cjxl", "--quiet", "--container=1", "-d", "1", str(png), str(dest))
        else:
            options = {
                "jpg": dict(format="JPEG", quality=90),
                "png": dict(format="PNG"),
                "gif": dict(format="GIF"),
                "tif": dict(format="TIFF"),
                "webp": dict(format="WEBP", lossless=True),
                "avif": dict(format="AVIF", quality=80),
            }[ext]
            img.save(dest, **options)


class Svg(Kind):
    created = Image.created
    edited = Image.edited
    mixed = Image.mixed

    def write(self, ext, variant, dest):
        circle = '<circle cx="128" cy="96" r="28" fill="#2040e0"/>'
        if variant == "component":
            body = '<circle cx="32" cy="32" r="28" fill="#2040e0"/>'
            size = 'width="64" height="64"'
        else:
            opacity = "" if variant == "created" else ' fill-opacity="0.8"'
            x = "17" if variant == "tampered" else "16"
            body = (f'<rect width="256" height="192" fill="#4080c0"{opacity}/>'
                    f'<text x="{x}" y="40" font-family="sans-serif" font-size="24">C2PA test image</text>')
            if variant == "mixed":
                body += circle
            size = 'width="256" height="192"'
        dest.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n'
                        f'<svg xmlns="http://www.w3.org/2000/svg" {size}>{body}</svg>\n')


# ---------------------------------------------------------------- audio and video


def run(*cmd):
    subprocess.run(cmd, check=True)


def ffmpeg(*args):
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args)


AUDIO_CODECS = {
    "mp3": ["-c:a", "libmp3lame", "-b:a", "128k", "-write_xing", "0"],
    "wav": ["-c:a", "pcm_s16le"],
    "flac": ["-c:a", "flac", "-sample_fmt", "s16"],
    "m4a": ["-c:a", "aac", "-b:a", "128k"],
    "alac": ["-c:a", "alac", "-sample_fmt", "s16p"],
}


def add_bext(data):
    """Insert a minimal Broadcast Wave `bext` chunk (EBU Tech 3285 v1) after `fmt `."""
    bext = bytearray(602)
    bext[0:30] = b"C2PA test BWF".ljust(30, b"\0")
    bext[256:268] = b"cogproof".ljust(12, b"\0")  # Originator
    bext[320:330] = b"2026-10-29"  # OriginationDate
    bext[330:338] = b"00:00:00"  # OriginationTime
    bext[346:348] = struct.pack("<H", 1)  # Version
    chunk = b"bext" + struct.pack("<I", len(bext)) + bext
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos : pos + 4], struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        pos += 8 + size + (size & 1)
        if cid == b"fmt ":
            out = data[:pos] + chunk + data[pos:]
            return out[:4] + struct.pack("<I", len(out) - 8) + out[8:]
    raise AssertionError("no fmt chunk")


class Audio(Kind):
    created = "Synthesised test tone"
    edited = "Reduced the volume by 6 dB"
    mixed = "Mixed in a second tone"

    def __init__(self, codec, bwf=False):
        self.codec, self.bwf = codec, bwf

    def write(self, ext, variant, dest):
        freq = 660 if variant == "component" else 440
        tone = f"sine=frequency={freq}:duration=3"
        if variant in ("created", "component"):
            args = ["-f", "lavfi", "-i", tone]
        elif variant == "mixed":
            graph = "[0:a]volume=-6dB[a];[a][1:a]amix=inputs=2:duration=first"
            args = ["-f", "lavfi", "-i", tone, "-f", "lavfi", "-i", "sine=frequency=660:duration=3",
                    "-filter_complex", graph]
        else:
            args = ["-f", "lavfi", "-i", tone, "-af", "volume=-6dB"]
        ffmpeg(*args, "-ac", "1", "-ar", "44100", "-map_metadata", "-1", "-fflags", "+bitexact",
               *AUDIO_CODECS[self.codec], str(dest))
        if self.bwf:
            dest.write_bytes(add_bext(dest.read_bytes()))


VIDEO_CODECS = {
    "mp4": ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "28"],
    "mov": ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "veryfast", "-crf", "28"],
    "avi": ["-c:v", "mjpeg", "-q:v", "5"],
}


class Video(Kind):
    created = "Synthesised test video"
    edited = Image.edited
    mixed = Image.mixed

    def write(self, ext, variant, dest):
        src = "testsrc2=size=320x240:rate=25:duration=2"
        if variant == "component":
            args = ["-f", "lavfi", "-i", "color=c=0x2040e0:size=64x64:rate=25:duration=2"]
        else:
            filters = {
                "created": "null",
                "edited": "eq=brightness=-0.1",
                "tampered": "eq=brightness=-0.1,drawbox=x=16:y=16:w=8:h=8:color=black:t=fill",
            }
            if variant == "mixed":
                args = ["-f", "lavfi", "-i", src, "-f", "lavfi", "-i",
                        "color=c=0x2040e0:size=64x64:rate=25:duration=2",
                        "-filter_complex", "[0:v]eq=brightness=-0.1[v];[v][1:v]overlay=128:88"]
            else:
                args = ["-f", "lavfi", "-i", src, "-vf", filters[variant]]
        ffmpeg(*args, "-map_metadata", "-1", "-fflags", "+bitexact", *VIDEO_CODECS[ext], str(dest))


# ---------------------------------------------------------------- fonts


class Font(Kind):
    created = "Synthesised test font"
    edited = "Scaled glyph A"
    mixed = "Added glyph B"

    def write(self, ext, variant, dest):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.t2CharStringPen import T2CharStringPen
        from fontTools.pens.ttGlyphPen import TTGlyphPen

        def square(pen, inset):
            pen.moveTo((100 + inset, inset))
            pen.lineTo((100 + inset, 700 - inset))
            pen.lineTo((600 - inset, 700 - inset))
            pen.lineTo((600 - inset, inset))
            pen.closePath()

        def triangle(pen):
            pen.moveTo((100, 0))
            pen.lineTo((350, 700))
            pen.lineTo((600, 0))
            pen.closePath()

        inset = 0 if variant == "created" else 100
        shapes = {".notdef": None}
        if variant == "component":
            shapes["B"] = triangle
        else:
            shapes["A"] = lambda pen: square(pen, inset + (1 if variant == "tampered" else 0))
            if variant == "mixed":
                shapes["B"] = triangle

        cff = ext == "otf"
        name = "C2PA Component" if variant == "component" else "C2PA Test"
        fb = FontBuilder(1000, isTTF=not cff)
        fb.setupGlyphOrder(list(shapes))
        fb.setupCharacterMap({ord(g): g for g in shapes if len(g) == 1})
        glyphs = {}
        for glyph, draw in shapes.items():
            pen = T2CharStringPen(700, None) if cff else TTGlyphPen(None)
            if draw:
                draw(pen)
            glyphs[glyph] = pen.getCharString() if cff else pen.glyph()
        if cff:
            fb.setupCFF(name.replace(" ", ""), {"FullName": name}, glyphs, {})
        else:
            fb.setupGlyf(glyphs)
        fb.setupHorizontalMetrics({g: (700, 100) for g in shapes})
        fb.setupHorizontalHeader(ascent=800, descent=-200)
        fb.setupNameTable({"familyName": name, "styleName": "Regular"})
        fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
        fb.setupPost()
        fb.save(str(dest))


# ---------------------------------------------------------------- documents and text

TEXT = {
    "created": ["C2PA test document."],
    "edited": ["C2PA test document, edited."],
    "mixed": ["C2PA test document, edited.", "Component paragraph."],
    "tampered": ["C2PA test document, edites."],
    "component": ["Component paragraph."],
}


class Document(Kind):
    created = "Synthesised test document"
    edited = "Edited the text"
    mixed = "Added a component paragraph"

    def write(self, ext, variant, dest):
        paras = TEXT[variant]
        if ext == "pdf":
            dest.write_bytes(pdf(paras))
        elif ext in ZIPS:
            dest.write_bytes(zip_document(ext, paras))
        else:
            dest.write_bytes(TEXTS[ext](paras).encode())


def pdf(paras):
    lines = "".join(f"BT /F1 18 Tf 72 {720 - 30 * i} Td ({p}) Tj ET\n" for i, p in enumerate(paras))
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        "/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(lines)} >>\nstream\n{lines}endstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n", []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;")


def ooxml(ext, paras):
    ct = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    ns = "http://schemas.openxmlformats.org"
    rel = f"{ns}/officeDocument/2006/relationships"
    doc_rel = f"{rel}/officeDocument"
    if ext == "docx":
        body = "".join(f"<w:p><w:r><w:t>{esc(p)}</w:t></w:r></w:p>" for p in paras)
        parts = {
            "word/document.xml": f'{ct}<w:document xmlns:w="{ns}/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>',
        }
        overrides = {"/word/document.xml": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"}
        main = "word/document.xml"
    elif ext == "xlsx":
        rows = "".join(f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{esc(p)}</t></is></c></row>'
                       for i, p in enumerate(paras, 1))
        sml = f"{ns}/spreadsheetml/2006/main"
        parts = {
            "xl/workbook.xml": f'{ct}<workbook xmlns="{sml}" xmlns:r="{rel}"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
            "xl/_rels/workbook.xml.rels": f'{ct}<Relationships xmlns="{ns}/package/2006/relationships"><Relationship Id="rId1" Type="{rel}/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
            "xl/worksheets/sheet1.xml": f'{ct}<worksheet xmlns="{sml}"><sheetData>{rows}</sheetData></worksheet>',
        }
        overrides = {
            "/xl/workbook.xml": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
            "/xl/worksheets/sheet1.xml": "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        }
        main = "xl/workbook.xml"
    else:
        parts, overrides = pptx_parts(ct, ns, rel, paras)
        main = "ppt/presentation.xml"
    types = "".join(f'<Override PartName="{k}" ContentType="{v}"/>' for k, v in overrides.items())
    files = {
        "[Content_Types].xml": f'{ct}<Types xmlns="{ns}/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        f'<Default Extension="xml" ContentType="application/xml"/>{types}</Types>',
        "_rels/.rels": f'{ct}<Relationships xmlns="{ns}/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{doc_rel}" Target="{main}"/></Relationships>',
        **parts,
    }
    return files, []


def pptx_parts(ct, ns, rel, paras):
    pml, dml = f"{ns}/presentationml/2006/main", f"{ns}/drawingml/2006/main"
    rels_ns = f"{ns}/package/2006/relationships"
    xmlns = f'xmlns:a="{dml}" xmlns:r="{rel}" xmlns:p="{pml}"'
    tree = ('<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr/>{}</p:spTree></p:cSld>')
    text = "".join(f"<a:p><a:r><a:t>{esc(p)}</a:t></a:r></a:p>" for p in paras)
    shape = ('<p:sp><p:nvSpPr><p:cNvPr id="2" name="Text"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
             '<p:spPr><a:xfrm><a:off x="914400" y="914400"/><a:ext cx="7315200" cy="1828800"/></a:xfrm>'
             f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr><p:txBody><a:bodyPr/>{text}</p:txBody></p:sp>')
    theme = (f'<a:theme xmlns:a="{dml}" name="C2PA"><a:themeElements>'
             '<a:clrScheme name="C2PA">' + "".join(
                 f'<a:{c}><a:srgbClr val="{v}"/></a:{c}>' for c, v in [
                     ("dk1", "000000"), ("lt1", "FFFFFF"), ("dk2", "1F497D"), ("lt2", "EEECE1"),
                     ("accent1", "4F81BD"), ("accent2", "C0504D"), ("accent3", "9BBB59"),
                     ("accent4", "8064A2"), ("accent5", "4BACC6"), ("accent6", "F79646"),
                     ("hlink", "0000FF"), ("folHlink", "800080")]) + '</a:clrScheme>'
             '<a:fontScheme name="C2PA"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
             '<a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
             '<a:fmtScheme name="C2PA"><a:fillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 +
             '</a:fillStyleLst><a:lnStyleLst>' + '<a:ln><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>' * 3 +
             '</a:lnStyleLst><a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 +
             '</a:effectStyleLst><a:bgFillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 +
             '</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>')

    def rels(*targets):
        return (f'{ct}<Relationships xmlns="{rels_ns}">' + "".join(
            f'<Relationship Id="rId{i}" Type="{rel}/{t}" Target="{target}"/>'
            for i, (t, target) in enumerate(targets, 1)) + "</Relationships>")

    parts = {
        "ppt/presentation.xml": f'{ct}<p:presentation {xmlns}>'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>'
        '<p:sldSz cx="9144000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>',
        "ppt/_rels/presentation.xml.rels": rels(("slideMaster", "slideMasters/slideMaster1.xml"),
                                                ("slide", "slides/slide1.xml"), ("theme", "theme/theme1.xml")),
        "ppt/slides/slide1.xml": f'{ct}<p:sld {xmlns}>{tree.format(shape)}</p:sld>',
        "ppt/slides/_rels/slide1.xml.rels": rels(("slideLayout", "../slideLayouts/slideLayout1.xml")),
        "ppt/slideLayouts/slideLayout1.xml": f'{ct}<p:sldLayout {xmlns} type="blank">{tree.format("")}</p:sldLayout>',
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": rels(("slideMaster", "../slideMasters/slideMaster1.xml")),
        "ppt/slideMasters/slideMaster1.xml": f'{ct}<p:sldMaster {xmlns}>{tree.format("")}'
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
        'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>',
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": rels(("slideLayout", "../slideLayouts/slideLayout1.xml"),
                                                             ("theme", "../theme/theme1.xml")),
        "ppt/theme/theme1.xml": ct + theme,
    }
    pre = "application/vnd.openxmlformats-officedocument.presentationml"
    overrides = {
        "/ppt/presentation.xml": f"{pre}.presentation.main+xml",
        "/ppt/slides/slide1.xml": f"{pre}.slide+xml",
        "/ppt/slideLayouts/slideLayout1.xml": f"{pre}.slideLayout+xml",
        "/ppt/slideMasters/slideMaster1.xml": f"{pre}.slideMaster+xml",
        "/ppt/theme/theme1.xml": "application/vnd.openxmlformats-officedocument.theme+xml",
    }
    return parts, overrides


ODF_TYPES = {
    "odt": ("text", lambda ps: "".join(f"<text:p>{esc(p)}</text:p>" for p in ps)),
    "ods": ("spreadsheet", lambda ps: '<table:table table:name="Sheet1">' + "".join(
        f'<table:table-row><table:table-cell office:value-type="string"><text:p>{esc(p)}</text:p>'
        "</table:table-cell></table:table-row>" for p in ps) + "</table:table>"),
    "odp": ("presentation", lambda ps: '<draw:page draw:name="Slide1">' + DRAW_FRAME.format(
        "".join(f"<text:p>{esc(p)}</text:p>" for p in ps)) + "</draw:page>"),
    "odg": ("graphics", lambda ps: '<draw:page draw:name="Page1">' + DRAW_FRAME.format(
        "".join(f"<text:p>{esc(p)}</text:p>" for p in ps)) + "</draw:page>"),
}
DRAW_FRAME = ('<draw:frame svg:x="2cm" svg:y="2cm" svg:width="20cm" svg:height="5cm">'
              "<draw:text-box>{}</draw:text-box></draw:frame>")


def odf(ext, paras):
    kind, body = ODF_TYPES[ext]
    mime = f"application/vnd.oasis.opendocument.{kind}"
    ns = 'xmlns:{0}="urn:oasis:names:tc:opendocument:xmlns:{1}:1.0"'
    xmlns = " ".join(ns.format(p, n) for p, n in [
        ("office", "office"), ("text", "text"), ("table", "table"), ("draw", "drawing"),
        ("svg", "svg-compatible"), ("manifest", "manifest")])
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    files = {
        "content.xml": f'{head}<office:document-content {xmlns} office:version="1.3">'
        f"<office:body><office:{kind}>{body(paras)}</office:{kind}></office:body></office:document-content>",
        "META-INF/manifest.xml": f'{head}<manifest:manifest {ns.format("manifest", "manifest")} manifest:version="1.3">'
        f'<manifest:file-entry manifest:full-path="/" manifest:media-type="{mime}"/>'
        '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        "</manifest:manifest>",
    }
    return files, [("mimetype", mime)]


def epub(paras):
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    body = "".join(f"<p>{esc(p)}</p>" for p in paras)
    xhtml = 'xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"'
    files = {
        "META-INF/container.xml": f'{head}<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
        '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
        "OEBPS/content.opf": f'{head}<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">'
        '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">urn:uuid:6f1d3a52-2b7e-4c1a-9a0e-6c2a00000001</dc:identifier>'
        '<dc:title>C2PA test document</dc:title><dc:language>en</dc:language>'
        '<meta property="dcterms:modified">2026-10-29T00:00:00Z</meta></metadata>'
        '<manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
        '<item id="ch1" href="chapter1.xhtml" media-type="application/xhtml+xml"/></manifest>'
        '<spine><itemref idref="ch1"/></spine></package>',
        "OEBPS/nav.xhtml": f'{head}<html {xhtml}><head><title>Contents</title></head><body>'
        '<nav epub:type="toc"><ol><li><a href="chapter1.xhtml">Chapter 1</a></li></ol></nav></body></html>',
        "OEBPS/chapter1.xhtml": f'{head}<html {xhtml}><head><title>Chapter 1</title></head><body>{body}</body></html>',
    }
    return files, [("mimetype", "application/epub+zip")]


def oxps(paras):
    """OpenXPS with one page; each paragraph is a coloured bar (no fonts needed)."""
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xps = "http://schemas.openxps.org/oxps/v1.0"
    colours = {"C2PA test document.": "#FF4080C0", "C2PA test document, edited.": "#FF305F90",
               "Component paragraph.": "#FF2040E0", "C2PA test document, edites.": "#FF305F91"}
    bars = "".join(f'<Path Fill="{colours[p]}" Data="M 96,{96 + 64 * i} L 700,{96 + 64 * i} '
                   f'L 700,{136 + 64 * i} L 96,{136 + 64 * i} Z"/>' for i, p in enumerate(paras))
    files = {
        "[Content_Types].xml": f'{head}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="fdseq" ContentType="application/vnd.ms-package.xps-fixeddocumentsequence+xml"/>'
        '<Default Extension="fdoc" ContentType="application/vnd.ms-package.xps-fixeddocument+xml"/>'
        '<Default Extension="fpage" ContentType="application/vnd.ms-package.xps-fixedpage+xml"/></Types>',
        "_rels/.rels": f'{head}<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxps.org/oxps/v1.0/fixedrepresentation" '
        'Target="/FixedDocumentSequence.fdseq"/></Relationships>',
        "FixedDocumentSequence.fdseq": f'{head}<FixedDocumentSequence xmlns="{xps}">'
        '<DocumentReference Source="/Documents/1/FixedDocument.fdoc"/></FixedDocumentSequence>',
        "Documents/1/FixedDocument.fdoc": f'{head}<FixedDocument xmlns="{xps}">'
        '<PageContent Source="/Documents/1/Pages/1.fpage"/></FixedDocument>',
        "Documents/1/Pages/1.fpage": f'{head}<FixedPage xmlns="{xps}" Width="816" Height="1056" xml:lang="en">'
        f"{bars}</FixedPage>",
    }
    return files, []


def zip_document(ext, paras):
    if ext in ("docx", "xlsx", "pptx"):
        files, stored = ooxml(ext, paras)
    elif ext in ODF_TYPES:
        files, stored = odf(ext, paras)
    elif ext == "epub":
        files, stored = epub(paras)
    else:
        files, stored = oxps(paras)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, data in stored:
            z.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), data, zipfile.ZIP_STORED)
        for name, data in files.items():
            z.writestr(zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0)), data, zipfile.ZIP_DEFLATED)
    return out.getvalue()


ZIPS = ["epub", "docx", "xlsx", "pptx", "odt", "ods", "odp", "odg", "oxps"]

def vtt_time(seconds):
    return f"00:00:{seconds:02d}.000"


TEXTS = {
    "txt": lambda ps: "\n\n".join(ps) + "\n",
    "vtt": lambda ps: "WEBVTT\n\n" + "\n\n".join(
        f"{vtt_time(2 * i)} --> {vtt_time(2 * i + 2)}\n{p}" for i, p in enumerate(ps)) + "\n",
    "md": lambda ps: "---\ntitle: C2PA test document\n---\n\n# C2PA test document\n\n" + "\n\n".join(ps) + "\n",
    "html": lambda ps: '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    "<title>C2PA test document</title>\n</head>\n<body>\n"
    + "".join(f"<p>{esc(p)}</p>\n" for p in ps) + "</body>\n</html>\n",
}


class Table(Kind):
    """A Parquet table with one row per paragraph."""

    created = Document.created
    edited = Document.edited
    mixed = Document.mixed

    def write(self, ext, variant, dest):
        import pyarrow as pa
        import pyarrow.parquet as pq

        paras = TEXT[variant]
        table = pa.table({"line": list(range(1, len(paras) + 1)), "text": paras})
        pq.write_table(table, dest, compression="none", write_statistics=False)


# ---------------------------------------------------------------- MIDI


def vlq(n):
    out = [n & 0x7F]
    while n > 0x7F:
        n >>= 7
        out.insert(0, (n & 0x7F) | 0x80)
    return bytes(out)


SCALE = [60, 62, 64, 65, 67, 69, 71, 72]  # C major, quarter notes


def midi_track(notes, velocity):
    body = b"\x00\xff\x51\x03\x07\xa1\x20"  # tempo: 500000 us per quarter note (120 bpm)
    for note, vel in zip(notes, velocity):
        body += b"\x00" + bytes([0x90, note, vel]) + vlq(480) + bytes([0x80, note, 0])
    body += b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(body)) + body


class Midi(Kind):
    created = "Synthesised test sequence"
    edited = "Halved the note velocities"
    mixed = "Added a second track"

    def write(self, ext, variant, dest):
        loud, quiet = [100] * len(SCALE), [50] * len(SCALE)
        fifth = [n + 7 for n in SCALE]
        tracks = {
            "created": [(SCALE, loud)],
            "edited": [(SCALE, quiet)],
            "mixed": [(SCALE, quiet), (fifth, loud)],
            "tampered": [(SCALE, quiet[:3] + [51] + quiet[4:])],
            "component": [(fifth, loud)],
        }[variant]
        header = struct.pack(">HHH", 0 if len(tracks) == 1 else 1, len(tracks), 480)
        dest.write_bytes(b"MThd" + struct.pack(">I", 6) + header +
                         b"".join(midi_track(n, v) for n, v in tracks))


# ---------------------------------------------------------------- machine-learning models


def weights(variant):
    """The tensors of each variant: `weight`, plus `bias` from the component."""
    import numpy as np

    w = np.arange(1, 9, dtype=np.float32).reshape(2, 4)
    if variant == "component":
        return {"bias": np.full(4, 0.25, dtype=np.float32)}
    if variant != "created":
        w = w * 0.5
    if variant == "tampered":
        w[0, 0] += 0.125
    tensors = {"weight": w}
    if variant == "mixed":
        tensors.update(weights("component"))
    return tensors


class Model(Kind):
    created = "Synthesised test model"
    edited = "Scaled the weights by 0.5"
    mixed = "Added a bias from a component model"

    def write(self, ext, variant, dest):
        tensors = weights(variant)
        if ext == "safetensors":
            from safetensors.numpy import save_file

            save_file(tensors, str(dest))
            return
        import onnx
        from onnx import TensorProto, helper, numpy_helper

        # y = x @ weight (+ bias): x is [1, 2], y is [1, 4].
        nodes, out = [], "x"
        if "weight" in tensors:
            nodes.append(helper.make_node("MatMul", ["x", "weight"], ["xw"]))
            out = "xw"
        if "bias" in tensors:
            nodes.append(helper.make_node("Add", [out, "bias"], ["y"]))
        else:
            nodes.append(helper.make_node("Identity", [out], ["y"]))
        x_shape = [1, 4] if "weight" not in tensors else [1, 2]
        graph = helper.make_graph(
            nodes, "c2pa_test",
            [helper.make_tensor_value_info("x", TensorProto.FLOAT, x_shape)],
            [helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 4])],
            [numpy_helper.from_array(t, name) for name, t in tensors.items()],
        )
        model = helper.make_model(graph, producer_name="c2pa test", opset_imports=[helper.make_opsetid("", 13)])
        model.ir_version = 8
        onnx.checker.check_model(model)
        dest.write_bytes(model.SerializeToString())
