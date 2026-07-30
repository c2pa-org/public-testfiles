# Unstructured text (A.8) test material

Test material for [C2PA Appendix A.8 unstructured-text embedding](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html#_embedding_manifests_into_unstructured_text),
which embeds a `C2PATextManifestWrapper` into text as a run of non-rendering
Unicode variation selectors.

These files exercise the **wrapper encoding and detection** — the interop-critical
part of A.8 that a text validator must implement — independent of manifest signing.
A.8 is defined in version 2.4 of the specification, which is why this material sits
under `2.4/` rather than `2.2/`.

## Files

- `writerslogic-20260714-a8-vectors.json` — byte-level conformance vectors: the
  `byteToVariationSelector` mapping, the `C2PATXT\0` magic code-point sequence,
  complete wrapper vectors in both unpadded and deterministically padded form, the
  `c2pa.hash.data` exclusion range for the example asset, and the expected outcome
  for each negative file.

Good:

- `writerslogic-20260714-a8-wrapper.txt` — visible sentence followed by an unpadded
  wrapper. A validator should locate it, decode it, and recover the payload.
- `writerslogic-20260714-a8-wrapper-padded.txt` — the same manifest with
  deterministic padding applied, so the wrapper is exactly `E_target` bytes.

Bad:

- `writerslogic-20260714-a8-bad-magic.txt` — final magic byte is `0x01`.
- `writerslogic-20260714-a8-bad-version.txt` — version field is `2`.
- `writerslogic-20260714-a8-bad-length.txt` — declares 24 payload bytes, carries 16.
- `writerslogic-20260714-a8-two-wrappers.txt` — two valid wrappers.
- `writerslogic-20260714-a8-no-wrapper.txt` — the visible sentence alone.

In every negative case the asset is to be treated as if no manifests were located.

## Deterministic padding

The specification fixes the target wrapper length and the padding byte values, so
that compliant generators produce byte-identical wrappers for the same manifest.
For the 16-byte payload used here, `E_target = 3 + (13 + 16) * 4 + 6` = 125, the
unpadded wrapper is 114 bytes, and the 11-byte gap decomposes as one `0x00` followed
by two `0x10`. This is the part of A.8 where implementations most easily diverge,
which is why both forms are included.

## Notes

- The wrapper payload is a fixed placeholder (`c2pa-manifest-01`), not a signed
  Manifest Store; these test the transport and detection layer. Signed
  positive/negative manifest files await a text-capable Conforming Generator.
- The `.txt` files deliberately have no trailing newline, so that the byte offsets
  in the vectors file are unambiguous.
- These characters are invisible by design — inspect with a hex or code-point viewer.
- Vector values are derived from the specification and independently verified by
  decoding each file back to its payload.

Contributed by [WritersLogic](https://writerslogic.com).
