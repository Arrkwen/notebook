## Uint<-->byte

```go
import "encoding/binary"

func Uint8ToBytes(x uint8) []byte {
	b := make([]byte, 1)
	b[0] = x
	return b
}

func BytesToUint8(b []byte) uint8 {
	var x uint8
	buf := bytes.NewBuffer(b)
	binary.Read(buf, binary.LittleEndian, &x)
	return x
}

func Uint16ToBytes(x uint16) []byte {
	b := make([]byte, 2)
	binary.LittleEndian.PutUint16(b, x)
	return b
}

func BytesToUint16(b []byte) uint16 {
	return binary.LittleEndian.Uint16(b)
}

func Uint32ToBytes(x uint32) []byte {
	b := make([]byte, 4)
	binary.LittleEndian.PutUint32(b, x)
	return b
}

func BytesToUint32(b []byte) uint32 {
	return binary.LittleEndian.Uint32(b)
}

func Uint64ToBytes(x uint64) []byte {
	b := make([]byte, 8)
	binary.LittleEndian.PutUint64(b, x)
	return b
}

func BytesToUint64(b []byte) uint64 {
	return binary.LittleEndian.Uint64(b)
}

```

## serialize

```go
import "os"
func Serialize(path string, label int64) error {
	f, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE, 0644)
	if err != nil {
		log.WithError(err).Errorf("failed to create file %s", path)
		return err
	}
	defer f.Close()

	off, err := f.Seek(0, os.SEEK_END)

	// write label
	b := utils.Uint64ToBytes(uint64(label))
	n, err := f.WriteAt(b, off)
	if err != nil {
		return err
	}
	off += int64(n)
}
```
