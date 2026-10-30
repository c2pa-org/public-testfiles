# Audio test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a 3-second 440 Hz tone (Ogg Vorbis; WAV inside `.facta`), or a Standard MIDI File playing a C major scale, signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the tone at -6 dB, or the scale with every note velocity halved. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a 660 Hz tone (or a second MIDI track) from an unsigned component file (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| Standard MIDI File | `midi` | `FF 7F` event, manufacturer `00 43 32`, before End of Track in the designated track | `c2pa.hash.data` |
| Ogg Vorbis | `ogg` | Its own logical bitstream, first packet `\x00c2pa` + store | `c2pa.hash.boxes` |
| BlockFact `.facta` | `facta` | `C2PA` extension block | `c2pa.hash.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.mid](good/midi/cogproof-20261029-C.mid) | Valid, no ingredients |
| [cogproof-20261029-CA.mid](good/midi/cogproof-20261029-CA.mid) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.mid](good/midi/cogproof-20261029-CAI.mid) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.ogg](good/ogg/cogproof-20261029-C.ogg) | Valid, no ingredients |
| [cogproof-20261029-CA.ogg](good/ogg/cogproof-20261029-CA.ogg) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.ogg](good/ogg/cogproof-20261029-CAI.ogg) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.facta](good/facta/cogproof-20261029-C.facta) | Valid, no ingredients |
| [cogproof-20261029-CA.facta](good/facta/cogproof-20261029-CA.facta) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.facta](good/facta/cogproof-20261029-CAI.facta) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.mid](bad/midi/cogproof-20261029-E-dat-CA.mid) | CA's manifest store on a copy of CA with one note velocity changed | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.mid](bad/midi/cogproof-20261029-E-sig-CA.mid) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.mid](bad/midi/cogproof-20261029-E-uri-CA.mid) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.ogg](bad/ogg/cogproof-20261029-E-dat-CA.ogg) | One audio byte of CA flipped | `assertion.boxesHash.mismatch` |
| [cogproof-20261029-E-sig-CA.ogg](bad/ogg/cogproof-20261029-E-sig-CA.ogg) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.ogg](bad/ogg/cogproof-20261029-E-uri-CA.ogg) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.facta](bad/facta/cogproof-20261029-E-dat-CA.facta) | CA's manifest store on a copy of CA with the tone at -6.1 dB | `assertion.dataHash.mismatch` |
| [cogproof-20261029-E-sig-CA.facta](bad/facta/cogproof-20261029-E-sig-CA.facta) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.facta](bad/facta/cogproof-20261029-E-uri-CA.facta) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

The Ogg box hash follows "Ogg-specific Handling" under General Box Hash: one `Stream-[serial]` box per logical bitstream, and the C2PA stream as the `C2PA` box. The Vorbis stream is split by the C2PA pages, so its box is made of two runs of pages. The 2.5 text leaves the page placement open (c2pa-org/specs-core#2646); these files put the C2PA stream's pages directly after the leading BOS pages.

In the Ogg E-dat file the flipped byte falls in a compressed audio page, so a decoder may report one damaged page.

c2pa-rs writes MIDI, Ogg and `.facta` behind its `unstable_midi`, `unstable_ogg` and `unstable_blockfact` features.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
