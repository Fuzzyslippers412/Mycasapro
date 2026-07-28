package config

import (
	"os"
	"path/filepath"
	"strings"
)

type Config struct {
	Addr           string
	Env            string
	AppName        string
	PublicURL      string
	WebURL         string
	DatabaseURL    string
	StoreBackend   string
	AutoMigrate    bool
	MigrationsDir  string
	AllowedOrigins []string
	UploadDir      string
}

func Load() Config {
	databaseURL := strings.TrimSpace(os.Getenv("APP_DATABASE_URL"))
	storeBackend := strings.ToLower(envOr("APP_STORE_BACKEND", "auto"))
	if storeBackend == "auto" {
		if databaseURL != "" {
			storeBackend = "postgres"
		} else {
			storeBackend = "memory"
		}
	}

	return Config{
		Addr:           envOr("APP_ADDR", ":8081"),
		Env:            envOr("APP_ENV", "development"),
		AppName:        envOr("APP_NAME", "MyCasaPro"),
		PublicURL:      envOr("APP_PUBLIC_URL", "http://localhost:8081"),
		WebURL:         envOr("APP_WEB_URL", "http://localhost:3000"),
		DatabaseURL:    databaseURL,
		StoreBackend:   storeBackend,
		AutoMigrate:    envBoolDefault("APP_AUTO_MIGRATE", true),
		MigrationsDir:  resolveMigrationsDir(),
		AllowedOrigins: splitCSV(envOr("APP_ALLOWED_ORIGINS", "http://localhost:3000")),
		UploadDir:      envOr("APP_UPLOAD_DIR", filepath.Join("var", "uploads")),
	}
}

func envOr(key string, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}

func splitCSV(raw string) []string {
	if strings.TrimSpace(raw) == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, part := range parts {
		trimmed := strings.TrimSpace(part)
		if trimmed != "" {
			out = append(out, trimmed)
		}
	}
	return out
}

func envBoolDefault(key string, fallback bool) bool {
	value := strings.ToLower(strings.TrimSpace(os.Getenv(key)))
	if value == "" {
		return fallback
	}
	switch value {
	case "1", "true", "yes", "on":
		return true
	case "0", "false", "no", "off":
		return false
	default:
		return fallback
	}
}

func resolveMigrationsDir() string {
	if configured := strings.TrimSpace(os.Getenv("APP_MIGRATIONS_DIR")); configured != "" {
		return configured
	}

	candidates := []string{
		filepath.Join("app", "migrations"),
		"migrations",
	}
	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			return candidate
		}
	}
	return filepath.Join("app", "migrations")
}
