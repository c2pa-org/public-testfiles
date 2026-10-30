# C2PA live segment validation rubric

- **Method:** Per-segment C2PA Manifest Box method (C2PA 2.3 and 2.4, Section 19.3)
- **Input:** `m4s-tampered`: 1 initialization segment(s), 5 media segment(s)
- **Validator:** c2patool 0.27.22
- **Segment index source:** number in the segment file name
- **Out of scope:** signer and time-stamp authority trust. The rubric scores signature and time-stamp validity, not trust-list membership

**Result: one or more validation criteria fail. See below.**

## Validation rubric

Checks a validator performs (Chapter 15, Section 19.7, the `com.ezdrm.anchor-chain` continuity method and the CAWG identity assertion).

| ID | Criterion | Spec section | Status code on failure | Method | Result |
|:--|:--|:--|:--|:--|:--|
| V1 | Initialization segment contains no `mdat` | 19.7.1 | `livevideo.init.invalid` | Measured | **PASS** (1/1) |
| V2 | Each media segment has a C2PA Manifest Box | 19.7.1 | `livevideo.segment.invalid` | Measured | **PASS** (5/5) |
| V3 | Claim signature is valid and inside the certificate's validity period | 15 | `claimSignature.mismatch`, `claimSignature.outsideValidity` | c2patool | **PASS** (6/6) |
| V4 | Time-stamp is valid for the claim signature | 10.3.2.5, 15 | `timeStamp.mismatch` | c2patool | **PASS** (6/6) |
| V5 | Every hashed URI in the claim matches its assertion | 15 | `assertion.hashedURI.mismatch` | Measured | **PASS** (6/6), 27/27 hashed URIs |
| V6 | `c2pa.hash.bmff.v3` matches the segment bytes | 9.2.3, 15 | `assertion.bmffHash.mismatch` | c2patool | **FAIL** (5/6; fails: seg_728692.m4s) |
| V7 | `c2pa.livevideo.segment` is present | 19.3.2 (defined), 19.7.2 (checked) | `livevideo.assertion.invalid` | Measured | **PASS** (5/5) |
| V8 | `sequenceNumber` is greater than the previous segment's | 19.7.2 | `livevideo.assertion.invalid` | Measured | **PASS** (5/5) |
| V9 | `streamId` equals the previous segment's | 19.7.2 | `livevideo.assertion.invalid` | Measured | **PASS** (5/5) |
| V10 | `continuityMethod` is present and supported | 19.7.2 | `livevideo.continuityMethod.invalid` | Measured | **PASS** (5/5), `com.ezdrm.anchor-chain` |
| V11 | `streamIdHash` equals `SHA-256(streamId)[0..15]` | `com.ezdrm.anchor-chain` | `livevideo.segment.invalid` | Measured | **PASS** (5/5) |
| V12 | Anchor-chain continuity token recomputes | `com.ezdrm.anchor-chain` | `livevideo.segment.invalid` | Measured | **FAIL** (4/5; fails: seg_728692.m4s) |
| V13 | `cawg.identity` referenced assertion hashes match | CAWG Identity Assertion | Identity assertion invalid | Measured | **PASS** (5/5) |
| V14 | `cawg.identity` signature (`cawg.x509.cose`) is valid | CAWG Identity Assertion | Identity assertion invalid | c2patool | **PASS** (5/5) |

### Results per file

| File | V1 | V2 | V3 | V4 | V5 | V6 | V7 | V8 | V9 | V10 | V11 | V12 | V13 | V14 |
|:--|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `init.mp4` (init) | PASS | — | PASS | PASS | PASS | PASS | — | — | — | — | — | — | — | — |
| `seg_728690.m4s` to `seg_728691.m4s` (2 files) | — | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| `seg_728692.m4s` | — | PASS | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL | PASS | PASS |
| `seg_728693.m4s` to `seg_728694.m4s` (2 files) | — | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

### Validator output per file

| File | `validation_state` | Status codes reported |
|:--|:--|:--|
| `init.mp4` (init) | Valid | `assertion.bmffHash.match`, `assertion.hashedURI.match` x2, `claimSignature.insideValidity`, `claimSignature.validated`, `signingCredential.untrusted`, `timeStamp.trusted`, `timeStamp.validated` |
| `seg_728690.m4s` to `seg_728691.m4s` (2 files) | Valid | `assertion.bmffHash.match`, `assertion.hashedURI.match` x5, `cawg.identity.well-formed`, `claimSignature.insideValidity`, `claimSignature.validated`, `signingCredential.untrusted` x2, `timeStamp.untrusted`, `timeStamp.validated` |
| `seg_728692.m4s` | Invalid | `assertion.bmffHash.mismatch`, `assertion.hashedURI.match` x5, `cawg.identity.well-formed`, `claimSignature.insideValidity`, `claimSignature.validated`, `signingCredential.untrusted` x2, `timeStamp.untrusted`, `timeStamp.validated` |
| `seg_728693.m4s` to `seg_728694.m4s` (2 files) | Valid | `assertion.bmffHash.match`, `assertion.hashedURI.match` x5, `cawg.identity.well-formed`, `claimSignature.insideValidity`, `claimSignature.validated`, `signingCredential.untrusted` x2, `timeStamp.untrusted`, `timeStamp.validated` |

## Predictive validation

With `com.ezdrm.anchor-chain`, a validator knows what the next segment must contain before it arrives. Only the segment's bytes and its `continuityToken` are new. Everything else is fixed for the stream or follows from `sequenceNumber`:

1. **Next `sequenceNumber`:** the previous one plus 1. The segment can be requested by that index.
2. **Next anchor:** anchors fall where `sequenceNumber % anchorSegmentIndex == 0`, so the validator knows which upcoming segment re-derives its IV.
3. **Next IV:** the previous IV plus 1, or for an anchor `SHA-256(streamIdHash + anchor)[0..15]`. It is computed before the segment arrives.
4. **AES key:** `certHash` is constant for the signer, so the AES-128 key schedule is set up once per stream.
5. **Stream binding:** `streamId` and `streamIdHash` are constant, so they are checked once and then compared by value.
6. **Streaming token check:** the CBC-MAC runs over `moof` then `mdat` in arrival order, so the token is ready as soon as the last byte of `mdat` arrives. No second pass over the segment is needed.
7. **Manifest first:** the C2PA Manifest Box comes before `moof` and `mdat`, so signature, time-stamp and CAWG checks can run while the media is still downloading.

The table replays the segments in order. The "Predicted" columns are computed from the previous segment only, before the segment is read. "Matches" checks the arriving segment's `sequenceNumber`, anchor-chain parameters and derived IV against the prediction.

| Segment | Predicted `sequenceNumber` | Predicted anchor | IV source | Predicted IV | Matches |
|:--|:-:|:-:|:--|:--|:-:|
| `seg_728690.m4s` | 728690 (first seen) | 728690 | start: anchor 728690 + 0 | `9d45f4a9b9b08700bbf3456c0edb741e` | PASS |
| `seg_728691.m4s` | 728691 | 728690 | previous IV + 1 | `9d45f4a9b9b08700bbf3456c0edb741f` | PASS |
| `seg_728692.m4s` | 728692 | 728690 | previous IV + 1 | `9d45f4a9b9b08700bbf3456c0edb7420` | PASS |
| `seg_728693.m4s` | 728693 | 728690 | previous IV + 1 | `9d45f4a9b9b08700bbf3456c0edb7421` | PASS |
| `seg_728694.m4s` | 728694 | 728690 | previous IV + 1 | `9d45f4a9b9b08700bbf3456c0edb7422` | PASS |

**5/5 segments matched the prediction made from the previous segment.**

## Generator conformance notes

Requirements on the claim generator. Validators do not reject files that miss these, so they do not affect the validation result above.

| ID | Criterion | Spec section | Status code on failure | Method | Result |
|:--|:--|:--|:--|:--|:--|
| G1 | Claim uses `c2pa.claim.v2` | 10 | None. Validators accept `c2pa.claim` | Measured | **FAIL** (5/6; fails: init.mp4) |
| G2 | Manifest identifier uses `urn:c2pa:` | 8 | None | Measured | **FAIL** (5/6; fails: init.mp4) |
| G3 | Claim signature carries a v2 time-stamp (`sigTst2`) | 10.3.2.5 | None. Validators accept `sigTst` | Measured | **FAIL** (5/6; fails: init.mp4) |
| G4 | `sequenceNumber` matches `mfhd.sequence_number` or the segment index | 19.3.2 | None | Measured | **PASS** (5/5), matches the segment index (playlist media sequence and file name) |

| File | G1 | G2 | G3 | G4 |
|:--|:-:|:-:|:-:|:-:|
| `init.mp4` (init) | FAIL | FAIL | FAIL | — |
| `seg_728690.m4s` to `seg_728694.m4s` (5 files) | PASS | PASS | PASS | PASS |
