package command

import (
	"bufio"
	"crypto/rand"
	"encoding/base64"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"github.com/Fuzzyslippers412/Mycasapro/cli/internal/assets"
)

var (
	versionPattern  = regexp.MustCompile(`^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$`)
	passwordPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{32,128}$`)
)

const (
	defaultPort    = 3210
	defaultVersion = "latest"
	markerName     = ".mycasapro-managed"
)

type config struct {
	Home       string
	Port       int
	Version    string
	DBPassword string
}

func stateHome() (string, error) {
	if configured := strings.TrimSpace(os.Getenv("MYCASAPRO_HOME")); configured != "" {
		if strings.HasPrefix(configured, "~"+string(os.PathSeparator)) {
			home, err := os.UserHomeDir()
			if err != nil {
				return "", err
			}
			configured = filepath.Join(home, strings.TrimPrefix(configured, "~"+string(os.PathSeparator)))
		}
		return filepath.Abs(configured)
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("find home directory: %w", err)
	}
	return filepath.Join(home, ".mycasapro"), nil
}

func loadConfig() (config, error) {
	home, err := stateHome()
	if err != nil {
		return config{}, err
	}
	values, err := readEnv(filepath.Join(home, ".env"))
	if err != nil {
		return config{}, err
	}
	port, err := strconv.Atoi(values["MYCASAPRO_PORT"])
	if err != nil || port < 1 || port > 65535 {
		return config{}, errors.New("local configuration has an invalid MYCASAPRO_PORT")
	}
	cfg := config{
		Home:       home,
		Port:       port,
		Version:    strings.TrimSpace(values["MYCASAPRO_VERSION"]),
		DBPassword: strings.TrimSpace(values["MYCASAPRO_DB_PASSWORD"]),
	}
	if cfg.Version == "" || cfg.DBPassword == "" {
		return config{}, errors.New("local configuration is incomplete; run mycasapro setup")
	}
	if !versionPattern.MatchString(cfg.Version) || !passwordPattern.MatchString(cfg.DBPassword) {
		return config{}, errors.New("local configuration contains unsafe values; run mycasapro setup")
	}
	return cfg, nil
}

func configExists() bool {
	home, err := stateHome()
	if err != nil {
		return false
	}
	_, err = os.Stat(filepath.Join(home, ".env"))
	return err == nil
}

func readEnv(path string) (map[string]string, error) {
	file, err := os.Open(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, errors.New("MyCasaPro is not set up; run mycasapro setup")
		}
		return nil, fmt.Errorf("read local configuration: %w", err)
	}
	defer file.Close()

	values := make(map[string]string)
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		key, value, ok := strings.Cut(line, "=")
		if !ok {
			continue
		}
		values[strings.TrimSpace(key)] = strings.TrimSpace(value)
	}
	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("read local configuration: %w", err)
	}
	return values, nil
}

func newConfig(port int, version string) (config, error) {
	home, err := stateHome()
	if err != nil {
		return config{}, err
	}
	secret := make([]byte, 32)
	if _, err := rand.Read(secret); err != nil {
		return config{}, fmt.Errorf("generate database credential: %w", err)
	}
	return config{
		Home:       home,
		Port:       port,
		Version:    version,
		DBPassword: base64.RawURLEncoding.EncodeToString(secret),
	}, nil
}

func saveConfig(cfg config) error {
	if cfg.Port < 1 || cfg.Port > 65535 {
		return errors.New("port must be between 1 and 65535")
	}
	if !versionPattern.MatchString(cfg.Version) {
		return errors.New("version must be a valid container image tag")
	}
	if !passwordPattern.MatchString(cfg.DBPassword) {
		return errors.New("database credential is invalid")
	}
	if err := os.MkdirAll(cfg.Home, 0o700); err != nil {
		return fmt.Errorf("create local state directory: %w", err)
	}
	if err := os.Chmod(cfg.Home, 0o700); err != nil {
		return fmt.Errorf("secure local state directory: %w", err)
	}
	envBody := fmt.Sprintf(
		"MYCASAPRO_PORT=%d\nMYCASAPRO_VERSION=%s\nMYCASAPRO_DB_PASSWORD=%s\n",
		cfg.Port,
		cfg.Version,
		cfg.DBPassword,
	)
	if err := writeAtomic(filepath.Join(cfg.Home, ".env"), []byte(envBody), 0o600); err != nil {
		return err
	}
	if err := writeAtomic(filepath.Join(cfg.Home, "compose.yaml"), assets.ComposeYAML, 0o600); err != nil {
		return err
	}
	return writeAtomic(filepath.Join(cfg.Home, markerName), []byte("managed by the MyCasaPro CLI\n"), 0o600)
}

func writeAtomic(path string, body []byte, mode os.FileMode) error {
	temp, err := os.CreateTemp(filepath.Dir(path), ".mycasapro-*")
	if err != nil {
		return fmt.Errorf("create temporary configuration: %w", err)
	}
	tempPath := temp.Name()
	defer os.Remove(tempPath)
	if err := temp.Chmod(mode); err != nil {
		_ = temp.Close()
		return err
	}
	if _, err := temp.Write(body); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Sync(); err != nil {
		_ = temp.Close()
		return err
	}
	if err := temp.Close(); err != nil {
		return err
	}
	if err := os.Rename(tempPath, path); err != nil {
		return fmt.Errorf("replace %s: %w", filepath.Base(path), err)
	}
	return nil
}

func (cfg config) URL() string {
	return fmt.Sprintf("http://127.0.0.1:%d", cfg.Port)
}
