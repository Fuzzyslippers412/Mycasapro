package config

import "testing"

func TestProductionConfigRequiresHTTPSAndPostgres(t *testing.T) {
	cfg := Config{
		Env: "production", StoreBackend: "postgres", DatabaseURL: "postgres://database/mycasapro",
		WebURL: "https://app.example.com", PublicURL: "https://app.example.com", AllowedOrigins: []string{"https://app.example.com"},
		MailMode: "disabled",
	}
	if err := cfg.Validate(); err != nil {
		t.Fatal(err)
	}
	cfg.WebURL = "http://app.example.com"
	if err := cfg.Validate(); err == nil {
		t.Fatal("production HTTP URL should be rejected")
	}
	cfg.WebURL = "https://app.example.com"
	cfg.AllowedOrigins = []string{"https://other.example.com"}
	if err := cfg.Validate(); err == nil {
		t.Fatal("production should require the web origin in APP_ALLOWED_ORIGINS")
	}
	cfg.AllowedOrigins = []string{"https://app.example.com/path"}
	if err := cfg.Validate(); err == nil {
		t.Fatal("CORS origins with paths should be rejected")
	}
}

func TestSMTPConfigRequiresCompleteSecureSettings(t *testing.T) {
	cfg := Config{
		Env: "production", StoreBackend: "postgres", DatabaseURL: "postgres://database/mycasapro",
		WebURL: "https://app.example.com", PublicURL: "https://app.example.com", AllowedOrigins: []string{"https://app.example.com"},
		MailMode: "smtp", MailFromEmail: "hello@example.com", MailFromName: "MyCasaPro",
		SMTPHost: "smtp.example.com", SMTPPort: 587, SMTPTLSMode: "starttls", SMTPUsername: "user", SMTPPassword: "secret",
	}
	if err := cfg.Validate(); err != nil {
		t.Fatal(err)
	}
	cfg.SMTPTLSMode = "none"
	if err := cfg.Validate(); err == nil {
		t.Fatal("unencrypted production SMTP should be rejected")
	}
}
