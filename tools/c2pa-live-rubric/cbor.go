package main

import (
	"encoding/binary"
	"errors"
	"fmt"
	"math"
)

// Tag is a CBOR tagged value.
type Tag struct {
	Num uint64
	Val any
}

type cborDecoder struct {
	b []byte
	p int
}

var errShort = errors.New("cbor: unexpected end of data")

// decodeCBOR decodes one CBOR data item. Maps decode to map[any]any; byte-string
// keys are converted to string so that the map stays usable.
func decodeCBOR(b []byte) (any, error) {
	d := &cborDecoder{b: b}
	return d.item()
}

func (d *cborDecoder) need(n int) error {
	if d.p+n > len(d.b) {
		return errShort
	}
	return nil
}

func (d *cborDecoder) arg(ai byte) (uint64, bool, error) {
	switch {
	case ai < 24:
		return uint64(ai), false, nil
	case ai == 24:
		if err := d.need(1); err != nil {
			return 0, false, err
		}
		v := uint64(d.b[d.p])
		d.p++
		return v, false, nil
	case ai == 25:
		if err := d.need(2); err != nil {
			return 0, false, err
		}
		v := uint64(binary.BigEndian.Uint16(d.b[d.p:]))
		d.p += 2
		return v, false, nil
	case ai == 26:
		if err := d.need(4); err != nil {
			return 0, false, err
		}
		v := uint64(binary.BigEndian.Uint32(d.b[d.p:]))
		d.p += 4
		return v, false, nil
	case ai == 27:
		if err := d.need(8); err != nil {
			return 0, false, err
		}
		v := binary.BigEndian.Uint64(d.b[d.p:])
		d.p += 8
		return v, false, nil
	case ai == 31:
		return 0, true, nil // indefinite length
	}
	return 0, false, fmt.Errorf("cbor: invalid additional info %d", ai)
}

func (d *cborDecoder) isBreak() bool {
	return d.p < len(d.b) && d.b[d.p] == 0xff
}

func (d *cborDecoder) item() (any, error) {
	if err := d.need(1); err != nil {
		return nil, err
	}
	ib := d.b[d.p]
	d.p++
	mt, ai := ib>>5, ib&0x1f

	if mt == 7 {
		switch ai {
		case 20:
			return false, nil
		case 21:
			return true, nil
		case 22, 23:
			return nil, nil
		case 25:
			if err := d.need(2); err != nil {
				return nil, err
			}
			h := binary.BigEndian.Uint16(d.b[d.p:])
			d.p += 2
			return halfToFloat(h), nil
		case 26:
			if err := d.need(4); err != nil {
				return nil, err
			}
			v := math.Float32frombits(binary.BigEndian.Uint32(d.b[d.p:]))
			d.p += 4
			return float64(v), nil
		case 27:
			if err := d.need(8); err != nil {
				return nil, err
			}
			v := math.Float64frombits(binary.BigEndian.Uint64(d.b[d.p:]))
			d.p += 8
			return v, nil
		}
		if ai < 24 {
			return fmt.Sprintf("simple(%d)", ai), nil
		}
		return nil, fmt.Errorf("cbor: unsupported simple value %d", ai)
	}

	n, indef, err := d.arg(ai)
	if err != nil {
		return nil, err
	}
	switch mt {
	case 0:
		return n, nil
	case 1:
		return -1 - int64(n), nil
	case 2, 3:
		var out []byte
		if indef {
			for !d.isBreak() {
				chunk, err := d.item()
				if err != nil {
					return nil, err
				}
				switch c := chunk.(type) {
				case []byte:
					out = append(out, c...)
				case string:
					out = append(out, c...)
				}
			}
			d.p++
		} else {
			if err := d.need(int(n)); err != nil {
				return nil, err
			}
			out = d.b[d.p : d.p+int(n)]
			d.p += int(n)
		}
		if mt == 3 {
			return string(out), nil
		}
		return out, nil
	case 4:
		arr := []any{}
		for i := uint64(0); indef && !d.isBreak() || !indef && i < n; i++ {
			v, err := d.item()
			if err != nil {
				return nil, err
			}
			arr = append(arr, v)
		}
		if indef {
			d.p++
		}
		return arr, nil
	case 5:
		m := map[any]any{}
		for i := uint64(0); indef && !d.isBreak() || !indef && i < n; i++ {
			k, err := d.item()
			if err != nil {
				return nil, err
			}
			v, err := d.item()
			if err != nil {
				return nil, err
			}
			if kb, ok := k.([]byte); ok {
				k = string(kb)
			}
			m[k] = v
		}
		if indef {
			d.p++
		}
		return m, nil
	case 6:
		v, err := d.item()
		if err != nil {
			return nil, err
		}
		return Tag{Num: n, Val: v}, nil
	}
	return nil, fmt.Errorf("cbor: unknown major type %d", mt)
}

func halfToFloat(h uint16) float64 {
	exp := (h >> 10) & 0x1f
	mant := float64(h & 0x3ff)
	var v float64
	switch exp {
	case 0:
		v = mant * math.Pow(2, -24)
	case 31:
		if mant == 0 {
			v = math.Inf(1)
		} else {
			v = math.NaN()
		}
	default:
		v = (mant + 1024) * math.Pow(2, float64(exp)-25)
	}
	if h&0x8000 != 0 {
		return -v
	}
	return v
}

// Helpers for navigating decoded CBOR.

func mapGet(v any, key string) (any, bool) {
	m, ok := v.(map[any]any)
	if !ok {
		return nil, false
	}
	r, ok := m[key]
	return r, ok
}

func getString(v any, key string) (string, bool) {
	r, ok := mapGet(v, key)
	if !ok {
		return "", false
	}
	s, ok := r.(string)
	return s, ok
}

func getUint(v any, key string) (uint64, bool) {
	r, ok := mapGet(v, key)
	if !ok {
		return 0, false
	}
	u, ok := r.(uint64)
	return u, ok
}

func getBytes(v any, key string) ([]byte, bool) {
	r, ok := mapGet(v, key)
	if !ok {
		return nil, false
	}
	b, ok := r.([]byte)
	return b, ok
}

func getArray(v any, key string) ([]any, bool) {
	r, ok := mapGet(v, key)
	if !ok {
		return nil, false
	}
	a, ok := r.([]any)
	return a, ok
}
