package store

import (
	"context"
	"database/sql"
	"errors"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func (s *PostgresStore) CreateWorkRequestInvite(ctx context.Context, input CreateWorkRequestInviteInput) (domain.WorkRequestInvite, error) {
	homeownerID := strings.TrimSpace(input.HomeownerUserID)
	workRequestID := strings.TrimSpace(input.WorkRequestID)
	tokenHash := strings.TrimSpace(input.TokenHash)
	createdAt := time.Now().UTC()
	if homeownerID == "" || workRequestID == "" || len(tokenHash) != 64 || !input.ExpiresAt.After(createdAt) {
		return domain.WorkRequestInvite{}, ErrInvalidInput
	}
	invite := domain.WorkRequestInvite{
		ID: newID("inv"), WorkRequestID: workRequestID, HomeownerUserID: homeownerID,
		ExpiresAt: input.ExpiresAt.UTC(), CreatedAt: createdAt,
	}
	result, err := s.db.ExecContext(ctx, `
		insert into work_request_invites (id, work_request_id, homeowner_user_id, token_hash, expires_at, created_at)
		select $1, wr.id, wr.requested_by_user_id, $4, $5, $6
		from work_requests wr
		where wr.id = $2 and wr.requested_by_user_id = $3
	`, invite.ID, workRequestID, homeownerID, tokenHash, invite.ExpiresAt, invite.CreatedAt)
	if err != nil {
		return domain.WorkRequestInvite{}, err
	}
	rows, err := result.RowsAffected()
	if err != nil {
		return domain.WorkRequestInvite{}, err
	}
	if rows != 1 {
		return domain.WorkRequestInvite{}, ErrWorkRequestNotFound
	}
	return invite, nil
}

func (s *PostgresStore) ListWorkRequestInvites(ctx context.Context, homeownerUserID string, workRequestID string) ([]domain.WorkRequestInvite, error) {
	var owned bool
	if err := s.db.QueryRowContext(ctx, `select exists(select 1 from work_requests where id=$1 and requested_by_user_id=$2)`,
		strings.TrimSpace(workRequestID), strings.TrimSpace(homeownerUserID)).Scan(&owned); err != nil {
		return nil, err
	}
	if !owned {
		return nil, ErrWorkRequestNotFound
	}
	rows, err := s.db.QueryContext(ctx, `
		select id, work_request_id, homeowner_user_id, expires_at, revoked_at, created_at
		from work_request_invites where work_request_id=$1 order by created_at desc
	`, strings.TrimSpace(workRequestID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]domain.WorkRequestInvite, 0)
	for rows.Next() {
		invite, err := scanWorkRequestInvite(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, invite)
	}
	return out, rows.Err()
}

func (s *PostgresStore) RevokeWorkRequestInvite(ctx context.Context, homeownerUserID string, workRequestID string, inviteID string, now time.Time) (domain.WorkRequestInvite, error) {
	row := s.db.QueryRowContext(ctx, `
		update work_request_invites i set revoked_at=$4
		from work_requests wr
		where i.id=$1 and i.work_request_id=$2 and wr.id=i.work_request_id and wr.requested_by_user_id=$3
		returning i.id, i.work_request_id, i.homeowner_user_id, i.expires_at, i.revoked_at, i.created_at
	`, strings.TrimSpace(inviteID), strings.TrimSpace(workRequestID), strings.TrimSpace(homeownerUserID), now.UTC())
	invite, err := scanWorkRequestInvite(row)
	if errors.Is(err, sql.ErrNoRows) {
		return domain.WorkRequestInvite{}, ErrInviteNotFound
	}
	return invite, err
}

func (s *PostgresStore) GetInviteTask(ctx context.Context, tokenHash string, now time.Time) (domain.InviteTask, error) {
	invite, err := getInviteByTokenHashUsing(ctx, s.db, strings.TrimSpace(tokenHash), now)
	if err != nil {
		return domain.InviteTask{}, err
	}
	row := s.db.QueryRowContext(ctx, `
		select wr.id, wr.property_id, wr.requested_by_user_id, wr.title, wr.category, wr.area, wr.urgency,
		       wr.description, wr.preferred_timing, wr.status, wr.created_at,
		       p.label, p.city, p.region, p.country_code
		from work_requests wr join properties p on p.id=wr.property_id where wr.id=$1
	`, invite.WorkRequestID)
	var request domain.WorkRequest
	var property domain.InviteProperty
	var status string
	if err := row.Scan(&request.ID, &request.PropertyID, &request.RequestedByUserID, &request.Title, &request.Category,
		&request.Area, &request.Urgency, &request.Description, &request.PreferredTiming, &status, &request.CreatedAt,
		&property.Label, &property.City, &property.Region, &property.CountryCode); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.InviteTask{}, ErrInviteNotFound
		}
		return domain.InviteTask{}, err
	}
	request.Status = domain.WorkRequestStatus(status)
	request.Attachments, err = s.listWorkRequestAttachmentsByID(ctx, request.ID)
	if err != nil {
		return domain.InviteTask{}, err
	}
	request.GuestEstimateCount, err = s.guestEstimateCount(ctx, request.ID)
	if err != nil {
		return domain.InviteTask{}, err
	}
	return domain.InviteTask{Invite: invite, WorkRequest: request, Property: property}, nil
}

func (s *PostgresStore) GetWorkRequestAttachmentForInvite(ctx context.Context, tokenHash string, attachmentID string, now time.Time) (domain.Attachment, error) {
	invite, err := getInviteByTokenHashUsing(ctx, s.db, strings.TrimSpace(tokenHash), now)
	if err != nil {
		return domain.Attachment{}, err
	}
	attachment, err := scanAttachment(s.db.QueryRowContext(ctx, `
		select id, work_request_id, project_id, uploaded_by_user_id, file_name, content_type, size_bytes, sha256, storage_key, created_at
		from attachments where id=$1 and work_request_id=$2
	`, strings.TrimSpace(attachmentID), invite.WorkRequestID))
	if errors.Is(err, sql.ErrNoRows) || errors.Is(err, ErrAttachmentNotFound) {
		return domain.Attachment{}, ErrAttachmentNotFound
	}
	return attachment, err
}

func (s *PostgresStore) CreateGuestEstimate(ctx context.Context, input CreateGuestEstimateInput) (domain.GuestEstimate, error) {
	input, total, ok := normalizeGuestEstimateInput(input)
	if !ok {
		return domain.GuestEstimate{}, ErrInvalidInput
	}
	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return domain.GuestEstimate{}, err
	}
	defer rollback(tx)
	invite, err := getInviteByTokenHashUsing(ctx, tx, strings.TrimSpace(input.TokenHash), input.Now)
	if err != nil {
		return domain.GuestEstimate{}, err
	}
	var exists bool
	if err := tx.QueryRowContext(ctx, `select exists(select 1 from guest_estimates where invite_id=$1 and lower(email)=lower($2))`, invite.ID, input.Email).Scan(&exists); err != nil {
		return domain.GuestEstimate{}, err
	}
	if exists {
		return domain.GuestEstimate{}, ErrEstimateUnavailable
	}
	estimate := domain.GuestEstimate{
		ID: newID("gest"), InviteID: invite.ID, WorkRequestID: invite.WorkRequestID,
		ContractorName: input.ContractorName, BusinessName: input.BusinessName, Email: input.Email,
		Summary: input.Summary, Notes: input.Notes, AvailableTiming: input.AvailableTiming, TotalAmountCents: total,
		LineItems: make([]domain.GuestEstimateLineItem, 0, len(input.LineItems)), CreatedAt: input.Now.UTC(),
	}
	for position, item := range input.LineItems {
		estimate.LineItems = append(estimate.LineItems, domain.GuestEstimateLineItem{
			ID: newID("gli"), GuestEstimateID: estimate.ID, Label: item.Label, AmountCents: item.AmountCents, Position: position,
		})
	}
	_, err = tx.ExecContext(ctx, `
		insert into guest_estimates (id, invite_id, work_request_id, contractor_name, business_name, email, summary, notes, available_timing, total_amount_cents, created_at)
		values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
	`, estimate.ID, estimate.InviteID, estimate.WorkRequestID, estimate.ContractorName, estimate.BusinessName,
		estimate.Email, estimate.Summary, estimate.Notes, estimate.AvailableTiming, estimate.TotalAmountCents, estimate.CreatedAt)
	if err != nil {
		return domain.GuestEstimate{}, err
	}
	for _, item := range estimate.LineItems {
		if _, err := tx.ExecContext(ctx, `insert into guest_estimate_line_items (id, guest_estimate_id, label, amount_cents, position) values ($1,$2,$3,$4,$5)`,
			item.ID, item.GuestEstimateID, item.Label, item.AmountCents, item.Position); err != nil {
			return domain.GuestEstimate{}, err
		}
	}
	if _, err := tx.ExecContext(ctx, `
		update work_requests set status=$2 where id=$1 and status in ($3,$4)
	`, estimate.WorkRequestID, string(domain.WorkRequestStatusQuoted), string(domain.WorkRequestStatusNew), string(domain.WorkRequestStatusReviewing)); err != nil {
		return domain.GuestEstimate{}, err
	}
	if err := tx.Commit(); err != nil {
		return domain.GuestEstimate{}, err
	}
	return estimate, nil
}

func (s *PostgresStore) ListGuestEstimates(ctx context.Context, homeownerUserID string, workRequestID string) ([]domain.GuestEstimate, error) {
	var owned bool
	if err := s.db.QueryRowContext(ctx, `select exists(select 1 from work_requests where id=$1 and requested_by_user_id=$2)`,
		strings.TrimSpace(workRequestID), strings.TrimSpace(homeownerUserID)).Scan(&owned); err != nil {
		return nil, err
	}
	if !owned {
		return nil, ErrWorkRequestNotFound
	}
	rows, err := s.db.QueryContext(ctx, `
		select id, invite_id, work_request_id, contractor_name, business_name, email, summary, notes, available_timing, total_amount_cents, created_at
		from guest_estimates where work_request_id=$1 order by created_at desc
	`, strings.TrimSpace(workRequestID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]domain.GuestEstimate, 0)
	for rows.Next() {
		estimate, err := scanGuestEstimate(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, estimate)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	for index := range out {
		items, err := s.listGuestEstimateLineItems(ctx, out[index].ID)
		if err != nil {
			return nil, err
		}
		out[index].LineItems = items
	}
	return out, nil
}

func getInviteByTokenHashUsing(ctx context.Context, db sqlQuerier, tokenHash string, now time.Time) (domain.WorkRequestInvite, error) {
	var revokedAt sql.NullTime
	var invite domain.WorkRequestInvite
	err := db.QueryRowContext(ctx, `
		select id, work_request_id, homeowner_user_id, expires_at, revoked_at, created_at
		from work_request_invites where token_hash=$1
	`, tokenHash).Scan(&invite.ID, &invite.WorkRequestID, &invite.HomeownerUserID, &invite.ExpiresAt, &revokedAt, &invite.CreatedAt)
	if errors.Is(err, sql.ErrNoRows) {
		return domain.WorkRequestInvite{}, ErrInviteNotFound
	}
	if err != nil {
		return domain.WorkRequestInvite{}, err
	}
	if revokedAt.Valid {
		invite.RevokedAt = &revokedAt.Time
		return domain.WorkRequestInvite{}, ErrInviteRevoked
	}
	if !invite.ExpiresAt.After(now.UTC()) {
		return domain.WorkRequestInvite{}, ErrInviteExpired
	}
	return invite, nil
}

func scanWorkRequestInvite(scanner interface{ Scan(...any) error }) (domain.WorkRequestInvite, error) {
	var invite domain.WorkRequestInvite
	var revokedAt sql.NullTime
	err := scanner.Scan(&invite.ID, &invite.WorkRequestID, &invite.HomeownerUserID, &invite.ExpiresAt, &revokedAt, &invite.CreatedAt)
	if revokedAt.Valid {
		invite.RevokedAt = &revokedAt.Time
	}
	return invite, err
}

func scanGuestEstimate(scanner interface{ Scan(...any) error }) (domain.GuestEstimate, error) {
	var estimate domain.GuestEstimate
	err := scanner.Scan(&estimate.ID, &estimate.InviteID, &estimate.WorkRequestID, &estimate.ContractorName,
		&estimate.BusinessName, &estimate.Email, &estimate.Summary, &estimate.Notes, &estimate.AvailableTiming,
		&estimate.TotalAmountCents, &estimate.CreatedAt)
	estimate.LineItems = []domain.GuestEstimateLineItem{}
	return estimate, err
}

func (s *PostgresStore) listGuestEstimateLineItems(ctx context.Context, estimateID string) ([]domain.GuestEstimateLineItem, error) {
	rows, err := s.db.QueryContext(ctx, `select id, guest_estimate_id, label, amount_cents, position from guest_estimate_line_items where guest_estimate_id=$1 order by position`, estimateID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]domain.GuestEstimateLineItem, 0)
	for rows.Next() {
		var item domain.GuestEstimateLineItem
		if err := rows.Scan(&item.ID, &item.GuestEstimateID, &item.Label, &item.AmountCents, &item.Position); err != nil {
			return nil, err
		}
		out = append(out, item)
	}
	return out, rows.Err()
}

func (s *PostgresStore) guestEstimateCount(ctx context.Context, workRequestID string) (int, error) {
	var count int
	err := s.db.QueryRowContext(ctx, `select count(*) from guest_estimates where work_request_id=$1`, workRequestID).Scan(&count)
	return count, err
}
