package config

import (
	"errors"
	"fmt"
	"net/mail"
	"net/url"
	"strings"
)

func (c Config) Validate() error {
	if c.MailMode != "disabled" && c.MailMode != "smtp" {
		return fmt.Errorf("APP_MAIL_MODE must be disabled or smtp")
	}
	if c.MailMode == "smtp" {
		if err := c.validateSMTP(); err != nil {
			return err
		}
	}
	if c.Env != "production" {
		return nil
	}
	if c.StoreBackend != "postgres" || strings.TrimSpace(c.DatabaseURL) == "" {
		return errors.New("production requires PostgreSQL through APP_DATABASE_URL")
	}
	if err := requireHTTPSURL("APP_WEB_URL", c.WebURL); err != nil {
		return err
	}
	if err := requireHTTPSURL("APP_PUBLIC_URL", c.PublicURL); err != nil {
		return err
	}
	if len(c.AllowedOrigins) == 0 {
		return errors.New("production requires at least one APP_ALLOWED_ORIGINS value")
	}
	webOrigin, err := canonicalOrigin(c.WebURL)
	if err != nil {
		return err
	}
	webOriginAllowed := false
	for _, origin := range c.AllowedOrigins {
		parsedOrigin, err := canonicalOrigin(origin)
		if err != nil || parsedOrigin != strings.TrimSpace(origin) {
			return errors.New("APP_ALLOWED_ORIGINS values must be absolute HTTPS origins without paths")
		}
		if parsedOrigin == webOrigin {
			webOriginAllowed = true
		}
		if err := requireHTTPSURL("APP_ALLOWED_ORIGINS", origin); err != nil {
			return err
		}
	}
	if !webOriginAllowed {
		return errors.New("APP_ALLOWED_ORIGINS must include the APP_WEB_URL origin")
	}
	return nil
}

func (c Config) validateSMTP() error {
	from, err := mail.ParseAddress(strings.TrimSpace(c.MailFromEmail))
	if err != nil || !strings.EqualFold(from.Address, strings.TrimSpace(c.MailFromEmail)) || !strings.Contains(from.Address, "@") {
		return errors.New("APP_MAIL_FROM_EMAIL must be a valid mailbox")
	}
	if strings.TrimSpace(c.MailFromName) == "" || strings.ContainsAny(c.MailFromName, "\r\n") {
		return errors.New("APP_MAIL_FROM_NAME is invalid")
	}
	if strings.TrimSpace(c.SMTPHost) == "" || strings.ContainsAny(c.SMTPHost, "\r\n") || c.SMTPPort < 1 || c.SMTPPort > 65535 {
		return errors.New("APP_SMTP_HOST and APP_SMTP_PORT must identify a valid SMTP server")
	}
	if c.SMTPTLSMode != "starttls" && c.SMTPTLSMode != "tls" && c.SMTPTLSMode != "none" {
		return errors.New("APP_SMTP_TLS_MODE must be starttls, tls, or none")
	}
	if c.Env == "production" && c.SMTPTLSMode == "none" {
		return errors.New("production SMTP delivery requires TLS")
	}
	if (c.SMTPUsername == "") != (c.SMTPPassword == "") {
		return errors.New("APP_SMTP_USERNAME and APP_SMTP_PASSWORD must be configured together")
	}
	return nil
}

func requireHTTPSURL(name, raw string) error {
	parsed, err := url.Parse(strings.TrimSpace(raw))
	if err != nil || parsed.Scheme != "https" || parsed.Host == "" || parsed.User != nil {
		return fmt.Errorf("%s must be an absolute HTTPS URL", name)
	}
	return nil
}

func canonicalOrigin(raw string) (string, error) {
	parsed, err := url.Parse(strings.TrimSpace(raw))
	if err != nil || parsed.Scheme != "https" || parsed.Host == "" || parsed.User != nil {
		return "", errors.New("invalid HTTPS origin")
	}
	return parsed.Scheme + "://" + parsed.Host, nil
}
