package filestore

import (
	"bytes"
	"context"
	"errors"
	"os"
	"path/filepath"
	"testing"
)

func TestLocalStorePersistsPrivateFiles(t *testing.T) {
	root := t.TempDir()
	files, err := NewLocalStore(root)
	if err != nil {
		t.Fatalf("create local store: %v", err)
	}
	ctx := context.Background()
	want := []byte("repair-photo-bytes")

	if err := files.Save(ctx, "file_abc123", want); err != nil {
		t.Fatalf("save: %v", err)
	}
	got, err := files.Read(ctx, "file_abc123")
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if !bytes.Equal(got, want) {
		t.Fatalf("content mismatch: got=%q want=%q", got, want)
	}
	info, err := os.Stat(filepath.Join(root, "file_abc123"))
	if err != nil {
		t.Fatalf("stat: %v", err)
	}
	if permissions := info.Mode().Perm(); permissions != 0o600 {
		t.Fatalf("file permissions mismatch: got=%o want=600", permissions)
	}

	if err := files.Delete(ctx, "file_abc123"); err != nil {
		t.Fatalf("delete: %v", err)
	}
	if _, err := files.Read(ctx, "file_abc123"); !errors.Is(err, ErrNotFound) {
		t.Fatalf("expected ErrNotFound after delete, got=%v", err)
	}
}

func TestLocalStoreRejectsTraversalKeys(t *testing.T) {
	files, err := NewLocalStore(t.TempDir())
	if err != nil {
		t.Fatalf("create local store: %v", err)
	}
	for _, key := range []string{"", "../secret", "nested/file", "file.txt"} {
		if err := files.Save(context.Background(), key, []byte("nope")); !errors.Is(err, ErrInvalidKey) {
			t.Fatalf("key %q: expected ErrInvalidKey, got=%v", key, err)
		}
	}
}
