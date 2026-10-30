package main

import (
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha256"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
)

// Check is the outcome of one criterion for one file.
type Check int

const (
	NA Check = iota // not applicable
	Pass
	Fail
)

func (c Check) String() string {
	switch c {
	case Pass:
		return "PASS"
	case Fail:
		return "FAIL"
	}
	return "—"
}

func check(ok bool) Check {
	if ok {
		return Pass
	}
	return Fail
}

// FileResult holds everything measured for one file.
type FileResult struct {
	Name    string
	Path    string
	Err     string
	IsInit  bool
	Boxes   []string
	HasMdat bool

	HasManifest   bool
	ManifestLabel string
	ClaimLabel    string
	TimeStamp     string // sigTst2, sigTst or none

	HashedURIOK, HashedURITotal int

	HasLive          bool
	Seq              uint64
	HasSeq           bool
	StreamID         string
	HasStreamID      bool
	ContinuityMethod string
	MFHD             uint32
	HasMFHD          bool

	StreamIDHash Check
	Token        Check

	// Anchor-chain parameters, used for predictive validation.
	AnchorInterval  uint64
	StreamIDHashVal string
	CertHashVal     string

	HasCAWG               bool
	CAWGRefOK, CAWGRefAll int

	// Set by the ordering pass.
	SeqIncreasing  Check
	StreamConstant Check

	// c2patool results.
	ToolRan   bool
	ToolErr   string
	ToolState string
	ToolCodes map[string]int // every reported code
	ToolFails map[string]int // codes reported as failures
}

func analyzeFile(path string) *FileResult {
	r := &FileResult{Name: filepath.Base(path), Path: path}
	data, err := os.ReadFile(path)
	if err != nil {
		r.Err = err.Error()
		return r
	}
	top, err := readBoxes(data, 0, len(data))
	if err != nil {
		r.Err = err.Error()
	}

	var store *Jumb
	var moofMdat []byte
	for i, b := range top {
		r.Boxes = append(r.Boxes, b.Type)
		switch b.Type {
		case "moov":
			r.IsInit = true
		case "mdat":
			r.HasMdat = true
		case "uuid":
			s, _, err := manifestStoreFromUUID(b.Payload(data))
			if err == nil && s != nil {
				store = s
			}
		case "moof":
			if i+1 < len(top) && top[i+1].Type == "mdat" {
				moofMdat = append(append([]byte{}, data[b.Start:b.End]...), data[top[i+1].Start:top[i+1].End]...)
			}
			if kids, err := readBoxes(data, b.Start+b.Header, b.End); err == nil {
				for _, k := range kids {
					if k.Type == "mfhd" && k.End-k.Start >= 16 {
						r.MFHD = binary.BigEndian.Uint32(data[k.Start+12:])
						r.HasMFHD = true
					}
				}
			}
		}
	}
	if store == nil || len(store.Children) == 0 {
		return r
	}
	r.HasManifest = true

	// The active manifest is the last manifest in the store.
	active := store.Children[len(store.Children)-1]
	r.ManifestLabel = active.Label
	assertions := active.Child("c2pa.assertions")

	// Claim and hashed URIs.
	claimBox := active.Child("c2pa.claim.v2")
	if claimBox == nil {
		claimBox = active.Child("c2pa.claim")
	}
	if claimBox != nil {
		r.ClaimLabel = claimBox.Label
		if claim, err := claimBox.CBOR(); err == nil {
			for _, key := range []string{"created_assertions", "gathered_assertions", "assertions"} {
				arr, _ := getArray(claim, key)
				for _, e := range arr {
					url, _ := getString(e, "url")
					want, _ := getBytes(e, "hash")
					r.HashedURITotal++
					if hashedURIMatches(assertions, url, want) {
						r.HashedURIOK++
					}
				}
			}
		}
	}

	// Claim signature time-stamp header.
	r.TimeStamp = "none"
	if sig := active.Child("c2pa.signature"); sig != nil {
		if v, err := sig.CBOR(); err == nil {
			if t, ok := v.(Tag); ok {
				v = t.Val
			}
			if arr, ok := v.([]any); ok && len(arr) >= 2 {
				if _, ok := mapGet(arr[1], "sigTst2"); ok {
					r.TimeStamp = "sigTst2"
				} else if _, ok := mapGet(arr[1], "sigTst"); ok {
					r.TimeStamp = "sigTst"
				}
			}
		}
	}

	if assertions == nil {
		return r
	}

	// Live video segment assertion.
	if lv := assertions.Child("c2pa.livevideo.segment"); lv != nil {
		r.HasLive = true
		if v, err := lv.CBOR(); err == nil {
			r.Seq, r.HasSeq = getUint(v, "sequenceNumber")
			r.StreamID, r.HasStreamID = getString(v, "streamId")
			r.ContinuityMethod, _ = getString(v, "continuityMethod")
			r.StreamIDHash, r.Token = checkAnchorChain(v, r, moofMdat)
		}
	}

	// CAWG identity assertion: verify each referenced assertion hash.
	if cawg := assertions.ChildPrefix("cawg.identity"); cawg != nil {
		r.HasCAWG = true
		if v, err := cawg.CBOR(); err == nil {
			sp, _ := mapGet(v, "signer_payload")
			refs, _ := getArray(sp, "referenced_assertions")
			for _, e := range refs {
				url, _ := getString(e, "url")
				want, _ := getBytes(e, "hash")
				r.CAWGRefAll++
				if hashedURIMatches(assertions, url, want) {
					r.CAWGRefOK++
				}
			}
		}
	}
	return r
}

// hashedURIMatches resolves a self#jumbf URL to an assertion and compares its
// SHA-256 (over the superbox contents, without its 8-byte header) with want.
func hashedURIMatches(assertions *Jumb, url string, want []byte) bool {
	if assertions == nil || len(want) == 0 {
		return false
	}
	i := strings.LastIndex(url, "c2pa.assertions/")
	if i < 0 {
		return false
	}
	box := assertions.Child(url[i+len("c2pa.assertions/"):])
	if box == nil {
		return false
	}
	h := sha256.Sum256(box.Raw[8:])
	return bytes.Equal(h[:], want)
}

// anchorField reads an anchor-chain field, accepting both the plain name and the
// com.ezdrm.-prefixed name.
func anchorField(v any, name string) any {
	if x, ok := mapGet(v, name); ok {
		return x
	}
	x, _ := mapGet(v, "com.ezdrm."+name)
	return x
}

// checkAnchorChain verifies streamIdHash and the com.ezdrm.anchor-chain token.
func checkAnchorChain(v any, r *FileResult, moofMdat []byte) (Check, Check) {
	sidh, _ := anchorField(v, "streamIdHash").(string)
	certHash, _ := anchorField(v, "certHash").(string)
	want, _ := anchorField(v, "continuityToken").(string)
	interval, _ := anchorField(v, "anchorSegmentIndex").(uint64)
	r.AnchorInterval, r.StreamIDHashVal, r.CertHashVal = interval, sidh, certHash

	sidCheck := NA
	if sidh != "" && r.HasStreamID {
		h := sha256.Sum256([]byte(r.StreamID))
		sidCheck = check(base64.StdEncoding.EncodeToString(h[:16]) == sidh)
	}
	if want == "" || interval == 0 || len(certHash) < 16 || !r.HasSeq {
		return sidCheck, NA
	}
	if len(moofMdat) == 0 {
		return sidCheck, Fail
	}
	tok, err := anchorChainToken(moofMdat, r.Seq, interval, sidh, certHash)
	if err != nil {
		return sidCheck, Fail
	}
	return sidCheck, check(tok == want)
}

// anchorChainToken computes the com.ezdrm.anchor-chain continuity token:
// AES-128-CBC (PKCS#7) over moof+mdat, key = UTF-8(certHash[0:16]),
// IV = SHA-256(UTF-8(streamIdHash + decimal(anchor)))[0:16] incremented
// (sequenceNumber - anchor) times; token = Base64(last ciphertext block).
func anchorChainToken(data []byte, seq, interval uint64, streamIDHash, certHash string) (string, error) {
	iv := segmentIV(seq, interval, streamIDHash)
	block, err := aes.NewCipher([]byte(certHash[:16]))
	if err != nil {
		return "", err
	}
	pad := aes.BlockSize - len(data)%aes.BlockSize
	in := append(append([]byte{}, data...), bytes.Repeat([]byte{byte(pad)}, pad)...)
	out := make([]byte, len(in))
	cipher.NewCBCEncrypter(block, iv).CryptBlocks(out, in)
	return base64.StdEncoding.EncodeToString(out[len(out)-aes.BlockSize:]), nil
}

// anchorIV derives the IV of an anchor segment.
func anchorIV(anchor uint64, streamIDHash string) []byte {
	h := sha256.Sum256([]byte(streamIDHash + strconv.FormatUint(anchor, 10)))
	return append([]byte{}, h[:16]...)
}

// incrementIV adds n to iv as a 128-bit big-endian integer.
func incrementIV(iv []byte, n uint64) []byte {
	out := append([]byte{}, iv...)
	for ; n > 0; n-- {
		for i := len(out) - 1; i >= 0; i-- {
			out[i]++
			if out[i] != 0 {
				break
			}
		}
	}
	return out
}

// segmentIV derives the IV of any segment from its anchor.
func segmentIV(seq, interval uint64, streamIDHash string) []byte {
	anchor := seq / interval * interval
	return incrementIV(anchorIV(anchor, streamIDHash), seq-anchor)
}

// runC2PATool runs c2patool on the file and collects the reported status codes.
func runC2PATool(tool string, r *FileResult) {
	out, err := exec.Command(tool, r.Path).Output()
	r.ToolRan = true
	if err != nil && len(out) == 0 {
		r.ToolErr = err.Error()
		return
	}
	var doc map[string]any
	if err := json.Unmarshal(out, &doc); err != nil {
		r.ToolErr = fmt.Sprintf("cannot parse c2patool output: %v", err)
		return
	}
	r.ToolState, _ = doc["validation_state"].(string)
	r.ToolCodes = map[string]int{}
	r.ToolFails = map[string]int{}
	add := func(list any, fail bool) {
		items, _ := list.([]any)
		for _, it := range items {
			m, _ := it.(map[string]any)
			code, _ := m["code"].(string)
			if code == "" {
				continue
			}
			r.ToolCodes[code]++
			if fail {
				r.ToolFails[code]++
			}
		}
	}
	if vr, ok := doc["validation_results"].(map[string]any); ok {
		if am, ok := vr["activeManifest"].(map[string]any); ok {
			add(am["success"], false)
			add(am["informational"], false)
			add(am["failure"], true)
		}
	}
	// validation_status repeats failures and informational codes; count only
	// codes not already reported above.
	if vs, ok := doc["validation_status"].([]any); ok {
		for _, it := range vs {
			m, _ := it.(map[string]any)
			code, _ := m["code"].(string)
			if code != "" && r.ToolCodes[code] == 0 {
				r.ToolCodes[code]++
				r.ToolFails[code]++
			}
		}
	}
}
