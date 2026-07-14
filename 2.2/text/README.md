# Unstructured text (A.8) test material

Test material for [C2PA Appendix A.8 unstructured-text embedding](https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html#_embedding_manifests_into_unstructured_text),
which embeds a `C2PATextManifestWrapper` into text as a run of non-rendering
Unicode variation selectors.

These files exercise the **wrapper encoding and detection** — the interop-critical
part of A.8 that a text validator must implement — independent of manifest signing.

## Files

- `writerslogic-20260714-a8-vectors.json` — byte-level conformance vectors: the
  `byteToVariationSelector` mapping, the `C2PATXT\0` magic code-point sequence, and
  a complete wrapper vector (payload → UTF-8 bytes). Verified byte-identical against
  the `c2pa-text` reference library.
- `writerslogic-20260714-a8-wrapper.txt` — a UTF-8 text file with a visible sentence
  followed by an embedded `C2PATextManifestWrapper` (a `U+FEFF` marker and a
  variation-selector run). A validator should locate the wrapper, decode it, and
  recover the payload documented in the vectors file.

## Notes

- The wrapper payload in these examples is a fixed placeholder (`c2pa-manifest-01`),
  not a signed manifest store; they test the transport and detection layer. Signed
  positive/negative manifest files await a text-capable Conforming Generator.
- These characters are invisible by design — inspect with a hex or code-point viewer.

Contributed by [WritersLogic](https://writerslogic.com).
