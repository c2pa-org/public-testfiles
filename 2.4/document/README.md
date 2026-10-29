# ZIP-based document test files

See the [2.4 README](../README.md) for the naming codes, the signing certificate, and how these files were made and checked.

## CogProof files (`cogproof-20261029-*`)

Each format has the same six files:

* **C**: a document holding "C2PA test document.", signed with a `c2pa.created` action (`algorithmicMedia`). The OpenXPS files draw coloured bars instead of text.
* **CA**: the document with edited text. C is its parent ingredient, with `c2pa.opened` and `c2pa.edited` actions.
* **CAI**: as CA, plus a paragraph from an unsigned component document (`c2pa.placed`).
* **E-dat-CA**, **E-sig-CA**, **E-uri-CA**: copies of CA, each damaged in one way (see Bad, below).

| Format | Folder | Embedding (2.4) | Hard binding |
| ------ | ------ | --------------- | ------------ |
| EPUB 3 | `epub` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| Word (OOXML) | `docx` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| Excel (OOXML) | `xlsx` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| PowerPoint (OOXML) | `pptx` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| OpenDocument text | `odt` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| OpenDocument spreadsheet | `ods` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| OpenDocument presentation | `odp` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| OpenDocument graphics | `odg` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |
| OpenXPS | `oxps` | `META-INF/content_credential.c2pa`, stored | `c2pa.hash.collection.data` |

### Good

| File | Expected result |
| ---- | --------------- |
| [cogproof-20261029-C.epub](good/epub/cogproof-20261029-C.epub) | Valid, no ingredients |
| [cogproof-20261029-CA.epub](good/epub/cogproof-20261029-CA.epub) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.epub](good/epub/cogproof-20261029-CAI.epub) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.docx](good/docx/cogproof-20261029-C.docx) | Valid, no ingredients |
| [cogproof-20261029-CA.docx](good/docx/cogproof-20261029-CA.docx) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.docx](good/docx/cogproof-20261029-CAI.docx) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.xlsx](good/xlsx/cogproof-20261029-C.xlsx) | Valid, no ingredients |
| [cogproof-20261029-CA.xlsx](good/xlsx/cogproof-20261029-CA.xlsx) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.xlsx](good/xlsx/cogproof-20261029-CAI.xlsx) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.pptx](good/pptx/cogproof-20261029-C.pptx) | Valid, no ingredients |
| [cogproof-20261029-CA.pptx](good/pptx/cogproof-20261029-CA.pptx) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.pptx](good/pptx/cogproof-20261029-CAI.pptx) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.odt](good/odt/cogproof-20261029-C.odt) | Valid, no ingredients |
| [cogproof-20261029-CA.odt](good/odt/cogproof-20261029-CA.odt) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.odt](good/odt/cogproof-20261029-CAI.odt) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.ods](good/ods/cogproof-20261029-C.ods) | Valid, no ingredients |
| [cogproof-20261029-CA.ods](good/ods/cogproof-20261029-CA.ods) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.ods](good/ods/cogproof-20261029-CAI.ods) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.odp](good/odp/cogproof-20261029-C.odp) | Valid, no ingredients |
| [cogproof-20261029-CA.odp](good/odp/cogproof-20261029-CA.odp) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.odp](good/odp/cogproof-20261029-CAI.odp) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.odg](good/odg/cogproof-20261029-C.odg) | Valid, no ingredients |
| [cogproof-20261029-CA.odg](good/odg/cogproof-20261029-CA.odg) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.odg](good/odg/cogproof-20261029-CAI.odg) | Valid, one parent and one component ingredient |
| [cogproof-20261029-C.oxps](good/oxps/cogproof-20261029-C.oxps) | Valid, no ingredients |
| [cogproof-20261029-CA.oxps](good/oxps/cogproof-20261029-CA.oxps) | Valid, one parent ingredient |
| [cogproof-20261029-CAI.oxps](good/oxps/cogproof-20261029-CAI.oxps) | Valid, one parent and one component ingredient |

### Bad

| File | Change to CA | Expected failure |
| ---- | ------------ | ---------------- |
| [cogproof-20261029-E-dat-CA.epub](bad/epub/cogproof-20261029-E-dat-CA.epub) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.epub](bad/epub/cogproof-20261029-E-sig-CA.epub) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.epub](bad/epub/cogproof-20261029-E-uri-CA.epub) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.docx](bad/docx/cogproof-20261029-E-dat-CA.docx) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.docx](bad/docx/cogproof-20261029-E-sig-CA.docx) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.docx](bad/docx/cogproof-20261029-E-uri-CA.docx) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.xlsx](bad/xlsx/cogproof-20261029-E-dat-CA.xlsx) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.xlsx](bad/xlsx/cogproof-20261029-E-sig-CA.xlsx) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.xlsx](bad/xlsx/cogproof-20261029-E-uri-CA.xlsx) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.pptx](bad/pptx/cogproof-20261029-E-dat-CA.pptx) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.pptx](bad/pptx/cogproof-20261029-E-sig-CA.pptx) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.pptx](bad/pptx/cogproof-20261029-E-uri-CA.pptx) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.odt](bad/odt/cogproof-20261029-E-dat-CA.odt) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.odt](bad/odt/cogproof-20261029-E-sig-CA.odt) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.odt](bad/odt/cogproof-20261029-E-uri-CA.odt) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.ods](bad/ods/cogproof-20261029-E-dat-CA.ods) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.ods](bad/ods/cogproof-20261029-E-sig-CA.ods) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.ods](bad/ods/cogproof-20261029-E-uri-CA.ods) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.odp](bad/odp/cogproof-20261029-E-dat-CA.odp) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.odp](bad/odp/cogproof-20261029-E-sig-CA.odp) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.odp](bad/odp/cogproof-20261029-E-uri-CA.odp) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.odg](bad/odg/cogproof-20261029-E-dat-CA.odg) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.odg](bad/odg/cogproof-20261029-E-sig-CA.odg) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.odg](bad/odg/cogproof-20261029-E-uri-CA.odg) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |
| [cogproof-20261029-E-dat-CA.oxps](bad/oxps/cogproof-20261029-E-dat-CA.oxps) | CA's manifest store on a copy of CA with one letter of the text changed | `assertion.collectionHash.mismatch` |
| [cogproof-20261029-E-sig-CA.oxps](bad/oxps/cogproof-20261029-E-sig-CA.oxps) | Last byte of the claim signature flipped | `claimSignature.mismatch` |
| [cogproof-20261029-E-uri-CA.oxps](bad/oxps/cogproof-20261029-E-uri-CA.oxps) | One letter of the `c2pa.edited` description changed | `assertion.hashedURI.mismatch` |

Each bad file fails for one reason only.

Each file has a C2PA Tool style report in `manifests/<name>/manifest_store.json` and `manifests/<name>/detailed.json`, next to the file.
