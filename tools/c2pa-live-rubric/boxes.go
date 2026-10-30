package main

import (
	"bytes"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"strings"
)

// C2PAUUID is the ISO BMFF 'uuid' user type of the C2PA Manifest Box (A.5.1).
var C2PAUUID = mustHex("d8fec3d61b0e483c92975828877ec481")

func mustHex(s string) []byte {
	b, err := hex.DecodeString(s)
	if err != nil {
		panic(err)
	}
	return b
}

// Box is an ISO BMFF or JUMBF box.
type Box struct {
	Type       string
	Start, End int // absolute offsets of the whole box
	Header     int // header length (8 or 16)
}

func (b Box) Payload(data []byte) []byte { return data[b.Start+b.Header : b.End] }

// readBoxes reads the boxes in data[off:end].
func readBoxes(data []byte, off, end int) ([]Box, error) {
	var out []Box
	for off < end {
		if off+8 > end {
			return out, fmt.Errorf("truncated box header at %d", off)
		}
		size := int(binary.BigEndian.Uint32(data[off:]))
		header := 8
		switch size {
		case 1:
			if off+16 > end {
				return out, fmt.Errorf("truncated largesize at %d", off)
			}
			size = int(binary.BigEndian.Uint64(data[off+8:]))
			header = 16
		case 0:
			size = end - off
		}
		if size < header || off+size > end {
			return out, fmt.Errorf("invalid box size %d at %d", size, off)
		}
		out = append(out, Box{Type: string(data[off+4 : off+8]), Start: off, End: off + size, Header: header})
		off += size
	}
	return out, nil
}

// JUMBF superbox ("jumb") with its description ("jumd").
type Jumb struct {
	Label    string
	TypeUUID []byte
	Raw      []byte // the whole superbox, including its 8-byte header
	Children []*Jumb
	Content  []Content // non-superbox content boxes (cbor, json, ...)
}

type Content struct {
	Type string
	Data []byte
}

func parseJumb(raw []byte) (*Jumb, error) {
	boxes, err := readBoxes(raw, 8, len(raw))
	if err != nil {
		return nil, err
	}
	if len(boxes) == 0 || boxes[0].Type != "jumd" {
		return nil, fmt.Errorf("jumb without jumd")
	}
	j := &Jumb{Raw: raw}
	d := boxes[0].Payload(raw)
	if len(d) < 17 {
		return nil, fmt.Errorf("short jumd")
	}
	j.TypeUUID = d[:16]
	toggles := d[16]
	if toggles&0x02 != 0 {
		if e := bytes.IndexByte(d[17:], 0); e >= 0 {
			j.Label = string(d[17 : 17+e])
		}
	}
	for _, b := range boxes[1:] {
		if b.Type == "jumb" {
			c, err := parseJumb(raw[b.Start:b.End])
			if err != nil {
				return nil, err
			}
			j.Children = append(j.Children, c)
		} else {
			j.Content = append(j.Content, Content{Type: b.Type, Data: b.Payload(raw)})
		}
	}
	return j, nil
}

func (j *Jumb) Child(label string) *Jumb {
	for _, c := range j.Children {
		if c.Label == label {
			return c
		}
	}
	return nil
}

func (j *Jumb) ChildPrefix(prefix string) *Jumb {
	for _, c := range j.Children {
		if strings.HasPrefix(c.Label, prefix) {
			return c
		}
	}
	return nil
}

// CBOR decodes the first cbor content box of the superbox.
func (j *Jumb) CBOR() (any, error) {
	for _, c := range j.Content {
		if c.Type == "cbor" {
			return decodeCBOR(c.Data)
		}
	}
	return nil, fmt.Errorf("%s: no cbor content", j.Label)
}

// manifestStoreFromUUID extracts the JUMBF manifest store from a C2PA 'uuid' box
// payload: usertype(16) version/flags(4) purpose NUL [merkle offset(8)] JUMBF.
func manifestStoreFromUUID(payload []byte) (*Jumb, string, error) {
	if len(payload) < 21 || !bytes.Equal(payload[:16], C2PAUUID) {
		return nil, "", fmt.Errorf("not a C2PA uuid box")
	}
	p := 20
	e := bytes.IndexByte(payload[p:], 0)
	if e < 0 {
		return nil, "", fmt.Errorf("unterminated purpose")
	}
	purpose := string(payload[p : p+e])
	p += e + 1
	if purpose == "manifest" {
		p += 8
	}
	if purpose != "manifest" && purpose != "original" && purpose != "update" {
		return nil, purpose, nil // auxiliary box, no manifest store
	}
	if p+8 > len(payload) {
		return nil, purpose, fmt.Errorf("no JUMBF after purpose")
	}
	size := int(binary.BigEndian.Uint32(payload[p:]))
	if size < 8 || p+size > len(payload) || string(payload[p+4:p+8]) != "jumb" {
		return nil, purpose, fmt.Errorf("invalid JUMBF superbox")
	}
	store, err := parseJumb(payload[p : p+size])
	return store, purpose, err
}
