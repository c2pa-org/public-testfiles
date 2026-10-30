# Machine-learning model test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a tiny model with one 2×4 `weight` tensor (ONNX: `y = x · weight`), signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the model with its weights scaled by 0.5. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a `bias` tensor from an unsigned component model (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| ONNX | `onnx` | Base64 in `metadata_props` entry `c2pa:manifest` | `c2pa.hash.data` |
| SafeTensors | `safetensors` | Base64 in `__metadata__` key `c2pa:manifest` | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.onnx](good/onnx/cogproof-20261029-C.onnx) | Valid, no ingredients |
| [cogproof-20261029-CA.onnx](good/onnx/cogproof-20261029-CA.onnx) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.onnx](good/onnx/cogproof-20261029-CAI.onnx) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.safetensors](good/safetensors/cogproof-20261029-C.safetensors) | Valid, no ingredients |
| [cogproof-20261029-CA.safetensors](good/safetensors/cogproof-20261029-CA.safetensors) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.safetensors](good/safetensors/cogproof-20261029-CAI.safetensors) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.onnx](bad/onnx/cogproof-20261029-E-dat-CA.onnx) | CA's manifest store on a copy of CA with one weight changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.onnx](bad/onnx/cogproof-20261029-E-sig-CA.onnx) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.onnx](bad/onnx/cogproof-20261029-E-uri-CA.onnx) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.safetensors](bad/safetensors/cogproof-20261029-E-dat-CA.safetensors) | CA's manifest store on a copy of CA with one weight changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.safetensors](bad/safetensors/cogproof-20261029-E-sig-CA.safetensors) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.safetensors](bad/safetensors/cogproof-20261029-E-uri-CA.safetensors) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
