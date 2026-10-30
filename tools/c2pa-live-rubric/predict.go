package main

import (
	"bytes"
	"encoding/hex"
	"fmt"
	"io"
)

// writePrediction shows that, with com.ezdrm.anchor-chain, everything a
// validator needs for the next segment except its bytes and its token can be
// prepared before the segment arrives, and checks each arriving segment
// against that prediction.
func writePrediction(w io.Writer, files []*FileResult) {
	var segs []*FileResult
	for _, r := range files {
		if !r.IsInit && r.HasSeq && r.AnchorInterval > 0 && r.StreamIDHashVal != "" {
			segs = append(segs, r)
		}
	}
	if len(segs) == 0 {
		return
	}

	fmt.Fprintln(w, "## Predictive validation")
	fmt.Fprintln(w)
	fmt.Fprintln(w, "With `com.ezdrm.anchor-chain`, a validator knows what the next segment must contain before it arrives. Only the segment's bytes and its `continuityToken` are new. Everything else is fixed for the stream or follows from `sequenceNumber`:")
	fmt.Fprintln(w)
	fmt.Fprintln(w, "1. **Next `sequenceNumber`:** the previous one plus 1. The segment can be requested by that index.")
	fmt.Fprintln(w, "2. **Next anchor:** anchors fall where `sequenceNumber % anchorSegmentIndex == 0`, so the validator knows which upcoming segment re-derives its IV.")
	fmt.Fprintln(w, "3. **Next IV:** the previous IV plus 1, or for an anchor `SHA-256(streamIdHash + anchor)[0..15]`. It is computed before the segment arrives.")
	fmt.Fprintln(w, "4. **AES key:** `certHash` is constant for the signer, so the AES-128 key schedule is set up once per stream.")
	fmt.Fprintln(w, "5. **Stream binding:** `streamId` and `streamIdHash` are constant, so they are checked once and then compared by value.")
	fmt.Fprintln(w, "6. **Streaming token check:** the CBC-MAC runs over `moof` then `mdat` in arrival order, so the token is ready as soon as the last byte of `mdat` arrives. No second pass over the segment is needed.")
	fmt.Fprintln(w, "7. **Manifest first:** the C2PA Manifest Box comes before `moof` and `mdat`, so signature, time-stamp and CAWG checks can run while the media is still downloading.")
	fmt.Fprintln(w)
	fmt.Fprintln(w, "The table replays the segments in order. The \"Predicted\" columns are computed from the previous segment only, before the segment is read. \"Matches\" checks the arriving segment's `sequenceNumber`, anchor-chain parameters and derived IV against the prediction.")
	fmt.Fprintln(w)
	fmt.Fprintln(w, "| Segment | Predicted `sequenceNumber` | Predicted anchor | IV source | Predicted IV | Matches |")
	fmt.Fprintln(w, "|:--|:-:|:-:|:--|:--|:-:|")

	matched := 0
	var prev *FileResult
	var prevIV []byte
	for _, r := range segs {
		actualIV := segmentIV(r.Seq, r.AnchorInterval, r.StreamIDHashVal)
		if prev == nil {
			anchor := r.Seq / r.AnchorInterval * r.AnchorInterval
			src := fmt.Sprintf("start: anchor %d + %d", anchor, r.Seq-anchor)
			fmt.Fprintf(w, "| `%s` | %d (first seen) | %d | %s | `%s` | PASS |\n", r.Name, r.Seq, anchor, src, hex.EncodeToString(actualIV))
			matched++
			prev, prevIV = r, actualIV
			continue
		}
		seq := prev.Seq + 1
		anchor := seq / prev.AnchorInterval * prev.AnchorInterval
		var iv []byte
		var src string
		if seq == anchor {
			iv = anchorIV(anchor, prev.StreamIDHashVal)
			src = "anchor: SHA-256(streamIdHash + anchor)"
		} else {
			iv = incrementIV(prevIV, 1)
			src = "previous IV + 1"
		}
		ok := r.Seq == seq &&
			r.AnchorInterval == prev.AnchorInterval &&
			r.StreamIDHashVal == prev.StreamIDHashVal &&
			r.CertHashVal == prev.CertHashVal &&
			bytes.Equal(iv, actualIV)
		if ok {
			matched++
		}
		fmt.Fprintf(w, "| `%s` | %d | %d | %s | `%s` | %s |\n", r.Name, seq, anchor, src, hex.EncodeToString(iv), check(ok))
		prev, prevIV = r, actualIV
	}
	fmt.Fprintln(w)
	fmt.Fprintf(w, "**%d/%d segments matched the prediction made from the previous segment.**\n\n", matched, len(segs))
}
