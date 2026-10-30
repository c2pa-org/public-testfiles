# C2PA Live Segment Validation (Per-segment C2PA Manifest Box method)

This document describes how to validate the live video segments in this
directory. They use the **Per-segment C2PA Manifest Box method** defined in
C2PA 2.3 and 2.4, Section 19.3. Every media segment carries its own C2PA Manifest in a
`uuid` box, and each segment is validated on its own, with continuity checked
against the previous segment. This method does not use session keys or
`verifiable-segment-info` (Section 19.4).

Continuity between segments uses an entity-specific continuity method,
`com.ezdrm.anchor-chain`, which Section 19.3.2 allows ("Implementers may define
additional continuity methods"). Each segment carries a continuity token
computed over its `moof` and `mdat` boxes with an IV that is chained from the
nearest anchor segment. Section 19.3.1 also allows this: "Claim generators may
derive additional per-segment validation values (e.g., anchor-point-based
chaining values) from segment hashes and embed them in the Manifest."

The segments also carry a CAWG identity assertion
(`cawg.identity`), which binds a named signer to the segment's hard binding.

## Contents

- [Specification versions](#specification-versions)
- [Files](#files)
- [Segment structure](#segment-structure)
- [Generation flow](#generation-flow)
- [Validation flow](#validation-flow)
- [Validation steps](#validation-steps)
- [Missing segments](#missing-segments)
- [Validation rubric](#validation-rubric)
- [Checking this test set](#checking-this-test-set)
- [Known deviations in the current files](#known-deviations-in-the-current-files)

## Specification versions

These files target **C2PA 2.3 and C2PA 2.4**. All section numbers and status
codes in this document are the same in both versions.

The parts of the specification that these files exercise are unchanged between
2.3 and 2.4:

| Area | Sections | 2.3 to 2.4 |
|:--|:--|:--|
| Per-segment C2PA Manifest Box method and live video segment assertion | 19.3, 19.3.1, 19.3.2 | Identical |
| Live video validation | 19.7.1, 19.7.2 | Identical |
| Live video status codes (`livevideo.*`) | 15 | Identical |
| BMFF hashing (`c2pa.hash.bmff.v3`) | 9.2.3, A.5 | Identical |
| Claims, manifest identifiers, time-stamps, labels | 10, 8, 10.3.2.5, 6.2 | Identical |

2.4 adds wording for dynamically packaged content to the live video
introduction (19.1, 19.2), and allows broadcast "push" streams to repeat an
initialization segment without a C2PA Manifest Box. Neither changes how these
files are generated or validated. The files are stored under `2.3/`, following
this repository's convention that validators compliant with later versions
also accept earlier test files.

## Files

| Folder | Files | Content | Format |
|:--|:--|:--|:--|
| `m4s/` | `init.mp4` and `seg_728690.m4s` to `seg_728709.m4s` (20 segments, two full anchor cycles: 728690 to 728699 and 728700 to 728709) | Clear | `c2pa.claim.v2`, `c2pa.livevideo.segment` with `continuityMethod` `com.ezdrm.anchor-chain`, `cawg.identity` |

`example_c2pa_manifest.json` is a decoded dump of the manifest store of
`m4s/seg_728690.m4s` (the first anchor segment). CBOR byte strings are shown
as `b64:` followed by their Base64 encoding.

## Segment structure

Each segment is a self-contained fMP4 media segment. The C2PA Manifest Box is a
`uuid` box with the C2PA user type `d8fec3d6-1b0e-483c-9297-5828877ec481`,
placed directly after the file or segment type box.

```mermaid
flowchart LR
  ftyp["ftyp / styp<br/>(excluded from hash)"] --> uuid["uuid: C2PA Manifest Box<br/>(excluded from hash)"]
  uuid --> sidx["sidx"]
  sidx --> moof["moof"]
  moof --> mdat["mdat"]

  subgraph manifest["Active C2PA Manifest (c2pa.claim.v2)"]
    direction TB
    a1["c2pa.hash.bmff.v3<br/>hard binding over this segment"]
    a2["c2pa.livevideo.segment<br/>sequenceNumber, streamId,<br/>continuityMethod = com.ezdrm.anchor-chain,<br/>anchor-chain fields"]
    a3["cawg.identity<br/>cawg.x509.cose over<br/>the c2pa.hash.bmff.v3 reference"]
    a4["c2pa.actions.v2 (c2pa.created),<br/>stds.schema-org.CreativeWork"]
    a5["claim signature<br/>(X.509, RFC 3161 time-stamp)"]
  end
  uuid -.contains.- manifest
  moof -.input to.- tok["continuity token<br/>(moof + mdat bytes)"]
  mdat -.input to.- tok
```

The `c2pa.hash.bmff.v3` assertion excludes the C2PA `uuid` box and the
`ftyp`, `styp`, `mfra`, `free` and `skip` boxes. In `m4s/seg_728690.m4s` the
claim lists `c2pa.hash.bmff.v3` as a created assertion, and
`c2pa.actions.v2`, `stds.schema-org.CreativeWork`, `c2pa.livevideo.segment`
and `cawg.identity` as gathered assertions.

The initialization segment `m4s/init.mp4` contains `ftyp`, a C2PA Manifest Box
and `moov`, and no `mdat`.

## Generation flow

```mermaid
sequenceDiagram
  participant E as Encoder / packager
  participant G as Claim generator
  participant T as Time-stamp authority
  participant C as Origin / CDN
  E->>G: init segment (ftyp, moov)
  G->>C: signed init.mp4
  E->>G: media segment N (sidx, moof, mdat)
  Note over G: derive IV from the anchor segment,<br/>compute continuity token over moof + mdat
  Note over G: build c2pa.livevideo.segment<br/>sequenceNumber = N, streamId,<br/>continuityMethod = com.ezdrm.anchor-chain
  Note over G: insert C2PA uuid box,<br/>compute c2pa.hash.bmff.v3<br/>with post-embed offsets
  Note over G: sign cawg.identity over the<br/>c2pa.hash.bmff.v3 reference
  G->>T: time-stamp request for claim signature
  T-->>G: RFC 3161 token
  G->>C: signed segment N
```

## Validation flow

```mermaid
flowchart TD
  S([Segment received]) --> I{Initialization<br/>segment?}
  I -- yes --> IM{Contains mdat?}
  IM -- yes --> F1[/"livevideo.init.invalid"/]
  IM -- no --> OKI([Init segment OK])
  I -- no --> B{C2PA Manifest Box<br/>present?}
  B -- no --> F2[/"livevideo.segment.invalid"/]
  B -- yes --> V{"Chapter 15 validation:<br/>signature, trust, time-stamp,<br/>c2pa.hash.bmff.v3"}
  V -- fail --> F3[/"livevideo.manifest.invalid"/]
  V -- pass --> CW{"cawg.identity<br/>valid?"}
  CW -- no --> F9[/"identity assertion invalid<br/>(reported separately)"/]
  CW -- yes --> L{"c2pa.livevideo.segment<br/>present?"}
  L -- no --> F4[/"not a live segment manifest"/]
  L -- yes --> Q{"sequenceNumber greater than previous<br/>and streamId equal to previous?"}
  Q -- no --> F5[/"livevideo.assertion.invalid"/]
  Q -- yes --> CM{continuityMethod}
  CM -- missing or not supported --> F6[/"livevideo.continuityMethod.invalid"/]
  CM -- c2pa.manifestId --> P{"previousManifestId equal to<br/>previous manifest ID?"}
  P -- no --> F7[/"livevideo.segment.invalid"/]
  P -- yes --> OK([Segment valid])
  CM -- com.ezdrm.anchor-chain --> K{"computed token equal to<br/>continuityToken?"}
  K -- yes --> OK
  K -- no --> F8[/"livevideo.segment.invalid,<br/>reset IV cache"/]
```

The first segment of a session has no previous segment, so the "previous"
comparisons are skipped for it.

## Validation steps

### Step 1: Check the box structure

Parse the top-level boxes of the segment. A media segment is expected to
contain a file or segment type box, a C2PA `uuid` box, `sidx`, then one `moof`
followed by one `mdat`.

- An initialization segment (one that contains `moov`) MUST NOT contain `mdat`,
  otherwise it fails with `livevideo.init.invalid`.
- A media segment without a C2PA Manifest Box fails with
  `livevideo.segment.invalid`.

```ts
type Box = { type: string; start: number; end: number; usertype?: string };

const C2PA_UUID = "d8fec3d61b0e483c92975828877ec481";

function readBoxes(data: Uint8Array): Box[] {
  const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
  const boxes: Box[] = [];
  let pos = 0;
  while (pos + 8 <= data.length) {
    let size = view.getUint32(pos);
    const type = String.fromCharCode(...data.subarray(pos + 4, pos + 8));
    let header = 8;
    if (size === 1) {
      size = Number(view.getBigUint64(pos + 8)); // 64-bit largesize
      header = 16;
    } else if (size === 0) {
      size = data.length - pos; // box extends to end of file
    }
    if (size < header || pos + size > data.length) {
      throw new Error(`malformed box '${type}' at offset ${pos}`);
    }
    const box: Box = { type, start: pos, end: pos + size };
    if (type === "uuid") {
      box.usertype = [...data.subarray(pos + header, pos + header + 16)]
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("");
    }
    boxes.push(box);
    pos += size;
  }
  return boxes;
}

const boxes = readBoxes(segment);
const isInit = boxes.some((b) => b.type === "moov");
const hasManifestBox = boxes.some((b) => b.type === "uuid" && b.usertype === C2PA_UUID);
if (isInit && boxes.some((b) => b.type === "mdat")) fail("livevideo.init.invalid");
if (!isInit && !hasManifestBox) fail("livevideo.segment.invalid");
```

### Step 2: Validate the C2PA Manifest (Chapter 15)

Validate the manifest with a conforming C2PA validator. This covers the claim
signature, the certificate chain against the validator's trust list, the
time-stamp, and the `c2pa.hash.bmff.v3` hard binding over the segment bytes.
If this fails, the segment fails with `livevideo.manifest.invalid`.

```ts
import { createC2pa } from "@contentauth/c2pa-web";
import wasmSrc from "@contentauth/c2pa-web/resources/c2pa.wasm?url";

const c2pa = await createC2pa({ wasmSrc, settings: toolkitSettings });
const reader = await c2pa.reader.fromBlob("video/mp4", new Blob([segment]));
const store = await reader.manifestStore();
const active = store.manifests[store.active_manifest];
if (store.validation_state === "Invalid") {
  fail("livevideo.manifest.invalid", store.validation_status);
}
```

`toolkitSettings` should load the trust list that the deployment uses. A
manifest signed with a certificate that is not on that list is reported with
`signingCredential.untrusted`.

### Step 3: Validate the CAWG identity assertion

Segments in `m4s/` carry a `cawg.identity` assertion with `sig_type`
`cawg.x509.cose`. Its `signer_payload.referenced_assertions` lists the
`c2pa.hash.bmff.v3` assertion by URL and hash, so the identity signature covers
the segment's hard binding. Validate it according to the CAWG Identity
Assertion specification: check that each referenced assertion hash matches,
verify the COSE signature, and check the signer's X.509 certificate against
the validator's CAWG trust configuration. c2pa-rs based validators report the
result alongside the C2PA validation results.

An invalid identity assertion is reported as an identity failure. It does not
change the result of the live video checks in Steps 4 to 6.

### Step 4: Read the live video segment assertion

Find the `c2pa.livevideo.segment` assertion in the active manifest. For
`m4s/seg_728690.m4s` it contains:

| Field | Value | Meaning |
|:--|:--|:--|
| `sequenceNumber` | `728690` | Monotonically increasing segment number (Section 19.3.2) |
| `streamId` | `https://undefined.s3.amazonaws.com/us-east-1` | Identifier for the whole live stream (see [Stream identifier](#stream-identifier)) |
| `continuityMethod` | `com.ezdrm.anchor-chain` | Entity-specific continuity method |
| `anchorSegmentIndex` | `10` | An anchor segment occurs every N segments |
| `streamIdHash` | `o1q7p/yXXB+e2q1RXBCUfg==` | Base64 of the first 16 bytes of `SHA-256(UTF-8(streamId))`. Used as a string as the seed for the anchor IV |
| `certHash` | `dHGNvgfyQjWSbjROm73g/w==` | Base64 string. Its first 16 characters, as UTF-8 bytes, are the AES-128 key |
| `continuityToken` | `z+yZ/5aCTd+WVSRXk+8uRA==` | Expected token for this segment, Base64 |

```ts
const seg = active.assertions.find((a) => a.label === "c2pa.livevideo.segment")?.data;
```

#### Stream identifier

Section 19.3.2 allows `streamId` to be "any string that uniquely identifies
the live video stream, such as a UUID or a URL". The generator creates its own
`streamId` at the start of the workflow and resolves it in this order:

1. **MPEG-DASH:** the `id` attribute of the root `MPD` element, for example
   `<MPD id="dash-session-123">` gives `dash-session-123`.
2. **HLS:** the `VALUE` of an `#EXT-X-SESSION-DATA` tag with `DATA-ID`
   `"com.publisher.stream-id"`, for example
   `#EXT-X-SESSION-DATA:DATA-ID="com.publisher.stream-id",VALUE="hls-live-456"`
   gives `hls-live-456`.
3. **Fallback:** a canonicalized form of the manifest URL, with query
   parameters and the port removed, for example
   `https://cdn.example.com/live/stream_01/manifest.m3u8?auth=token` gives
   `https://cdn.example.com/live/stream_01/manifest.m3u8`.

`streamIdHash` is derived from the resolved value:
`Base64(SHA-256(UTF-8(streamId))[0..15])`. For the `m4s/` set,
`SHA-256("https://undefined.s3.amazonaws.com/us-east-1")` gives
`o1q7p/yXXB+e2q1RXBCUfg==`, which matches the manifest. A validator may
recompute `streamIdHash` from `streamId` and reject the segment if they differ.


### Step 5: Apply the Section 19.7.2 checks

Keep the state of the previous segment of the same stream (`prev.seq`,
`prev.streamId`, `prev.manifestId`). Then:

1. `seg.sequenceNumber` MUST be greater than `prev.seq`. Otherwise:
   `livevideo.assertion.invalid`.
2. `seg.streamId` MUST equal `prev.streamId`. Otherwise:
   `livevideo.assertion.invalid`.
3. `seg.continuityMethod` MUST be present. Otherwise:
   `livevideo.continuityMethod.invalid`.
4. If `continuityMethod` is `c2pa.manifestId`, `seg.previousManifestId` MUST be
   present (otherwise `livevideo.continuityMethod.invalid`) and MUST equal
   `prev.manifestId` (otherwise `livevideo.segment.invalid`).
5. If `continuityMethod` is `com.ezdrm.anchor-chain`, validate the continuity
   token ([Step 6](#step-6-validate-the-anchor-chained-continuity-token)).
6. If `continuityMethod` is any other value the validator does not support:
   `livevideo.continuityMethod.invalid`.

```ts
if (prev) {
  if (!(seg.sequenceNumber > prev.seq) || seg.streamId !== prev.streamId) {
    fail("livevideo.assertion.invalid");
  }
}
switch (seg.continuityMethod) {
  case undefined:
    fail("livevideo.continuityMethod.invalid");
    break;
  case "c2pa.manifestId":
    if (!seg.previousManifestId) fail("livevideo.continuityMethod.invalid");
    if (prev && seg.previousManifestId !== prev.manifestId) fail("livevideo.segment.invalid");
    break;
  case "com.ezdrm.anchor-chain":
    await checkAnchorChain(seg, segment, boxes); // Step 6
    break;
  default:
    fail("livevideo.continuityMethod.invalid");
}
prev = { seq: seg.sequenceNumber, streamId: seg.streamId, manifestId: store.active_manifest };
```

### Step 6: Validate the anchor-chained continuity token

```mermaid
flowchart LR
  A["anchor = floor(sequenceNumber / anchorSegmentIndex) x anchorSegmentIndex"] --> H["anchorIV = SHA-256(UTF-8(streamIdHash + decimal(anchor)))[0..15]"]
  H --> INC["IV = anchorIV + (sequenceNumber - anchor)<br/>(128-bit big-endian increment)"]
  INC --> ENC["AES-128-CBC, PKCS#7<br/>key = UTF-8(certHash[0..15])<br/>plaintext = moof + mdat"]
  ENC --> LAST["token = Base64(last 16 bytes of ciphertext)"]
  LAST --> CMP{"token equal to continuityToken?"}
```

1. **Extract the input bytes.** Concatenate the raw bytes of the `moof` box and
   the `mdat` box that follows it, including their headers. No other box is
   part of the input. For encrypted segments these are the encrypted bytes as
   stored in the file.
2. **Derive the anchor IV.** `anchor = floor(sequenceNumber /
   anchorSegmentIndex) * anchorSegmentIndex`. `anchorIV` is the first 16 bytes
   of `SHA-256(UTF-8(streamIdHash + String(anchor)))`. `streamIdHash` is used
   as its Base64 string, not decoded.
3. **Advance to the segment IV.** Increment `anchorIV` as a 128-bit big-endian
   integer `sequenceNumber - anchor` times. A validator that holds the IV of the
   previous segment (`sequenceNumber - 1`) and is not at an anchor may
   increment that IV once instead.
4. **Compute the token.** Encrypt the input bytes with AES-128-CBC and PKCS#7
   padding, using `UTF-8(certHash.slice(0, 16))` as the key and the segment IV.
   The token is the Base64 encoding of the last 16 bytes of the ciphertext
   (a CBC-MAC).
5. **Compare.** If the computed token equals `continuityToken`, the check
   passes. Otherwise the segment fails with `livevideo.segment.invalid`, and
   any cached IV is cleared so the next anchor segment starts a clean chain.

```ts
const utf8 = (s: string) => new TextEncoder().encode(s);

function moofAndMdat(data: Uint8Array, boxes: Box[]): Uint8Array {
  const i = boxes.findIndex((b) => b.type === "moof");
  if (i < 0 || boxes[i + 1]?.type !== "mdat") throw new Error("moof + mdat not found");
  return data.slice(boxes[i].start, boxes[i + 1].end);
}

function incrementIv(iv: Uint8Array, times = 1): Uint8Array {
  const out = new Uint8Array(iv);
  for (let n = 0; n < times; n++) {
    for (let i = out.length - 1; i >= 0; i--) {
      out[i] = (out[i] + 1) & 0xff;
      if (out[i] !== 0) break;
    }
  }
  return out;
}

async function segmentIv(seq: number, anchorSegmentIndex: number, streamIdHash: string) {
  const anchor = Math.floor(seq / anchorSegmentIndex) * anchorSegmentIndex;
  const digest = new Uint8Array(
    await crypto.subtle.digest("SHA-256", utf8(streamIdHash + anchor.toString()))
  );
  return incrementIv(digest.slice(0, 16), seq - anchor);
}

async function continuityToken(input: Uint8Array, certHash: string, iv: Uint8Array) {
  const key = await crypto.subtle.importKey(
    "raw", utf8(certHash.slice(0, 16)), { name: "AES-CBC" }, false, ["encrypt"]
  );
  // WebCrypto AES-CBC always applies PKCS#7 padding
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-CBC", iv }, key, input));
  return btoa(String.fromCharCode(...ct.slice(-16)));
}

async function checkAnchorChain(seg: any, segment: Uint8Array, boxes: Box[]) {
  const iv = await segmentIv(seg.sequenceNumber, seg.anchorSegmentIndex, seg.streamIdHash);
  const token = await continuityToken(moofAndMdat(segment, boxes), seg.certHash, iv);
  if (token !== seg.continuityToken) {
    clearIvCache();
    fail("livevideo.segment.invalid");
  }
}
```

**Security note.** The AES key and the IV are derived only from values that
are in the manifest. Anyone who can read the manifest can recompute the token,
so it shows that the `moof`/`mdat` bytes are consistent with the manifest but
does not by itself authenticate them. Authenticity comes from the signed
manifest and its `c2pa.hash.bmff.v3` hard binding (Step 2).

### Step 7: Report the result

A segment is **valid** when Steps 1, 2, 5 and (for `com.ezdrm.anchor-chain`) 6
pass. The CAWG identity result from Step 3 is reported alongside. Report
failures with the status codes above. On any failure, clear the cached
previous-segment state and IV so that the next segment, or the next anchor
segment for Step 6, starts a new chain.

## Missing segments

Live delivery regularly loses or skips segments, for example when a player
joins mid-stream, switches renditions or drops a segment that arrived late.

- With **`c2pa.manifestId`**, every segment names the manifest of the segment
  before it. If segment N is missing, segment N+1 carries a
  `previousManifestId` that the validator has never seen, so N+1 fails with
  `livevideo.segment.invalid`. The chain can only be restarted by out-of-band
  means.
- With **`com.ezdrm.anchor-chain`**, the IV of every segment can be derived
  from its own `sequenceNumber` and the anchor index alone. A validator that
  misses segment N derives the IV of N+1 from the anchor (Step 6.2 and 6.3)
  instead of incrementing a cached IV, and N+1 validates normally. The
  `sequenceNumber` check in Step 5 still passes, because it only requires an
  increase. Only the missing segment itself is lost.

```mermaid
sequenceDiagram
  participant P as Player / validator
  Note over P: seg 728690 (anchor), IV derived from anchor, valid
  Note over P: seg 728691, IV = cached IV + 1, valid
  Note over P: seg 728692 not received
  Note over P: seg 728693, cached IV is stale,<br/>IV re-derived from anchor 728690 + 3, valid
  Note over P: with c2pa.manifestId, 728693 would fail:<br/>previousManifestId names 728692
```

## Validation rubric

The rubric below scores `m4s/` (`init.mp4` and segments 728690 to 728709)
against each validation criterion. "Measured" criteria were checked directly
against the file bytes. "c2patool" criteria were checked with c2patool 0.27.22
(c2pa-rs), which reports `validation_state` `Valid` for all 21 files.

Signer certificate trust is out of scope for this test set: the rubric scores
signature and time-stamp validity, not whether the signing certificates are on
a particular trust list.

### Criteria

| ID | Criterion | Spec | Status code on failure | Method | Result |
|:--|:--|:--|:--|:--|:--|
| R1 | Initialization segment contains no `mdat` | 19.7.1 | `livevideo.init.invalid` | Measured | **PASS** (1/1) |
| R2 | Each media segment has a C2PA Manifest Box | 19.7.1 | `livevideo.segment.invalid` | Measured | **PASS** (20/20) |
| R3 | Claim uses `c2pa.claim.v2` | 10 | Generator conformance | Measured | **PASS** (20/20 segments). **FAIL** for `init.mp4` (`c2pa.claim`) |
| R4 | Manifest identifier uses `urn:c2pa:` | 8 | Generator conformance | Measured | **PASS** (20/20 segments). **FAIL** for `init.mp4` (`urn:uuid:`) |
| R5 | Claim signature carries a v2 time-stamp (`sigTst2`) | 10.3.2.5 | Generator conformance | Measured | **PASS** (20/20) |
| R6 | Every hashed URI in the claim matches its assertion | 15 | `assertion.hashedURI.mismatch` | Measured | **PASS** (100/100 in segments, 2/2 in `init.mp4`) |
| R7 | `c2pa.livevideo.segment` is present | 19.3.2 | `livevideo.assertion.invalid` | Measured | **PASS** (20/20) |
| R8 | `sequenceNumber` is greater than the previous segment's | 19.7.2 | `livevideo.assertion.invalid` | Measured | **PASS** (20/20) |
| R9 | `streamId` equals the previous segment's | 19.7.2 | `livevideo.assertion.invalid` | Measured | **PASS** (20/20) |
| R10 | `continuityMethod` is present and supported | 19.7.2 | `livevideo.continuityMethod.invalid` | Measured | **PASS** (20/20, `com.ezdrm.anchor-chain`) |
| R11 | `streamIdHash` equals `SHA-256(streamId)[0..15]` | `com.ezdrm.anchor-chain` | `livevideo.segment.invalid` | Measured | **PASS** (20/20) |
| R12 | Continuity token recomputes (anchors 728690 and 728700) | `com.ezdrm.anchor-chain` | `livevideo.segment.invalid` | Measured | **PASS** (20/20) |
| R13 | `sequenceNumber` matches `mfhd.sequence_number` | 19.3.2 | Generator conformance | Measured | **FAIL** (0/20, `sequenceNumber` is `mfhd` minus 1) |
| R14 | `cawg.identity` is present and its referenced `c2pa.hash.bmff.v3` hash matches | CAWG Identity Assertion | Identity assertion invalid | Measured | **PASS** (20/20) |
| R15 | Claim signature is valid and inside the certificate's validity period | 15 | `claimSignature.mismatch`, `claimSignature.outsideValidity` | c2patool | **PASS** (21/21 `claimSignature.validated`, `claimSignature.insideValidity`) |
| R16 | Time-stamp is valid for the claim signature | 10.3.2.5, 15 | `timeStamp.mismatch` | c2patool | **PASS** (21/21 `timeStamp.validated`) |
| R17 | `c2pa.hash.bmff.v3` matches the segment bytes | 15 | `assertion.bmffHash.mismatch` | c2patool | **PASS** (21/21 `assertion.bmffHash.match`) |
| R18 | CAWG identity signature (`cawg.x509.cose`) is valid | CAWG Identity Assertion | Identity assertion invalid | c2patool | **PASS** (20/20 `cawg.identity.well-formed`, "CAWG X.509 identity signature valid") |

### Results per file (measured)

| File | Box structure | C2PA Manifest Box | claim.v2 | urn:c2pa | sigTst2 | livevideo.segment | sequenceNumber increasing | streamId constant | continuityMethod | streamIdHash | Continuity token | seq = mfhd | Assertion hashes | CAWG identity | CAWG ref hash |
|:--|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `init.mp4` (init) | PASS (`ftyp uuid moov`, no mdat) | PASS | FAIL | FAIL | — | — | — | — | — | — | — | — | PASS (2/2) | — | — |
| `seg_728690.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728691.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728692.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728693.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728694.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728695.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728696.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728697.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728698.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728699.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728700.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728701.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728702.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728703.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728704.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728705.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728706.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728707.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728708.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |
| `seg_728709.m4s` | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | `com.ezdrm.anchor-chain` | PASS | PASS | FAIL | PASS (5/5) | present | PASS |

### Results per file (c2patool 0.27.22)

| File | validation_state | claimSignature.validated | timeStamp.validated | assertion.bmffHash.match | assertion.hashedURI.match | cawg.identity.well-formed |
|:--|:-:|:-:|:-:|:-:|:-:|:-:|
| `init.mp4` | Valid | PASS | PASS | PASS | 2 | — |
| `seg_728690.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728691.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728692.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728693.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728694.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728695.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728696.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728697.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728698.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728699.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728700.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728701.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728702.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728703.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728704.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728705.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728706.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728707.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728708.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |
| `seg_728709.m4s` | Valid | PASS | PASS | PASS | 5 | PASS |

## Checking this test set

1. **Box structure.** List the top-level boxes, for example with GPAC:

   ```bash
   MP4Box -info m4s/init.mp4
   ```

   ```bash
   MP4Box -info m4s/seg_728690.m4s
   ```

   `init.mp4` contains `ftyp`, the C2PA `uuid` box and `moov`. Each media
   segment contains `ftyp`, the C2PA `uuid` box, `sidx`, `moof` and `mdat`.
2. **Manifest.** Read each file with a C2PA validator and record
   `validation_state` and `validation_status`, for example with c2patool:

   ```bash
   c2patool m4s/seg_728690.m4s
   ```

   All 21 files report `validation_state` `Valid` with c2patool 0.27.22.
3. **Hard binding.** Confirm that `c2pa.hash.bmff.v3` validates for every
   file (`assertion.bmffHash.match`).
4. **CAWG identity.** Confirm that `cawg.identity` validates for every segment
   (`cawg.identity.well-formed`).
5. **Live video checks.** Run Steps 4 and 5 in segment order.
   `sequenceNumber` runs from 728690 to 728709 in steps of one and `streamId`
   is constant.
6. **Continuity tokens.** Run Step 6. All 20 tokens (anchors 728690 and 728700)
   recompute correctly with the algorithm above.
7. **Negative checks.**
   - Flip one byte in an `mdat`: Step 2 (`assertion.bmffHash.mismatch`) and
     Step 6 both fail.
   - Swap two segments: Step 5 fails.
   - Remove one segment from the middle of `m4s/`: the following segment still
     validates by re-deriving its IV from the anchor
     ([Missing segments](#missing-segments)).

## Known deviations in the current files

| Issue | Spec reference | Effect |
|:--|:--|:--|
| `sequenceNumber` is one less than `mfhd.sequence_number` (728690 against 728691) | 19.3.2, 19.4 `sequenceNumber` | `sequenceNumber` should match `mfhd.sequence_number` or follow ISO/IEC 23009-9 segment indexing |
| The manifest in `init.mp4` uses `c2pa.claim` (v1), `c2pa.hash.bmff.v2` and a `urn:uuid:` label. The media segments already use `c2pa.claim.v2`, `c2pa.hash.bmff.v3` and `urn:c2pa:` | 8, 10, Appendix C | Deprecated constructs. Validators accept them, but generators must not write them |
| Media segments start with `ftyp` rather than `styp` | ISO/IEC 14496-12 | Media segments normally start with `styp`. Both are excluded from the hash |
| The anchor-chain fields (`anchorSegmentIndex`, `streamIdHash`, `certHash`, `continuityToken`) are not namespaced | 19.3.2, 6.2 | Fields added by other continuity methods should be named as labels, for example `com.ezdrm.continuityToken` |
| `com.ezdrm.anchor-chain` is an entity-specific continuity method | 19.7.2 | Validators that do not support it report `livevideo.continuityMethod.invalid` for every segment, by design |
