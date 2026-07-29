package notification

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/tls"
	"encoding/hex"
	"errors"
	"fmt"
	"mime"
	"mime/multipart"
	"net"
	"net/mail"
	"net/smtp"
	"net/textproto"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/config"
)

type Sender interface {
	Send(context.Context, Message) error
}

type SMTPSender struct {
	host        string
	port        int
	username    string
	password    string
	tlsMode     string
	fromEmail   string
	fromName    string
	dialTimeout time.Duration
}

func NewSMTPSender(cfg config.Config) *SMTPSender {
	return &SMTPSender{
		host: cfg.SMTPHost, port: cfg.SMTPPort, username: cfg.SMTPUsername, password: cfg.SMTPPassword,
		tlsMode: cfg.SMTPTLSMode, fromEmail: cfg.MailFromEmail, fromName: cfg.MailFromName, dialTimeout: 15 * time.Second,
	}
}

func (s *SMTPSender) Send(ctx context.Context, message Message) error {
	payload, err := s.buildMessage(message)
	if err != nil {
		return err
	}
	address := net.JoinHostPort(s.host, fmt.Sprintf("%d", s.port))
	dialer := &net.Dialer{Timeout: s.dialTimeout}
	tlsConfig := &tls.Config{ServerName: s.host, MinVersion: tls.VersionTLS12}
	var connection net.Conn
	if s.tlsMode == "tls" {
		connection, err = (&tls.Dialer{NetDialer: dialer, Config: tlsConfig}).DialContext(ctx, "tcp", address)
	} else {
		connection, err = dialer.DialContext(ctx, "tcp", address)
	}
	if err != nil {
		return fmt.Errorf("connect to SMTP server: %w", err)
	}
	if deadline, ok := ctx.Deadline(); ok {
		_ = connection.SetDeadline(deadline)
	}
	client, err := smtp.NewClient(connection, s.host)
	if err != nil {
		_ = connection.Close()
		return err
	}
	defer client.Close()
	if s.tlsMode == "starttls" {
		if supported, _ := client.Extension("STARTTLS"); !supported {
			return errors.New("SMTP server does not support STARTTLS")
		}
		if err := client.StartTLS(tlsConfig); err != nil {
			return fmt.Errorf("start SMTP TLS: %w", err)
		}
	}
	if s.username != "" {
		if err := client.Auth(smtp.PlainAuth("", s.username, s.password, s.host)); err != nil {
			return fmt.Errorf("authenticate to SMTP server: %w", err)
		}
	}
	if err := client.Mail(s.fromEmail); err != nil {
		return fmt.Errorf("set SMTP sender: %w", err)
	}
	if err := client.Rcpt(message.RecipientEmail); err != nil {
		return fmt.Errorf("set SMTP recipient: %w", err)
	}
	writer, err := client.Data()
	if err != nil {
		return fmt.Errorf("start SMTP message: %w", err)
	}
	if _, err := writer.Write(payload); err != nil {
		_ = writer.Close()
		return fmt.Errorf("write SMTP message: %w", err)
	}
	if err := writer.Close(); err != nil {
		return fmt.Errorf("finish SMTP message: %w", err)
	}
	if err := client.Quit(); err != nil {
		return fmt.Errorf("finish SMTP session: %w", err)
	}
	return nil
}

func (s *SMTPSender) buildMessage(message Message) ([]byte, error) {
	to, err := mail.ParseAddress(strings.TrimSpace(message.RecipientEmail))
	if err != nil || !strings.EqualFold(to.Address, strings.TrimSpace(message.RecipientEmail)) {
		return nil, errors.New("invalid email recipient")
	}
	if strings.TrimSpace(message.Subject) == "" || strings.ContainsAny(message.Subject, "\r\n") {
		return nil, errors.New("invalid email subject")
	}
	from, err := mail.ParseAddress(strings.TrimSpace(s.fromEmail))
	if err != nil || !strings.EqualFold(from.Address, strings.TrimSpace(s.fromEmail)) || !strings.Contains(from.Address, "@") || strings.ContainsAny(s.fromName, "\r\n") {
		return nil, errors.New("invalid email sender")
	}
	randomID := make([]byte, 16)
	if _, err := rand.Read(randomID); err != nil {
		return nil, errors.New("generate email message ID")
	}
	fromDomain := from.Address[strings.LastIndexByte(from.Address, '@')+1:]
	var body bytes.Buffer
	multipartWriter := multipart.NewWriter(&body)
	fromHeader := (&mail.Address{Name: s.fromName, Address: from.Address}).String()
	toHeader := (&mail.Address{Address: to.Address}).String()
	fmt.Fprintf(&body, "From: %s\r\n", fromHeader)
	fmt.Fprintf(&body, "To: %s\r\n", toHeader)
	fmt.Fprintf(&body, "Subject: %s\r\n", mime.QEncoding.Encode("utf-8", message.Subject))
	fmt.Fprintf(&body, "Date: %s\r\n", time.Now().UTC().Format(time.RFC1123Z))
	fmt.Fprintf(&body, "Message-ID: <%s@%s>\r\n", hex.EncodeToString(randomID), fromDomain)
	fmt.Fprint(&body, "Auto-Submitted: auto-generated\r\n")
	fmt.Fprint(&body, "MIME-Version: 1.0\r\n")
	fmt.Fprintf(&body, "Content-Type: multipart/alternative; boundary=%q\r\n\r\n", multipartWriter.Boundary())
	textPart, err := multipartWriter.CreatePart(textproto.MIMEHeader{
		"Content-Type":              {"text/plain; charset=utf-8"},
		"Content-Transfer-Encoding": {"8bit"},
	})
	if err != nil {
		return nil, err
	}
	if _, err := textPart.Write([]byte(message.TextBody)); err != nil {
		return nil, err
	}
	htmlPart, err := multipartWriter.CreatePart(textproto.MIMEHeader{
		"Content-Type":              {"text/html; charset=utf-8"},
		"Content-Transfer-Encoding": {"8bit"},
	})
	if err != nil {
		return nil, err
	}
	if _, err := htmlPart.Write([]byte(message.HTMLBody)); err != nil {
		return nil, err
	}
	if err := multipartWriter.Close(); err != nil {
		return nil, err
	}
	return body.Bytes(), nil
}
