package store

import (
	"context"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func (s *MemoryStore) ClaimEmailNotifications(_ context.Context, now, lockedUntil time.Time, limit int) ([]domain.EmailNotification, error) {
	if limit < 1 || limit > 100 || !lockedUntil.After(now) {
		return nil, ErrInvalidInput
	}
	s.mu.Lock()
	defer s.mu.Unlock()

	out := make([]domain.EmailNotification, 0, limit)
	for index := range s.emailOutbox {
		if len(out) == limit {
			break
		}
		notification := &s.emailOutbox[index]
		claimable := notification.DeliveryStatus == domain.EmailDeliveryQueued && !notification.NextAttemptAt.After(now)
		if notification.DeliveryStatus == domain.EmailDeliveryProcessing && notification.LockedUntil != nil && !notification.LockedUntil.After(now) {
			claimable = true
		}
		if !claimable {
			continue
		}
		lock := lockedUntil.UTC()
		notification.DeliveryStatus = domain.EmailDeliveryProcessing
		notification.Attempts++
		notification.LockedUntil = &lock
		out = append(out, *notification)
	}
	return out, nil
}

func (s *MemoryStore) MarkEmailNotificationSent(_ context.Context, notificationID string, sentAt time.Time) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	for index := range s.emailOutbox {
		notification := &s.emailOutbox[index]
		if notification.ID != strings.TrimSpace(notificationID) {
			continue
		}
		if notification.DeliveryStatus != domain.EmailDeliveryProcessing {
			return ErrInvalidInput
		}
		when := sentAt.UTC()
		notification.DeliveryStatus = domain.EmailDeliverySent
		notification.SentAt = &when
		notification.LockedUntil = nil
		notification.LastError = ""
		notification.TextBody = ""
		notification.HTMLBody = ""
		s.updateInviteDeliveryStatusLocked(notification.AggregateID, domain.EmailDeliverySent)
		return nil
	}
	return ErrInvalidInput
}

func (s *MemoryStore) MarkEmailNotificationFailed(_ context.Context, notificationID, failure string, nextAttemptAt time.Time, final bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	for index := range s.emailOutbox {
		notification := &s.emailOutbox[index]
		if notification.ID != strings.TrimSpace(notificationID) {
			continue
		}
		if notification.DeliveryStatus != domain.EmailDeliveryProcessing {
			return ErrInvalidInput
		}
		notification.DeliveryStatus = domain.EmailDeliveryQueued
		if final {
			notification.DeliveryStatus = domain.EmailDeliveryFailed
			notification.TextBody = ""
			notification.HTMLBody = ""
			s.updateInviteDeliveryStatusLocked(notification.AggregateID, domain.EmailDeliveryFailed)
		}
		notification.NextAttemptAt = nextAttemptAt.UTC()
		notification.LockedUntil = nil
		notification.LastError = truncateFailure(failure)
		return nil
	}
	return ErrInvalidInput
}

func (s *MemoryStore) updateInviteDeliveryStatusLocked(inviteID string, status domain.EmailDeliveryStatus) {
	for index := range s.invites {
		if s.invites[index].Invite.ID == inviteID {
			s.invites[index].Invite.DeliveryStatus = status
			return
		}
	}
}

func truncateFailure(failure string) string {
	failure = strings.TrimSpace(failure)
	if len(failure) > 1000 {
		return failure[:1000]
	}
	return failure
}
