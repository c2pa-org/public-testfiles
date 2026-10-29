# MIDI test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a Standard MIDI File (format 0) playing a C major scale, signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the scale with every note velocity halved. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a second track (format 1) from an unsigned component file (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| Standard MIDI File | `midi` | `FF 7F` event, manufacturer `00 43 32`, before End of Track in the designated track | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.mid](good/midi/cogproof-20261029-C.mid) | Valid, no ingredients |
| [cogproof-20261029-CA.mid](good/midi/cogproof-20261029-CA.mid) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.mid](good/midi/cogproof-20261029-CAI.mid) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.mid](bad/midi/cogproof-20261029-E-dat-CA.mid) | CA's manifest store on a copy of CA with one note velocity changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.mid](bad/midi/cogproof-20261029-E-sig-CA.mid) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.mid](bad/midi/cogproof-20261029-E-uri-CA.mid) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

c2pa-rs writes MIDI behind its `unstable_midi` feature.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
