package notification

import (
	"context"
	"fmt"
	"log"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

const (
	batchSize        = 20
	maxAttempts      = 8
	deliveryLockTime = 2 * time.Minute
)

type Outbox interface {
	ClaimEmailNotifications(context.Context, time.Time, time.Time, int) ([]domain.EmailNotification, error)
	MarkEmailNotificationSent(context.Context, string, time.Time) error
	MarkEmailNotificationFailed(context.Context, string, string, time.Time, bool) error
}

type Worker struct {
	outbox   Outbox
	sender   Sender
	interval time.Duration
}

func NewWorker(outbox Outbox, sender Sender) *Worker {
	return &Worker{outbox: outbox, sender: sender, interval: 5 * time.Second}
}

func (w *Worker) Run(ctx context.Context) {
	if _, err := w.ProcessOnce(ctx, time.Now().UTC()); err != nil && ctx.Err() == nil {
		log.Printf("email delivery worker: %v", err)
	}
	ticker := time.NewTicker(w.interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case now := <-ticker.C:
			if _, err := w.ProcessOnce(ctx, now.UTC()); err != nil && ctx.Err() == nil {
				log.Printf("email delivery worker: %v", err)
			}
		}
	}
}

func (w *Worker) ProcessOnce(ctx context.Context, now time.Time) (int, error) {
	notifications, err := w.outbox.ClaimEmailNotifications(ctx, now, now.Add(deliveryLockTime), batchSize)
	if err != nil {
		return 0, err
	}
	delivered := 0
	for _, item := range notifications {
		message := Message{
			RecipientEmail: item.RecipientEmail, Subject: item.Subject, TextBody: item.TextBody, HTMLBody: item.HTMLBody,
		}
		deliveryCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
		err := w.sender.Send(deliveryCtx, message)
		cancel()
		if err == nil {
			if err := w.outbox.MarkEmailNotificationSent(ctx, item.ID, now); err != nil {
				return delivered, fmt.Errorf("mark email sent: %w", err)
			}
			delivered++
			continue
		}
		final := item.Attempts >= maxAttempts
		if err := w.outbox.MarkEmailNotificationFailed(ctx, item.ID, err.Error(), now.Add(retryDelay(item.Attempts)), final); err != nil {
			return delivered, fmt.Errorf("mark email failed: %w", err)
		}
	}
	if delivered > 0 {
		log.Printf("email delivery worker sent %d notification(s)", delivered)
	}
	return delivered, nil
}

func retryDelay(attempt int) time.Duration {
	if attempt < 1 {
		attempt = 1
	}
	delay := time.Minute << min(attempt-1, 6)
	if delay > time.Hour {
		return time.Hour
	}
	return delay
}
