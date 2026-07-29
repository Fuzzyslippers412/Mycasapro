package notification

import (
	"bufio"
	"context"
	"fmt"
	"net"
	"strings"
	"testing"
	"time"
)

func TestSMTPSenderDeliversMessageOverProtocol(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer listener.Close()
	received := make(chan string, 1)
	serverErr := make(chan error, 1)
	go func() {
		serverErr <- serveOneSMTPMessage(listener, received)
	}()

	port := listener.Addr().(*net.TCPAddr).Port
	sender := &SMTPSender{
		host: "127.0.0.1", port: port, tlsMode: "none", fromEmail: "hello@mycasapro.test", fromName: "MyCasaPro", dialTimeout: time.Second,
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := sender.Send(ctx, Message{
		RecipientEmail: "contractor@example.com", Subject: "Repair invitation",
		TextBody: "Review this repair", HTMLBody: "<p>Review this repair</p>",
	}); err != nil {
		t.Fatal(err)
	}
	if err := <-serverErr; err != nil {
		t.Fatal(err)
	}
	payload := <-received
	if !strings.Contains(payload, "Subject: Repair invitation") || !strings.Contains(payload, "Review this repair") {
		t.Fatalf("SMTP server received an incomplete message: %s", payload)
	}
}

func serveOneSMTPMessage(listener net.Listener, received chan<- string) error {
	connection, err := listener.Accept()
	if err != nil {
		return err
	}
	defer connection.Close()
	reader := bufio.NewReader(connection)
	writer := bufio.NewWriter(connection)
	write := func(response string) error {
		if _, err := writer.WriteString(response + "\r\n"); err != nil {
			return err
		}
		return writer.Flush()
	}
	if err := write("220 localhost MyCasaPro test SMTP"); err != nil {
		return err
	}
	var message strings.Builder
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return err
		}
		command := strings.TrimSpace(line)
		switch {
		case strings.HasPrefix(command, "EHLO") || strings.HasPrefix(command, "HELO"):
			if _, err := writer.WriteString("250-localhost\r\n250 8BITMIME\r\n"); err != nil {
				return err
			}
			if err := writer.Flush(); err != nil {
				return err
			}
		case strings.HasPrefix(command, "MAIL FROM:") || strings.HasPrefix(command, "RCPT TO:"):
			if err := write("250 accepted"); err != nil {
				return err
			}
		case command == "DATA":
			if err := write("354 end with <CRLF>.<CRLF>"); err != nil {
				return err
			}
			for {
				bodyLine, err := reader.ReadString('\n')
				if err != nil {
					return err
				}
				if bodyLine == ".\r\n" {
					break
				}
				message.WriteString(bodyLine)
			}
			received <- message.String()
			if err := write("250 queued"); err != nil {
				return err
			}
		case command == "QUIT":
			return write("221 goodbye")
		default:
			return fmt.Errorf("unexpected SMTP command %q", command)
		}
	}
}
