package command

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/Fuzzyslippers412/Mycasapro/cli/internal/assets"
)

func TestSaveAndLoadConfig(t *testing.T) {
	home := t.TempDir()
	t.Setenv("MYCASAPRO_HOME", home)
	cfg := config{Home: home, Port: 4321, Version: "v1.2.3", DBPassword: "0123456789abcdefghijklmnopqrstuvwxyzABCDE"}
	if err := saveConfig(cfg); err != nil {
		t.Fatal(err)
	}
	loaded, err := loadConfig()
	if err != nil {
		t.Fatal(err)
	}
	if loaded.Port != cfg.Port || loaded.Version != cfg.Version || loaded.DBPassword != cfg.DBPassword {
		t.Fatalf("loaded config does not match: %#v", loaded)
	}
	info, err := os.Stat(filepath.Join(home, ".env"))
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("env permissions = %o, want 600", info.Mode().Perm())
	}
}

func TestEmbeddedComposeIsPrivateAndPersistent(t *testing.T) {
	body := string(assets.ComposeYAML)
	for _, expected := range []string{
		`127.0.0.1:${MYCASAPRO_PORT:-3210}:3000`,
		"postgres-data:/var/lib/postgresql/data",
		"uploads:/data/uploads",
		"ghcr.io/fuzzyslippers412/mycasapro-api",
	} {
		if !strings.Contains(body, expected) {
			t.Fatalf("compose file is missing %q", expected)
		}
	}
	if strings.Contains(body, `"5432:5432"`) || strings.Contains(body, `"8081:8081"`) {
		t.Fatal("private services must not publish host ports")
	}
}

func TestSafeManagedHome(t *testing.T) {
	home := t.TempDir()
	if err := safeManagedHome(home); err == nil {
		t.Fatal("unmarked directory should not be accepted")
	}
	if err := os.WriteFile(filepath.Join(home, markerName), []byte("managed"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := safeManagedHome(home); err != nil {
		t.Fatal(err)
	}
}
