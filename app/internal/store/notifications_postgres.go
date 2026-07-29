package store

import (
	"context"
	"database/sql"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func (s *PostgresStore) ClaimEmailNotifications(ctx context.Context, now, lockedUntil time.Time, limit int) ([]domain.EmailNotification, error) {
	if limit < 1 || limit > 100 || !lockedUntil.After(now) {
		return nil, ErrInvalidInput
	}
	rows, err := s.db.QueryContext(ctx, `
		with candidates as (
			select id from email_outbox
			where attempts < 8 and (
				(status='queued' and next_attempt_at <= $1)
				or (status='processing' and locked_until <= $1)
			)
			order by next_attempt_at, created_at
			for update skip locked
			limit $3
		)
		update email_outbox e
		set status='processing', attempts=e.attempts+1, locked_until=$2
		from candidates c where e.id=c.id
		returning e.id, e.kind, e.aggregate_id, e.recipient_email, e.subject, e.text_body, e.html_body,
		          e.status, e.attempts, e.next_attempt_at, e.locked_until, e.last_error, e.created_at, e.sent_at
	`, now.UTC(), lockedUntil.UTC(), limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]domain.EmailNotification, 0, limit)
	for rows.Next() {
		notification, err := scanEmailNotification(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, notification)
	}
	return out, rows.Err()
}

func (s *PostgresStore) MarkEmailNotificationSent(ctx context.Context, notificationID string, sentAt time.Time) error {
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return err
	}
	defer rollback(tx)
	var kind, aggregateID string
	err = tx.QueryRowContext(ctx, `
		update email_outbox
		set status='sent', sent_at=$2, locked_until=null, last_error='', text_body='', html_body=''
		where id=$1 and status='processing'
		returning kind, aggregate_id
	`, notificationID, sentAt.UTC()).Scan(&kind, &aggregateID)
	if err != nil {
		return err
	}
	if kind == "work_request_invite" {
		if _, err := tx.ExecContext(ctx, `update work_request_invites set delivery_status='sent' where id=$1`, aggregateID); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func (s *PostgresStore) MarkEmailNotificationFailed(ctx context.Context, notificationID, failure string, nextAttemptAt time.Time, final bool) error {
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return err
	}
	defer rollback(tx)
	status := domain.EmailDeliveryQueued
	clearBody := false
	if final {
		status = domain.EmailDeliveryFailed
		clearBody = true
	}
	var kind, aggregateID string
	err = tx.QueryRowContext(ctx, `
		update email_outbox
		set status=$2, next_attempt_at=$3, locked_until=null, last_error=$4,
		    text_body=case when $5 then '' else text_body end,
		    html_body=case when $5 then '' else html_body end
		where id=$1 and status='processing'
		returning kind, aggregate_id
	`, notificationID, string(status), nextAttemptAt.UTC(), truncateFailure(failure), clearBody).Scan(&kind, &aggregateID)
	if err != nil {
		return err
	}
	if final && kind == "work_request_invite" {
		if _, err := tx.ExecContext(ctx, `update work_request_invites set delivery_status='failed' where id=$1`, aggregateID); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func scanEmailNotification(scanner interface{ Scan(...any) error }) (domain.EmailNotification, error) {
	var notification domain.EmailNotification
	var lockedUntil, sentAt sql.NullTime
	err := scanner.Scan(
		&notification.ID, &notification.Kind, &notification.AggregateID, &notification.RecipientEmail,
		&notification.Subject, &notification.TextBody, &notification.HTMLBody, &notification.DeliveryStatus,
		&notification.Attempts, &notification.NextAttemptAt, &lockedUntil, &notification.LastError,
		&notification.CreatedAt, &sentAt,
	)
	if lockedUntil.Valid {
		notification.LockedUntil = &lockedUntil.Time
	}
	if sentAt.Valid {
		notification.SentAt = &sentAt.Time
	}
	return notification, err
}
