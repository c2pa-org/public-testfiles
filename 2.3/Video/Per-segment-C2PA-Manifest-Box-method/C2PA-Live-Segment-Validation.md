 C2PA Live Segment Validation
 
 Step 1: Feed the raw MP4 segment bytes to the C2PA Wasm binary. The binary will:
-	Parse the embedded C2PA manifest.
-	Cryptographically verify its signature against the Trust List. 
  If verification fails, the segment must be rejected.


import wasmSrc from "@contentauth/c2pa-web/resources/c2pa.wasm?url";

// configure settings
// ...
const c2pa = await createC2pa({
      wasmSrc,
      settings: toolkitSettings,
    });
// feed fragment
// ...
 const reader = await c2pa.reader.fromBlob("video/mp4", fragment);
// verify signature
// ...



Step 2: Extract Manifest Parameters:

 From the active manifest,  locate the assertion with  action c2pa.IVHASH and extract:
1.	segmentId: Monotonically increasing integer ID of this segment.
2.	anchorSegmentIndex: How often anchor segments occur (e.g. every N segments).
3.	streamIdHash: Hash identifying the stream (used as IV seed). 
4.	certHash:  Certificate hash; first 16 characters are the AES key.
5.	continuityToken: Expected content hash value (Base64) to verify against.

  
If any of these are missing, reject the segment.


const manifest = await reader.manifestStore();
const anchorSegmentIndex = getValueFromManifest(manifest, "anchorSegmentIndex");
const certHash = getValueFromManifest(manifest, "certHash");
const streamIdHash = getValueFromManifest(manifest, "streamIdHash");
const segmentId = getValueFromManifest(manifest, "segmentId");
const continuityToken = getValueFromManifest(manifest, "continuityToken");


  Step 3 Extract moof + mdat Boxes:

Parse the MP4 container and extract only the moof and mdat boxes, concatenated in order. 

function extractMoofAndMdat(data: Buffer) {
  const boxes = [];
  let pos = 0;

  while (pos < data.length) {
    const size =
      (data[pos] << 24) |
      (data[pos + 1] << 16) |
      (data[pos + 2] << 8) |
      data[pos + 3];
    const type = String.fromCharCode(
      data[pos + 4],
      data[pos + 5],
      data[pos + 6],
      data[pos + 7]
    );

    if (type === "moof") {
      boxes.push(data.slice(pos, pos + size));
    }

    if (type === "mdat") {
      boxes.push(data.slice(pos, pos + size));
      break;
    }

    pos += size;
    if (size <= 0) break;
  }

  if (boxes.length === 0) return null;

  const totalSize = boxes.reduce((sum, box) => sum + box.length, 0);
  const combinedData = new Uint8Array(totalSize);

  let offset = 0;
  for (const box of boxes) {
    combinedData.set(box, offset);
    offset += box.length;
  }

  return combinedData;
}

  Step 4: Derive the Per-Segment IV:

1.	Identify the anchor segment for this segment.
2.	Compute the anchor IV (16 bytes).
3.	Increment to reach the current segment's IV.
 If you already have the previous segment's IV cached and the current segment is not an
  anchor,  you can simply increment it  by 1 instead of re-deriving from the anchor.


async function deriveAnchorIv16(anchorNumber: number, streamIdHash: string) {
  const dig = await sha256Bytes(utf8Bytes(streamIdHash + anchorNumber.toString()));
  return dig.slice(0, 16);
}

function incrementIv(iv: Uint8Array<ArrayBuffer>): Uint8Array<ArrayBuffer> {
  const newIv = new Uint8Array(iv);
  for (let i = newIv.length - 1; i >= 0; i--) {
    newIv[i]++;
    if (newIv[i] !== 0) {
      break;
    }
  }
  return newIv;
}


const isAnchor = segmentId % anchorSegmentIndex == 0;
const anchorNumber = Math.floor(segmentId / anchorSegmentIndex) * anchorSegmentIndex;
const anchorIvBytes = await deriveAnchorIv16( anchorNumber,                streamIdHash);
const currentIvOffset = segmentId - anchorNumber;
let currentIvBytes = anchorIvBytes;
if (previousChunkIV && !isAnchor) {
currentIvBytes = incrementIv(previousChunkIV);
       } else {
       for (let i = 0; i < currentIvOffset; i++) {
       	currentIvBytes = incrementIv(currentIvBytes);
        }
       }


Step 5:  Compute the content hash value:
segment_hash= AES-128(hash(mdat and moof boxes), currentIvBytes, certHash + streamIdHash).
 
async function computeContentHash(
  data: Uint8Array<ArrayBuffer>,
  key: string,
  iv: Uint8Array<ArrayBuffer>
) {
  const wordArray = CryptoJS.lib.WordArray.create(data);
  const ivWordArray = CryptoJS.lib.WordArray.create(iv);
  const keyUtf8 = CryptoJS.enc.Utf8.parse(key);

  const encrypted = CryptoJS.AES.encrypt(wordArray, keyUtf8, {
    iv: ivWordArray,
    padding: CryptoJS.pad.Pkcs7,
    mode: CryptoJS.mode.CBC,
  });

  const ciphertext = Uint8Array.from(
    Buffer.from(encrypted.ciphertext.toString(CryptoJS.enc.Hex), "hex")
  );

  const hash= ciphertext.slice(-16);
  return Buffer.from(hash).toString("base64");
}


const computedContentHash = await computeContentHash(
                moofAndMdat,
                key,
                currentIvBytes
              );


Step 6: Compare Tokens:
If: 
-	computedContentHash ==  continuityToken  →  VALID
-	computedContentHash !=  continuityToken  →  INVALID
On failure: mark the manifest validation state as Invalid, notify the consumer, and clear the cached IV so the next anchor  segment re-derives a clean chain.
