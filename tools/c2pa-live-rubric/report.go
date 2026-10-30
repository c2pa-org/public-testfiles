package main

import (
	"fmt"
	"io"
	"sort"
	"strings"
)

// Criterion is one row of the rubric.
type Criterion struct {
	ID, Name, Spec, Code, Method string
	Applies                      func(*FileResult) bool
	Score                        func(*FileResult) Check
	Detail                       func(files []*FileResult) string // optional extra text for the result cell
}

func isSegment(r *FileResult) bool { return !r.IsInit }
func isInit(r *FileResult) bool    { return r.IsInit }
func anyFile(*FileResult) bool     { return true }

func toolCheck(r *FileResult, ok string, bad ...string) Check {
	if !r.ToolRan || r.ToolErr != "" {
		return NA
	}
	for _, b := range bad {
		if r.ToolFails[b] > 0 || r.ToolCodes[b] > 0 {
			return Fail
		}
	}
	return check(r.ToolCodes[ok] > 0)
}

// segmentIndexOK reports whether sequenceNumber follows the segment index used
// to address the segment (playlist media sequence or the number in its name).
func segmentIndexOK(r *FileResult, index map[string]uint64) bool {
	if n, ok := index[r.Name]; ok {
		return n == r.Seq
	}
	return false
}

func validationCriteria(useTool bool) []Criterion {
	method := "c2patool"
	cs := []Criterion{
		{ID: "V1", Name: "Initialization segment contains no `mdat`", Spec: "19.7.1", Code: "`livevideo.init.invalid`", Method: "Measured",
			Applies: isInit, Score: func(r *FileResult) Check { return check(!r.HasMdat) }},
		{ID: "V2", Name: "Each media segment has a C2PA Manifest Box", Spec: "19.7.1", Code: "`livevideo.segment.invalid`", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check { return check(r.HasManifest) }},
		{ID: "V3", Name: "Claim signature is valid and inside the certificate's validity period", Spec: "15", Code: "`claimSignature.mismatch`, `claimSignature.outsideValidity`", Method: method,
			Applies: anyFile, Score: func(r *FileResult) Check {
				return toolCheck(r, "claimSignature.validated", "claimSignature.mismatch", "claimSignature.outsideValidity", "claimSignature.missing")
			}},
		{ID: "V4", Name: "Time-stamp is valid for the claim signature", Spec: "10.3.2.5, 15", Code: "`timeStamp.mismatch`", Method: method,
			Applies: anyFile, Score: func(r *FileResult) Check {
				return toolCheck(r, "timeStamp.validated", "timeStamp.mismatch", "timeStamp.malformed")
			}},
		{ID: "V5", Name: "Every hashed URI in the claim matches its assertion", Spec: "15", Code: "`assertion.hashedURI.mismatch`", Method: "Measured",
			Applies: anyFile, Score: func(r *FileResult) Check { return check(r.HashedURITotal > 0 && r.HashedURIOK == r.HashedURITotal) },
			Detail: func(fs []*FileResult) string {
				ok, all := 0, 0
				for _, r := range fs {
					ok += r.HashedURIOK
					all += r.HashedURITotal
				}
				return fmt.Sprintf("%d/%d hashed URIs", ok, all)
			}},
		{ID: "V6", Name: "`c2pa.hash.bmff.v3` matches the segment bytes", Spec: "9.2.3, 15", Code: "`assertion.bmffHash.mismatch`", Method: method,
			Applies: anyFile, Score: func(r *FileResult) Check {
				return toolCheck(r, "assertion.bmffHash.match", "assertion.bmffHash.mismatch")
			}},
		{ID: "V7", Name: "`c2pa.livevideo.segment` is present", Spec: "19.3.2, 19.7.2", Code: "`livevideo.assertion.invalid`", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check { return check(r.HasLive) }},
		{ID: "V8", Name: "`sequenceNumber` is greater than the previous segment's", Spec: "19.7.2", Code: "`livevideo.assertion.invalid`", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check { return r.SeqIncreasing }},
		{ID: "V9", Name: "`streamId` equals the previous segment's", Spec: "19.7.2", Code: "`livevideo.assertion.invalid`", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check { return r.StreamConstant }},
		{ID: "V10", Name: "`continuityMethod` is present and supported", Spec: "19.7.2", Code: "`livevideo.continuityMethod.invalid`", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check {
				return check(r.ContinuityMethod == "com.ezdrm.anchor-chain" || r.ContinuityMethod == "c2pa.manifestId")
			},
			Detail: func(fs []*FileResult) string {
				seen := map[string]bool{}
				var ms []string
				for _, r := range fs {
					if r.ContinuityMethod != "" && !seen[r.ContinuityMethod] {
						seen[r.ContinuityMethod] = true
						ms = append(ms, "`"+r.ContinuityMethod+"`")
					}
				}
				return strings.Join(ms, ", ")
			}},
		{ID: "V11", Name: "`streamIdHash` equals `SHA-256(streamId)[0..15]`", Spec: "`com.ezdrm.anchor-chain`", Code: "`livevideo.segment.invalid`", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check { return r.StreamIDHash }},
		{ID: "V12", Name: "Anchor-chain continuity token recomputes", Spec: "`com.ezdrm.anchor-chain`", Code: "`livevideo.segment.invalid`", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check { return r.Token }},
		{ID: "V13", Name: "`cawg.identity` referenced assertion hashes match", Spec: "CAWG Identity Assertion", Code: "Identity assertion invalid", Method: "Measured",
			Applies: func(r *FileResult) bool { return r.HasCAWG }, Score: func(r *FileResult) Check { return check(r.CAWGRefAll > 0 && r.CAWGRefOK == r.CAWGRefAll) }},
		{ID: "V14", Name: "`cawg.identity` signature (`cawg.x509.cose`) is valid", Spec: "CAWG Identity Assertion", Code: "Identity assertion invalid", Method: method,
			Applies: func(r *FileResult) bool { return r.HasCAWG }, Score: func(r *FileResult) Check {
				c := toolCheck(r, "cawg.identity.well-formed")
				if c == Pass {
					for code := range r.ToolFails {
						if strings.HasPrefix(code, "cawg.") {
							return Fail
						}
					}
				}
				return c
			}},
	}
	if !useTool {
		for i := range cs {
			if cs[i].Method == method {
				cs[i].Method = "c2patool (not run)"
			}
		}
	}
	return cs
}

func conformanceCriteria(index map[string]uint64) []Criterion {
	return []Criterion{
		{ID: "G1", Name: "Claim uses `c2pa.claim.v2`", Spec: "10", Code: "None. Validators accept `c2pa.claim`", Method: "Measured",
			Applies: anyFile, Score: func(r *FileResult) Check { return check(r.ClaimLabel == "c2pa.claim.v2") }},
		{ID: "G2", Name: "Manifest identifier uses `urn:c2pa:`", Spec: "8", Code: "None", Method: "Measured",
			Applies: anyFile, Score: func(r *FileResult) Check { return check(strings.HasPrefix(r.ManifestLabel, "urn:c2pa:")) }},
		{ID: "G3", Name: "Claim signature carries a v2 time-stamp (`sigTst2`)", Spec: "10.3.2.5", Code: "None. Validators accept `sigTst`", Method: "Measured",
			Applies: anyFile, Score: func(r *FileResult) Check { return check(r.TimeStamp == "sigTst2") }},
		{ID: "G4", Name: "`sequenceNumber` matches `mfhd.sequence_number` or the segment index", Spec: "19.3.2", Code: "None", Method: "Measured",
			Applies: isSegment, Score: func(r *FileResult) Check {
				return check(r.HasSeq && (r.HasMFHD && uint64(r.MFHD) == r.Seq || segmentIndexOK(r, index)))
			},
			Detail: func(fs []*FileResult) string {
				mf, idx := 0, 0
				for _, r := range fs {
					if r.HasMFHD && uint64(r.MFHD) == r.Seq {
						mf++
					} else if segmentIndexOK(r, index) {
						idx++
					}
				}
				switch {
				case idx == 0:
					return "matches `mfhd.sequence_number`"
				case mf == 0:
					return "matches the segment index (playlist media sequence and file name)"
				}
				return fmt.Sprintf("%d match `mfhd`, %d match the segment index", mf, idx)
			}},
	}
}

func score(c Criterion, files []*FileResult) (pass, total int, failing []string) {
	for _, r := range files {
		if !c.Applies(r) {
			continue
		}
		switch c.Score(r) {
		case Pass:
			pass++
			total++
		case Fail:
			total++
			failing = append(failing, r.Name)
		}
	}
	return
}

func resultCell(c Criterion, files []*FileResult) string {
	pass, total, failing := score(c, files)
	if total == 0 {
		return "Not scored"
	}
	var cell string
	if pass == total {
		cell = fmt.Sprintf("**PASS** (%d/%d)", pass, total)
	} else {
		cell = fmt.Sprintf("**FAIL** (%d/%d; fails: %s)", pass, total, strings.Join(failing, ", "))
	}
	if c.Detail != nil {
		if d := c.Detail(files); d != "" {
			cell += ", " + d
		}
	}
	return cell
}

func writeCriteria(w io.Writer, cs []Criterion, files []*FileResult) {
	fmt.Fprintln(w, "| ID | Criterion | Spec | Status code on failure | Method | Result |")
	fmt.Fprintln(w, "|:--|:--|:--|:--|:--|:--|")
	for _, c := range cs {
		fmt.Fprintf(w, "| %s | %s | %s | %s | %s | %s |\n", c.ID, c.Name, c.Spec, c.Code, c.Method, resultCell(c, files))
	}
}

func writePerFile(w io.Writer, cs []Criterion, files []*FileResult) {
	fmt.Fprint(w, "| File |")
	for _, c := range cs {
		fmt.Fprintf(w, " %s |", c.ID)
	}
	fmt.Fprint(w, "\n|:--|")
	for range cs {
		fmt.Fprint(w, ":-:|")
	}
	fmt.Fprintln(w)
	for _, r := range files {
		name := "`" + r.Name + "`"
		if r.IsInit {
			name += " (init)"
		}
		fmt.Fprintf(w, "| %s |", name)
		for _, c := range cs {
			v := NA
			if c.Applies(r) {
				v = c.Score(r)
			}
			fmt.Fprintf(w, " %s |", v)
		}
		fmt.Fprintln(w)
	}
}

func writeToolTable(w io.Writer, files []*FileResult) {
	fmt.Fprintln(w, "| File | `validation_state` | Status codes reported |")
	fmt.Fprintln(w, "|:--|:--|:--|")
	for _, r := range files {
		if r.ToolErr != "" {
			fmt.Fprintf(w, "| `%s` | error | %s |\n", r.Name, r.ToolErr)
			continue
		}
		var codes []string
		for c, n := range r.ToolCodes {
			if n > 1 {
				codes = append(codes, fmt.Sprintf("`%s` x%d", c, n))
			} else {
				codes = append(codes, "`"+c+"`")
			}
		}
		sort.Strings(codes)
		fmt.Fprintf(w, "| `%s` | %s | %s |\n", r.Name, r.ToolState, strings.Join(codes, ", "))
	}
}
