package command

import (
	"archive/tar"
	"compress/gzip"
	"context"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const maxBackupEntrySize = int64(100 << 30)

func createBackup(ctx context.Context, cfg config, destination string) error {
	if destination == "" {
		destination = fmt.Sprintf("mycasapro-backup-%s.tar.gz", time.Now().UTC().Format("20060102-150405"))
	}
	absDestination, err := filepath.Abs(destination)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(absDestination), 0o700); err != nil {
		return fmt.Errorf("create backup directory: %w", err)
	}

	databaseDump, err := os.CreateTemp(cfg.Home, "database-*.dump")
	if err != nil {
		return err
	}
	defer os.Remove(databaseDump.Name())
	defer databaseDump.Close()
	if err := runComposeIO(ctx, cfg, nil, databaseDump, "exec", "-T", "postgres", "pg_dump", "-U", "mycasapro", "--format=custom", "mycasapro"); err != nil {
		return fmt.Errorf("back up database: %w", err)
	}
	if err := databaseDump.Close(); err != nil {
		return err
	}

	uploadDump, err := os.CreateTemp(cfg.Home, "uploads-*.tar.gz")
	if err != nil {
		return err
	}
	defer os.Remove(uploadDump.Name())
	defer uploadDump.Close()
	if err := runComposeIO(ctx, cfg, nil, uploadDump, "exec", "-T", "app", "tar", "-czf", "-", "-C", "/data/uploads", "."); err != nil {
		return fmt.Errorf("back up uploads: %w", err)
	}
	if err := uploadDump.Close(); err != nil {
		return err
	}

	output, err := os.OpenFile(absDestination, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
	if err != nil {
		if errors.Is(err, os.ErrExist) {
			return fmt.Errorf("backup already exists: %s", absDestination)
		}
		return err
	}
	removeIncomplete := true
	defer func() {
		_ = output.Close()
		if removeIncomplete {
			_ = os.Remove(absDestination)
		}
	}()

	gzipWriter := gzip.NewWriter(output)
	tarWriter := tar.NewWriter(gzipWriter)
	for _, item := range []struct {
		name string
		path string
	}{
		{name: "database.dump", path: databaseDump.Name()},
		{name: "uploads.tar.gz", path: uploadDump.Name()},
	} {
		if err := addBackupFile(tarWriter, item.name, item.path); err != nil {
			return err
		}
	}
	if err := tarWriter.Close(); err != nil {
		return err
	}
	if err := gzipWriter.Close(); err != nil {
		return err
	}
	if err := output.Sync(); err != nil {
		return err
	}
	if err := output.Close(); err != nil {
		return err
	}
	removeIncomplete = false
	fmt.Printf("Backup created: %s\n", absDestination)
	return nil
}

func addBackupFile(writer *tar.Writer, name, path string) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil {
		return err
	}
	if err := writer.WriteHeader(&tar.Header{
		Name:    name,
		Mode:    0o600,
		Size:    info.Size(),
		ModTime: time.Now().UTC(),
	}); err != nil {
		return err
	}
	_, err = io.Copy(writer, file)
	return err
}

func restoreBackup(ctx context.Context, cfg config, source string) (restoreErr error) {
	absSource, err := filepath.Abs(source)
	if err != nil {
		return err
	}
	databasePath, uploadsPath, cleanup, err := extractBackup(cfg.Home, absSource)
	if err != nil {
		return err
	}
	defer cleanup()
	if err := validateUploadArchive(uploadsPath); err != nil {
		return fmt.Errorf("unsafe upload archive: %w", err)
	}

	if err := runCompose(ctx, cfg, "stop", "web", "app"); err != nil {
		return err
	}
	defer func() {
		if err := runCompose(context.Background(), cfg, "up", "-d", "--remove-orphans"); restoreErr == nil && err != nil {
			restoreErr = err
		}
	}()
	if err := runCompose(ctx, cfg, "up", "-d", "postgres"); err != nil {
		return err
	}
	if err := waitForPostgres(ctx, cfg, 60*time.Second); err != nil {
		return err
	}

	databaseDump, err := os.Open(databasePath)
	if err != nil {
		return err
	}
	if err := runComposeIO(ctx, cfg, databaseDump, nil, "exec", "-T", "postgres", "pg_restore", "--clean", "--if-exists", "--no-owner", "--no-privileges", "-U", "mycasapro", "-d", "mycasapro"); err != nil {
		_ = databaseDump.Close()
		return fmt.Errorf("restore database: %w", err)
	}
	if err := databaseDump.Close(); err != nil {
		return err
	}

	uploadDump, err := os.Open(uploadsPath)
	if err != nil {
		return err
	}
	restoreScript := "find /data/uploads -mindepth 1 -delete && tar -xzf - -C /data/uploads"
	if err := runComposeIO(ctx, cfg, uploadDump, nil, "run", "--rm", "--no-deps", "--entrypoint", "sh", "app", "-c", restoreScript); err != nil {
		_ = uploadDump.Close()
		return fmt.Errorf("restore uploads: %w", err)
	}
	if err := uploadDump.Close(); err != nil {
		return err
	}

	fmt.Printf("Backup restored from %s\n", absSource)
	return nil
}

func waitForPostgres(ctx context.Context, cfg config, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		cmd := composeCommand(ctx, cfg, "exec", "-T", "postgres", "pg_isready", "-U", "mycasapro", "-d", "mycasapro")
		if cmd.Run() == nil {
			return nil
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(time.Second):
		}
	}
	return errors.New("PostgreSQL did not become ready")
}

func extractBackup(home, source string) (databasePath, uploadsPath string, cleanup func(), err error) {
	tempDir, err := os.MkdirTemp(home, "restore-*")
	if err != nil {
		return "", "", func() {}, err
	}
	cleanup = func() { _ = os.RemoveAll(tempDir) }
	fail := func(err error) (string, string, func(), error) {
		cleanup()
		return "", "", func() {}, err
	}

	file, err := os.Open(source)
	if err != nil {
		return fail(err)
	}
	defer file.Close()
	gzipReader, err := gzip.NewReader(file)
	if err != nil {
		return fail(errors.New("backup is not a valid gzip archive"))
	}
	defer gzipReader.Close()
	tarReader := tar.NewReader(gzipReader)
	found := make(map[string]string)
	for {
		header, nextErr := tarReader.Next()
		if errors.Is(nextErr, io.EOF) {
			break
		}
		if nextErr != nil {
			return fail(nextErr)
		}
		if header.Typeflag != tar.TypeReg || (header.Name != "database.dump" && header.Name != "uploads.tar.gz") {
			return fail(fmt.Errorf("unexpected backup entry %q", header.Name))
		}
		if _, duplicate := found[header.Name]; duplicate {
			return fail(fmt.Errorf("duplicate backup entry %q", header.Name))
		}
		if header.Size < 0 || header.Size > maxBackupEntrySize {
			return fail(fmt.Errorf("backup entry %q has an invalid size", header.Name))
		}
		destination := filepath.Join(tempDir, header.Name)
		output, createErr := os.OpenFile(destination, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o600)
		if createErr != nil {
			return fail(createErr)
		}
		written, copyErr := io.CopyN(output, tarReader, header.Size)
		closeErr := output.Close()
		if copyErr != nil || written != header.Size {
			return fail(errors.New("backup entry is truncated"))
		}
		if closeErr != nil {
			return fail(closeErr)
		}
		found[header.Name] = destination
	}
	if found["database.dump"] == "" || found["uploads.tar.gz"] == "" {
		return fail(errors.New("backup must contain database.dump and uploads.tar.gz"))
	}
	return found["database.dump"], found["uploads.tar.gz"], cleanup, nil
}

func validateUploadArchive(path string) error {
	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()
	gzipReader, err := gzip.NewReader(file)
	if err != nil {
		return err
	}
	defer gzipReader.Close()
	tarReader := tar.NewReader(gzipReader)
	for {
		header, err := tarReader.Next()
		if errors.Is(err, io.EOF) {
			return nil
		}
		if err != nil {
			return err
		}
		name := strings.TrimPrefix(header.Name, "./")
		clean := filepath.ToSlash(filepath.Clean(name))
		if name == "" || name == "." {
			continue
		}
		if filepath.IsAbs(name) || clean == ".." || strings.HasPrefix(clean, "../") {
			return fmt.Errorf("entry escapes upload directory: %q", header.Name)
		}
		if header.Typeflag != tar.TypeReg && header.Typeflag != tar.TypeDir {
			return fmt.Errorf("entry uses unsupported type: %q", header.Name)
		}
	}
}
