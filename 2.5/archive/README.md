# Archive test files

See the [2.5 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a WARC capture of one page (`warcinfo`, `request` and `response` records) whose HTML reads "C2PA test document.", signed with a `c2pa.created` action (`algorithmicMedia`).
* **CA**: the capture with the page text edited. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a paragraph from an unsigned component capture (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.5) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| WARC 1.1 | `warc` | Final `c2pa-provenance` record | `c2pa.hash.collection.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.warc](good/warc/cogproof-20261029-C.warc) | Valid, no ingredients |
| [cogproof-20261029-CA.warc](good/warc/cogproof-20261029-CA.warc) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.warc](good/warc/cogproof-20261029-CAI.warc) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.warc](bad/warc/cogproof-20261029-E-dat-CA.warc) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.warc](bad/warc/cogproof-20261029-E-sig-CA.warc) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.warc](bad/warc/cogproof-20261029-E-uri-CA.warc) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

The collection data hash has one entry per record other than the C2PA record, keyed by its `WARC-Record-ID` and hashed over the whole uncompressed record. The C2PA record is last, with `WARC-Type: c2pa-provenance`, `Content-Type: application/c2pa` and no `WARC-Target-URI`.

c2pa-rs writes WARC behind its `unstable_warc` feature, with contentauth/c2pa-rs#2964.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
