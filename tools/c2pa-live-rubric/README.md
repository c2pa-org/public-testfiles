# c2pa-live-rubric

Scores a set of live video segments that use the **Per-segment C2PA Manifest
Box method** (C2PA 2.3 and 2.4, Section 19.3) against a validation rubric, and
writes the result as Markdown.

It combines direct measurement of the files with an optional run of
[c2patool](https://github.com/contentauth/c2pa-rs) for the cryptographic checks
(claim signature, time-stamp, BMFF hash, CAWG signature).

## Build

Requires Go 1.21 or later. No external modules.

```bash
go build -o c2pa-live-rubric .
```

## Usage

```bash
c2pa-live-rubric -c2patool /path/to/c2patool -o rubric.md path/to/m4s
```

To score the live video test set in this repository from the repository root
without building first:

```bash
cd tools/c2pa-live-rubric
```

```bash
go run . -c2patool /path/to/c2patool ../../2.4/Video/Per-segment-C2PA-Manifest-Box-method/m4s
```

| Option | Meaning |
|:--|:--|
| `<folder>` | Folder with the initialization segment and the media segments (`.mp4`, `.m4s`, `.cmfv`, `.cmfa`) |
| `-c2patool` | Path to c2patool. Without it, V3, V4, V6 and V14 are shown as not run |
| `-playlist` | HLS playlist (`index.m3u8`). Its `EXT-X-MEDIA-SEQUENCE` is used as the segment index for G4. Without it, the number at the end of each file name is used |
| `-o` | Write the report to a file instead of standard output |

The exit code is 0 when the report is written, whatever the result. Read the
**Result** line of the report.

## What it checks

### Validation rubric (V1 to V14)

Checks a validator performs. All must pass for a file set to pass.

| ID | Check | Spec | Method |
|:--|:--|:--|:--|
| V1 | Initialization segment contains no `mdat` | 19.7.1 | Measured |
| V2 | Each media segment has a C2PA Manifest Box | 19.7.1 | Measured |
| V3 | Claim signature valid, inside validity period | 15 | c2patool |
| V4 | Time-stamp valid | 10.3.2.5, 15 | c2patool |
| V5 | Every hashed URI in the claim matches its assertion | 15 | Measured |
| V6 | `c2pa.hash.bmff.v3` matches the segment bytes | 9.2.3, 15 | c2patool |
| V7 | `c2pa.livevideo.segment` present | 19.3.2 | Measured |
| V8 | `sequenceNumber` increases | 19.7.2 | Measured |
| V9 | `streamId` constant | 19.7.2 | Measured |
| V10 | `continuityMethod` present and supported (`c2pa.manifestId` or `com.ezdrm.anchor-chain`) | 19.7.2 | Measured |
| V11 | `streamIdHash` = `SHA-256(streamId)[0..15]` | `com.ezdrm.anchor-chain` | Measured |
| V12 | Anchor-chain continuity token recomputes | `com.ezdrm.anchor-chain` | Measured |
| V13 | CAWG referenced assertion hashes match | CAWG | Measured |
| V14 | CAWG `cawg.x509.cose` signature valid | CAWG | c2patool |

Signer and time-stamp authority **trust** are out of scope: the rubric scores
validity, not trust-list membership.

### Predictive validation

Replays the segments in order and, for each one, predicts from the previous
segment alone its `sequenceNumber`, its anchor and its IV, then checks the
arriving segment against the prediction. This shows that a validator can
prepare everything except the token computation before a segment arrives.

### Generator conformance notes (G1 to G4)

Requirements on the claim generator that validators do not enforce:
`c2pa.claim.v2` (G1), `urn:c2pa:` identifiers (G2), `sigTst2` time-stamps (G3),
and `sequenceNumber` matching `mfhd.sequence_number` or the segment index (G4).
They are reported separately and do not affect the validation result.

## Examples

- [example/rubric-m4s-728690-728709.md](example/rubric-m4s-728690-728709.md):
  `init.mp4` and segments 728690 to 728709. All 21 files pass validation, and
  20/20 segments match the prediction.
- [example/rubric-negative-tampered-mdat.md](example/rubric-negative-tampered-mdat.md):
  the same init segment and segments 728690 to 728694, with one byte changed
  in the `mdat` of `seg_728692.m4s`. V6 (`assertion.bmffHash.mismatch`) and V12
  (continuity token) fail for that segment only.

## Source layout

| File | Contents |
|:--|:--|
| `main.go` | Command line, file ordering, segment index, report layout |
| `analyze.go` | Per-file measurement, anchor-chain token, c2patool run |
| `report.go` | Rubric criteria and Markdown tables |
| `predict.go` | Predictive validation |
| `boxes.go` | ISO BMFF box reader, JUMBF parser, C2PA Manifest Box extraction |
| `cbor.go` | CBOR decoder |
