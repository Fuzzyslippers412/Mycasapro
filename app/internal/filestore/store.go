package filestore

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

var (
	ErrInvalidKey = errors.New("invalid file key")
	ErrNotFound   = errors.New("file not found")
)

type Store interface {
	Save(context.Context, string, []byte) error
	Read(context.Context, string) ([]byte, error)
	Delete(context.Context, string) error
}

type LocalStore struct {
	root string
}

func NewLocalStore(root string) (*LocalStore, error) {
	root = strings.TrimSpace(root)
	if root == "" {
		return nil, errors.New("upload directory is required")
	}
	absolute, err := filepath.Abs(root)
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(absolute, 0o700); err != nil {
		return nil, err
	}
	return &LocalStore{root: absolute}, nil
}

func (s *LocalStore) Save(_ context.Context, key string, data []byte) error {
	path, err := s.path(key)
	if err != nil {
		return err
	}
	temporary, err := os.CreateTemp(s.root, ".upload-*")
	if err != nil {
		return err
	}
	temporaryName := temporary.Name()
	defer func() { _ = os.Remove(temporaryName) }()
	if err := temporary.Chmod(0o600); err != nil {
		_ = temporary.Close()
		return err
	}
	if _, err := temporary.Write(data); err != nil {
		_ = temporary.Close()
		return err
	}
	if err := temporary.Sync(); err != nil {
		_ = temporary.Close()
		return err
	}
	if err := temporary.Close(); err != nil {
		return err
	}
	return os.Rename(temporaryName, path)
}

func (s *LocalStore) Read(_ context.Context, key string) ([]byte, error) {
	path, err := s.path(key)
	if err != nil {
		return nil, err
	}
	data, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil, ErrNotFound
	}
	return data, err
}

func (s *LocalStore) Delete(_ context.Context, key string) error {
	path, err := s.path(key)
	if err != nil {
		return err
	}
	err = os.Remove(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	return err
}

func (s *LocalStore) path(key string) (string, error) {
	if !validKey(key) {
		return "", ErrInvalidKey
	}
	return filepath.Join(s.root, key), nil
}

type MemoryStore struct {
	mu    sync.RWMutex
	files map[string][]byte
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{files: make(map[string][]byte)}
}

func (s *MemoryStore) Save(_ context.Context, key string, data []byte) error {
	if !validKey(key) {
		return ErrInvalidKey
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	s.files[key] = append([]byte(nil), data...)
	return nil
}

func (s *MemoryStore) Read(_ context.Context, key string) ([]byte, error) {
	if !validKey(key) {
		return nil, ErrInvalidKey
	}
	s.mu.RLock()
	defer s.mu.RUnlock()
	data, ok := s.files[key]
	if !ok {
		return nil, ErrNotFound
	}
	return append([]byte(nil), data...), nil
}

func (s *MemoryStore) Delete(_ context.Context, key string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.files, key)
	return nil
}

func validKey(key string) bool {
	key = strings.TrimSpace(key)
	if key == "" || len(key) > 128 {
		return false
	}
	for _, char := range key {
		if (char >= 'a' && char <= 'z') || (char >= 'A' && char <= 'Z') || (char >= '0' && char <= '9') || char == '-' || char == '_' {
			continue
		}
		return false
	}
	return true
}
