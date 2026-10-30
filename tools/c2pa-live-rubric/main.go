// c2pa-live-rubric scores a set of live video segments that use the C2PA
// Per-segment C2PA Manifest Box method (C2PA 2.3 and 2.4, Section 19.3) against
// a validation rubric, and writes the result as Markdown.
//
// Usage:
//
//	c2pa-live-rubric [-c2patool path] [-playlist index.m3u8] [-o rubric.md] <folder>
package main

import (
	"bufio"
	"bytes"
	"flag"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

func main() {
	tool := flag.String("c2patool", "", "path to c2patool; when set, signature, time-stamp, BMFF hash and CAWG signature are scored with it")
	playlist := flag.String("playlist", "", "HLS playlist (index.m3u8) used to map segment files to their media sequence numbers")
	output := flag.String("o", "", "write the Markdown report to this file instead of stdout")
	flag.Usage = func() {
		fmt.Fprintln(os.Stderr, "usage: c2pa-live-rubric [-c2patool path] [-playlist index.m3u8] [-o rubric.md] <folder>")
		flag.PrintDefaults()
	}
	flag.Parse()
	if flag.NArg() != 1 {
		flag.Usage()
		os.Exit(2)
	}
	dir := flag.Arg(0)

	paths, err := mediaFiles(dir)
	if err != nil || len(paths) == 0 {
		fmt.Fprintf(os.Stderr, "no .mp4/.m4s files in %s: %v\n", dir, err)
		os.Exit(1)
	}

	var files []*FileResult
	for _, p := range paths {
		r := analyzeFile(p)
		if *tool != "" {
			runC2PATool(*tool, r)
		}
		files = append(files, r)
	}
	orderAndSequence(files)

	index, indexSource := segmentIndex(files, *playlist)

	var w io.Writer = os.Stdout
	if *output != "" {
		f, err := os.Create(*output)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		defer f.Close()
		w = f
	}
	writeReport(w, dir, *tool, indexSource, files, index)
}

func mediaFiles(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var out []string
	for _, e := range entries {
		ext := strings.ToLower(filepath.Ext(e.Name()))
		if !e.IsDir() && (ext == ".mp4" || ext == ".m4s" || ext == ".cmfv" || ext == ".cmfa") {
			out = append(out, filepath.Join(dir, e.Name()))
		}
	}
	return out, nil
}

// orderAndSequence puts initialization segments first and media segments in
// sequenceNumber order, then applies the "previous segment" checks of 19.7.2.
func orderAndSequence(files []*FileResult) {
	sort.SliceStable(files, func(i, j int) bool {
		a, b := files[i], files[j]
		if a.IsInit != b.IsInit {
			return a.IsInit
		}
		if a.HasSeq && b.HasSeq && a.Seq != b.Seq {
			return a.Seq < b.Seq
		}
		return a.Name < b.Name
	})
	var prev *FileResult
	for _, r := range files {
		if r.IsInit || !r.HasLive {
			continue
		}
		if prev == nil {
			r.SeqIncreasing = check(r.HasSeq)
			r.StreamConstant = check(r.HasStreamID)
		} else {
			r.SeqIncreasing = check(r.HasSeq && r.Seq > prev.Seq)
			r.StreamConstant = check(r.HasStreamID && r.StreamID == prev.StreamID)
		}
		prev = r
	}
}

var trailingNumber = regexp.MustCompile(`(\d+)\.[A-Za-z0-9]+$`)

// segmentIndex maps file names to the index used to address each segment: the
// HLS media sequence number from the playlist when given, otherwise the number
// at the end of the file name.
func segmentIndex(files []*FileResult, playlist string) (map[string]uint64, string) {
	index := map[string]uint64{}
	if playlist != "" {
		if f, err := os.Open(playlist); err == nil {
			defer f.Close()
			var seq uint64
			sc := bufio.NewScanner(f)
			for sc.Scan() {
				line := strings.TrimSpace(sc.Text())
				switch {
				case strings.HasPrefix(line, "#EXT-X-MEDIA-SEQUENCE:"):
					seq, _ = strconv.ParseUint(strings.TrimPrefix(line, "#EXT-X-MEDIA-SEQUENCE:"), 10, 64)
				case line != "" && !strings.HasPrefix(line, "#"):
					index[filepath.Base(line)] = seq
					seq++
				}
			}
		}
	}
	source := "HLS playlist media sequence"
	if len(index) == 0 {
		source = "number in the segment file name"
	}
	for _, r := range files {
		if _, ok := index[r.Name]; ok {
			continue
		}
		if m := trailingNumber.FindStringSubmatch(r.Name); m != nil && !r.IsInit {
			n, _ := strconv.ParseUint(m[1], 10, 64)
			index[r.Name] = n
		}
	}
	return index, source
}

func toolVersion(tool string) string {
	out, err := exec.Command(tool, "--version").Output()
	if err != nil {
		return tool
	}
	return strings.TrimSpace(string(bytes.SplitN(out, []byte("\n"), 2)[0]))
}

func writeReport(w io.Writer, dir, tool, indexSource string, files []*FileResult, index map[string]uint64) {
	useTool := tool != ""
	vc := validationCriteria(useTool)
	gc := conformanceCriteria(index)

	inits, segs := 0, 0
	for _, r := range files {
		if r.IsInit {
			inits++
		} else {
			segs++
		}
	}
	allPass := true
	for _, c := range vc {
		if pass, total, _ := score(c, files); pass != total {
			allPass = false
		}
	}

	fmt.Fprintln(w, "# C2PA live segment validation rubric")
	fmt.Fprintln(w)
	fmt.Fprintf(w, "- **Method:** Per-segment C2PA Manifest Box method (C2PA 2.3 and 2.4, Section 19.3)\n")
	fmt.Fprintf(w, "- **Input:** `%s`: %d initialization segment(s), %d media segment(s)\n", filepath.ToSlash(dir), inits, segs)
	if useTool {
		fmt.Fprintf(w, "- **Validator:** %s\n", toolVersion(tool))
	} else {
		fmt.Fprintln(w, "- **Validator:** not run. Pass `-c2patool` to score V3, V4, V6 and V14")
	}
	fmt.Fprintf(w, "- **Segment index source:** %s\n", indexSource)
	fmt.Fprintln(w, "- **Out of scope:** signer and time-stamp authority trust. The rubric scores signature and time-stamp validity, not trust-list membership")
	fmt.Fprintln(w)
	switch {
	case allPass && useTool:
		fmt.Fprintf(w, "**Result: all %d files pass validation.**\n\n", len(files))
	case allPass:
		fmt.Fprintf(w, "**Result: all %d files pass the measured criteria. V3, V4, V6 and V14 were not run.**\n\n", len(files))
	default:
		fmt.Fprintln(w, "**Result: one or more validation criteria fail. See below.**")
		fmt.Fprintln(w)
	}

	fmt.Fprintln(w, "## Validation rubric")
	fmt.Fprintln(w)
	fmt.Fprintln(w, "Checks a validator performs (Chapter 15, Section 19.7, the `com.ezdrm.anchor-chain` continuity method and the CAWG identity assertion).")
	fmt.Fprintln(w)
	writeCriteria(w, vc, files)
	fmt.Fprintln(w)

	fmt.Fprintln(w, "### Results per file")
	fmt.Fprintln(w)
	writePerFile(w, vc, files)
	fmt.Fprintln(w)

	if useTool {
		fmt.Fprintln(w, "### Validator output per file")
		fmt.Fprintln(w)
		writeToolTable(w, files)
		fmt.Fprintln(w)
	}

	writePrediction(w, files)

	fmt.Fprintln(w, "## Generator conformance notes")
	fmt.Fprintln(w)
	fmt.Fprintln(w, "Requirements on the claim generator. Validators do not reject files that miss these, so they do not affect the validation result above.")
	fmt.Fprintln(w)
	writeCriteria(w, gc, files)
	fmt.Fprintln(w)
	writePerFile(w, gc, files)
}
