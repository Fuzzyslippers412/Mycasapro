package store

import (
	"context"
	"database/sql"
	"errors"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func (s *PostgresStore) CreateWorkRequestAttachment(ctx context.Context, input CreateWorkRequestAttachmentInput) (domain.Attachment, error) {
	if strings.TrimSpace(input.HomeownerUserID) == "" || strings.TrimSpace(input.WorkRequestID) == "" ||
		strings.TrimSpace(input.StorageKey) == "" || strings.TrimSpace(input.FileName) == "" ||
		strings.TrimSpace(input.ContentType) == "" || input.SizeBytes <= 0 || strings.TrimSpace(input.SHA256) == "" {
		return domain.Attachment{}, ErrInvalidInput
	}

	var owned bool
	if err := s.db.QueryRowContext(ctx, `
		select exists (
			select 1 from work_requests
			where id = $1 and requested_by_user_id = $2
		)
	`, strings.TrimSpace(input.WorkRequestID), strings.TrimSpace(input.HomeownerUserID)).Scan(&owned); err != nil {
		return domain.Attachment{}, err
	}
	if !owned {
		return domain.Attachment{}, ErrWorkRequestNotFound
	}

	attachment := domain.Attachment{
		ID:               newID("att"),
		WorkRequestID:    strings.TrimSpace(input.WorkRequestID),
		UploadedByUserID: strings.TrimSpace(input.HomeownerUserID),
		FileName:         strings.TrimSpace(input.FileName),
		ContentType:      strings.TrimSpace(input.ContentType),
		SizeBytes:        input.SizeBytes,
		SHA256:           strings.TrimSpace(input.SHA256),
		StorageKey:       strings.TrimSpace(input.StorageKey),
		CreatedAt:        time.Now().UTC(),
	}
	_, err := s.db.ExecContext(ctx, `
		insert into attachments (
			id, work_request_id, project_id, uploaded_by_user_id, file_name, content_type,
			size_bytes, sha256, storage_key, created_at
		) values ($1,$2,null,$3,$4,$5,$6,$7,$8,$9)
	`, attachment.ID, attachment.WorkRequestID, attachment.UploadedByUserID, attachment.FileName,
		attachment.ContentType, attachment.SizeBytes, attachment.SHA256, attachment.StorageKey, attachment.CreatedAt)
	if err != nil {
		return domain.Attachment{}, err
	}
	return attachment, nil
}

func (s *PostgresStore) ListWorkRequestAttachments(ctx context.Context, homeownerUserID string, workRequestID string) ([]domain.Attachment, error) {
	rows, err := s.db.QueryContext(ctx, `
		select a.id, a.work_request_id, a.project_id, a.uploaded_by_user_id, a.file_name,
		       a.content_type, a.size_bytes, a.sha256, a.storage_key, a.created_at
		from attachments a
		join work_requests wr on wr.id = a.work_request_id
		where wr.id = $1 and wr.requested_by_user_id = $2
		order by a.created_at asc
	`, strings.TrimSpace(workRequestID), strings.TrimSpace(homeownerUserID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]domain.Attachment, 0)
	for rows.Next() {
		attachment, err := scanAttachment(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, attachment)
	}
	return out, rows.Err()
}

func (s *PostgresStore) listWorkRequestAttachmentsByID(ctx context.Context, workRequestID string) ([]domain.Attachment, error) {
	rows, err := s.db.QueryContext(ctx, `
		select id, work_request_id, project_id, uploaded_by_user_id, file_name,
		       content_type, size_bytes, sha256, storage_key, created_at
		from attachments
		where work_request_id = $1
		order by created_at asc
	`, strings.TrimSpace(workRequestID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make([]domain.Attachment, 0)
	for rows.Next() {
		attachment, err := scanAttachment(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, attachment)
	}
	return out, rows.Err()
}

func (s *PostgresStore) GetWorkRequestAttachment(ctx context.Context, homeownerUserID string, workRequestID string, attachmentID string) (domain.Attachment, error) {
	attachment, err := scanAttachment(s.db.QueryRowContext(ctx, `
		select a.id, a.work_request_id, a.project_id, a.uploaded_by_user_id, a.file_name,
		       a.content_type, a.size_bytes, a.sha256, a.storage_key, a.created_at
		from attachments a
		join work_requests wr on wr.id = a.work_request_id
		where a.id = $1 and wr.id = $2 and wr.requested_by_user_id = $3
	`, strings.TrimSpace(attachmentID), strings.TrimSpace(workRequestID), strings.TrimSpace(homeownerUserID)))
	if errors.Is(err, sql.ErrNoRows) || errors.Is(err, ErrAttachmentNotFound) {
		return domain.Attachment{}, ErrAttachmentNotFound
	}
	return attachment, err
}

func (s *PostgresStore) GetWorkRequestAttachmentForContractor(ctx context.Context, contractorUserID string, workRequestID string, attachmentID string) (domain.Attachment, error) {
	attachment, err := scanAttachment(s.db.QueryRowContext(ctx, `
		select a.id, a.work_request_id, a.project_id, a.uploaded_by_user_id, a.file_name,
		       a.content_type, a.size_bytes, a.sha256, a.storage_key, a.created_at
		from attachments a
		join work_requests wr on wr.id = a.work_request_id
		where a.id = $1 and wr.id = $2 and (
			wr.status not in ($3, $4)
			or exists (
				select 1
				from projects pr
				join organization_members om on om.organization_id = pr.contractor_org_id
				where pr.work_request_id = wr.id and om.user_id = $5
			)
		)
	`, strings.TrimSpace(attachmentID), strings.TrimSpace(workRequestID),
		string(domain.WorkRequestStatusConverted), string(domain.WorkRequestStatusDeclined), strings.TrimSpace(contractorUserID)))
	if errors.Is(err, sql.ErrNoRows) || errors.Is(err, ErrAttachmentNotFound) {
		return domain.Attachment{}, ErrAttachmentNotFound
	}
	return attachment, err
}

func scanAttachment(scanner interface{ Scan(...any) error }) (domain.Attachment, error) {
	var attachment domain.Attachment
	var workRequestID sql.NullString
	var projectID sql.NullString
	err := scanner.Scan(
		&attachment.ID, &workRequestID, &projectID, &attachment.UploadedByUserID, &attachment.FileName,
		&attachment.ContentType, &attachment.SizeBytes, &attachment.SHA256, &attachment.StorageKey, &attachment.CreatedAt,
	)
	if errors.Is(err, sql.ErrNoRows) {
		return domain.Attachment{}, ErrAttachmentNotFound
	}
	if err != nil {
		return domain.Attachment{}, err
	}
	attachment.WorkRequestID = workRequestID.String
	attachment.ProjectID = projectID.String
	return attachment, nil
}
