package notification

import (
	"context"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/store"
)

type recordingSender struct {
	messages []Message
	err      error
}

func (s *recordingSender) Send(_ context.Context, message Message) error {
	s.messages = append(s.messages, message)
	return s.err
}

func TestWorkerDeliversQueuedInvitation(t *testing.T) {
	repo, invite := queuedInvitation(t)
	sender := &recordingSender{}
	worker := NewWorker(repo, sender)
	delivered, err := worker.ProcessOnce(context.Background(), time.Now().UTC().Add(time.Second))
	if err != nil {
		t.Fatal(err)
	}
	if delivered != 1 || len(sender.messages) != 1 {
		t.Fatalf("delivery count mismatch: delivered=%d messages=%d", delivered, len(sender.messages))
	}
	invites, err := repo.ListWorkRequestInvites(context.Background(), "homeowner-mail", invite.WorkRequestID)
	if err != nil {
		t.Fatal(err)
	}
	if invites[0].DeliveryStatus != domain.EmailDeliverySent {
		t.Fatalf("delivery status = %s, want sent", invites[0].DeliveryStatus)
	}
}

func TestWorkerSchedulesRetryWithoutLeakingBody(t *testing.T) {
	repo, invite := queuedInvitation(t)
	sender := &recordingSender{err: errors.New("mail server unavailable")}
	worker := NewWorker(repo, sender)
	if _, err := worker.ProcessOnce(context.Background(), time.Now().UTC().Add(time.Second)); err != nil {
		t.Fatal(err)
	}
	invites, err := repo.ListWorkRequestInvites(context.Background(), "homeowner-mail", invite.WorkRequestID)
	if err != nil {
		t.Fatal(err)
	}
	if invites[0].DeliveryStatus != domain.EmailDeliveryQueued {
		t.Fatalf("delivery status = %s, want queued", invites[0].DeliveryStatus)
	}
}

func TestWorkerMarksInvitationFailedAfterRetryLimit(t *testing.T) {
	repo, invite := queuedInvitation(t)
	sender := &recordingSender{err: errors.New("mail server unavailable")}
	worker := NewWorker(repo, sender)
	now := time.Now().UTC()
	for attempt := 0; attempt < maxAttempts; attempt++ {
		now = now.Add(2 * time.Hour)
		if _, err := worker.ProcessOnce(context.Background(), now); err != nil {
			t.Fatal(err)
		}
	}
	invites, err := repo.ListWorkRequestInvites(context.Background(), "homeowner-mail", invite.WorkRequestID)
	if err != nil {
		t.Fatal(err)
	}
	if invites[0].DeliveryStatus != domain.EmailDeliveryFailed {
		t.Fatalf("delivery status = %s, want failed", invites[0].DeliveryStatus)
	}
	claimed, err := repo.ClaimEmailNotifications(context.Background(), now.Add(24*time.Hour), now.Add(25*time.Hour), 10)
	if err != nil {
		t.Fatal(err)
	}
	if len(claimed) != 0 {
		t.Fatalf("terminal notification was claimed again: %+v", claimed)
	}
}

func TestRevokedInvitationIsNotDelivered(t *testing.T) {
	repo, invite := queuedInvitation(t)
	if _, err := repo.RevokeWorkRequestInvite(context.Background(), "homeowner-mail", invite.WorkRequestID, invite.ID, time.Now().UTC()); err != nil {
		t.Fatal(err)
	}
	sender := &recordingSender{}
	delivered, err := NewWorker(repo, sender).ProcessOnce(context.Background(), time.Now().UTC().Add(time.Second))
	if err != nil {
		t.Fatal(err)
	}
	if delivered != 0 || len(sender.messages) != 0 {
		t.Fatalf("revoked invitation was delivered: delivered=%d messages=%d", delivered, len(sender.messages))
	}
	invites, err := repo.ListWorkRequestInvites(context.Background(), "homeowner-mail", invite.WorkRequestID)
	if err != nil {
		t.Fatal(err)
	}
	if invites[0].DeliveryStatus != domain.EmailDeliveryCanceled {
		t.Fatalf("delivery status = %s, want canceled", invites[0].DeliveryStatus)
	}
}

func TestInvitationMessageEscapesRecipientName(t *testing.T) {
	message := WorkRequestInvitation("MyCasaPro", `<script>alert(1)</script>`, "https://example.com/invite/token", time.Now().Add(time.Hour))
	if strings.Contains(message.HTMLBody, "<script>") || !strings.Contains(message.TextBody, "https://example.com/invite/token") {
		t.Fatal("invitation message was not safely rendered")
	}
}

func TestSMTPMessageHasSafeMultipartHeaders(t *testing.T) {
	sender := &SMTPSender{fromEmail: "hello@mycasapro.test", fromName: "MyCasaPro"}
	payload, err := sender.buildMessage(Message{
		RecipientEmail: "contractor@example.com", Subject: "Private repair invitation",
		TextBody: "Review the repair", HTMLBody: "<p>Review the repair</p>",
	})
	if err != nil {
		t.Fatal(err)
	}
	raw := string(payload)
	for _, expected := range []string{`From: "MyCasaPro" <hello@mycasapro.test>`, "To: <contractor@example.com>", "Message-ID:", "Auto-Submitted: auto-generated", "multipart/alternative", "text/plain", "text/html"} {
		if !strings.Contains(raw, expected) {
			t.Fatalf("SMTP payload is missing %q: %s", expected, raw)
		}
	}
	if _, err := sender.buildMessage(Message{RecipientEmail: "contractor@example.com", Subject: "Hello\r\nBcc: attacker@example.com"}); err == nil {
		t.Fatal("header injection subject should be rejected")
	}
}

func queuedInvitation(t *testing.T) (*store.MemoryStore, domain.WorkRequestInvite) {
	t.Helper()
	repo := store.NewMemoryStore()
	ctx := context.Background()
	property, err := repo.CreateProperty(ctx, store.CreatePropertyInput{
		HomeownerUserID: "homeowner-mail", Label: "Home", AddressLine1: "1 Main St", City: "Oakland", Region: "CA", PostalCode: "94607",
	})
	if err != nil {
		t.Fatal(err)
	}
	request, err := repo.CreateWorkRequest(ctx, store.CreateWorkRequestInput{
		HomeownerUserID: "homeowner-mail", PropertyID: property.ID, Title: "Repair", Category: "general",
		Area: "entry", Urgency: "medium", Description: "Repair needed",
	})
	if err != nil {
		t.Fatal(err)
	}
	invite, err := repo.CreateWorkRequestInvite(ctx, store.CreateWorkRequestInviteInput{
		HomeownerUserID: "homeowner-mail", WorkRequestID: request.ID, TokenHash: strings.Repeat("a", 64),
		RecipientName: "Jordan", RecipientEmail: "jordan@example.com", EmailSubject: "Invitation",
		EmailTextBody: "Review this repair", EmailHTMLBody: "<p>Review this repair</p>", ExpiresAt: time.Now().UTC().Add(time.Hour),
	})
	if err != nil {
		t.Fatal(err)
	}
	return repo, invite
}
