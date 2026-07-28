package store

import (
	"context"
	"slices"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func (s *MemoryStore) CreateWorkRequestInvite(_ context.Context, input CreateWorkRequestInviteInput) (domain.WorkRequestInvite, error) {
	homeownerID := strings.TrimSpace(input.HomeownerUserID)
	workRequestID := strings.TrimSpace(input.WorkRequestID)
	tokenHash := strings.TrimSpace(input.TokenHash)
	if homeownerID == "" || workRequestID == "" || len(tokenHash) != 64 || !input.ExpiresAt.After(time.Now().UTC()) {
		return domain.WorkRequestInvite{}, ErrInvalidInput
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	request, ok := s.workRequestByIDLocked(workRequestID)
	if !ok || request.RequestedByUserID != homeownerID {
		return domain.WorkRequestInvite{}, ErrWorkRequestNotFound
	}
	for _, existing := range s.invites {
		if existing.TokenHash == tokenHash {
			return domain.WorkRequestInvite{}, ErrInvalidInput
		}
	}
	invite := domain.WorkRequestInvite{
		ID:              newID("inv"),
		WorkRequestID:   workRequestID,
		HomeownerUserID: homeownerID,
		ExpiresAt:       input.ExpiresAt.UTC(),
		CreatedAt:       time.Now().UTC(),
	}
	s.invites = append(s.invites, memoryWorkRequestInvite{Invite: invite, TokenHash: tokenHash})
	return invite, nil
}

func (s *MemoryStore) ListWorkRequestInvites(_ context.Context, homeownerUserID string, workRequestID string) ([]domain.WorkRequestInvite, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	request, ok := s.workRequestByIDLocked(strings.TrimSpace(workRequestID))
	if !ok || request.RequestedByUserID != strings.TrimSpace(homeownerUserID) {
		return nil, ErrWorkRequestNotFound
	}
	out := make([]domain.WorkRequestInvite, 0)
	for _, stored := range s.invites {
		if stored.Invite.WorkRequestID == request.ID {
			out = append(out, stored.Invite)
		}
	}
	slices.SortFunc(out, func(a, b domain.WorkRequestInvite) int { return b.CreatedAt.Compare(a.CreatedAt) })
	return out, nil
}

func (s *MemoryStore) RevokeWorkRequestInvite(_ context.Context, homeownerUserID string, workRequestID string, inviteID string, now time.Time) (domain.WorkRequestInvite, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	request, ok := s.workRequestByIDLocked(strings.TrimSpace(workRequestID))
	if !ok || request.RequestedByUserID != strings.TrimSpace(homeownerUserID) {
		return domain.WorkRequestInvite{}, ErrWorkRequestNotFound
	}
	for index := range s.invites {
		invite := &s.invites[index].Invite
		if invite.ID == strings.TrimSpace(inviteID) && invite.WorkRequestID == request.ID {
			revokedAt := now.UTC()
			invite.RevokedAt = &revokedAt
			return *invite, nil
		}
	}
	return domain.WorkRequestInvite{}, ErrInviteNotFound
}

func (s *MemoryStore) GetInviteTask(_ context.Context, tokenHash string, now time.Time) (domain.InviteTask, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	stored, err := s.activeInviteByHashLocked(strings.TrimSpace(tokenHash), now)
	if err != nil {
		return domain.InviteTask{}, err
	}
	request, ok := s.workRequestByIDLocked(stored.Invite.WorkRequestID)
	if !ok {
		return domain.InviteTask{}, ErrInviteNotFound
	}
	property, ok := s.propertyByIDLocked(request.PropertyID)
	if !ok {
		return domain.InviteTask{}, ErrInviteNotFound
	}
	request.Attachments = s.listWorkRequestAttachmentsLocked(request.ID)
	request.GuestEstimateCount = s.guestEstimateCountLocked(request.ID)
	return domain.InviteTask{
		Invite:      stored.Invite,
		WorkRequest: request,
		Property: domain.InviteProperty{
			Label: property.Label, City: property.City, Region: property.Region, CountryCode: property.CountryCode,
		},
	}, nil
}

func (s *MemoryStore) GetWorkRequestAttachmentForInvite(_ context.Context, tokenHash string, attachmentID string, now time.Time) (domain.Attachment, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	stored, err := s.activeInviteByHashLocked(strings.TrimSpace(tokenHash), now)
	if err != nil {
		return domain.Attachment{}, err
	}
	for _, attachment := range s.attachments {
		if attachment.ID == strings.TrimSpace(attachmentID) && attachment.WorkRequestID == stored.Invite.WorkRequestID {
			return attachment, nil
		}
	}
	return domain.Attachment{}, ErrAttachmentNotFound
}

func (s *MemoryStore) CreateGuestEstimate(_ context.Context, input CreateGuestEstimateInput) (domain.GuestEstimate, error) {
	input, total, ok := normalizeGuestEstimateInput(input)
	if !ok {
		return domain.GuestEstimate{}, ErrInvalidInput
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	stored, err := s.activeInviteByHashLocked(strings.TrimSpace(input.TokenHash), input.Now)
	if err != nil {
		return domain.GuestEstimate{}, err
	}
	for _, existing := range s.guestEstimates {
		if existing.InviteID == stored.Invite.ID && strings.EqualFold(existing.Email, input.Email) {
			return domain.GuestEstimate{}, ErrEstimateUnavailable
		}
	}
	estimateID := newID("gest")
	lineItems := make([]domain.GuestEstimateLineItem, 0, len(input.LineItems))
	for position, inputItem := range input.LineItems {
		lineItems = append(lineItems, domain.GuestEstimateLineItem{
			ID: newID("gli"), GuestEstimateID: estimateID, Label: inputItem.Label, AmountCents: inputItem.AmountCents, Position: position,
		})
	}
	estimate := domain.GuestEstimate{
		ID: estimateID, InviteID: stored.Invite.ID, WorkRequestID: stored.Invite.WorkRequestID,
		ContractorName: input.ContractorName, BusinessName: input.BusinessName, Email: input.Email,
		Summary: input.Summary, Notes: input.Notes, AvailableTiming: input.AvailableTiming,
		TotalAmountCents: total, LineItems: lineItems, CreatedAt: input.Now.UTC(),
	}
	s.guestEstimates = append(s.guestEstimates, estimate)
	for index := range s.workRequests {
		if s.workRequests[index].ID == estimate.WorkRequestID && (s.workRequests[index].Status == domain.WorkRequestStatusNew || s.workRequests[index].Status == domain.WorkRequestStatusReviewing) {
			s.workRequests[index].Status = domain.WorkRequestStatusQuoted
			break
		}
	}
	return estimate, nil
}

func (s *MemoryStore) ListGuestEstimates(_ context.Context, homeownerUserID string, workRequestID string) ([]domain.GuestEstimate, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	request, ok := s.workRequestByIDLocked(strings.TrimSpace(workRequestID))
	if !ok || request.RequestedByUserID != strings.TrimSpace(homeownerUserID) {
		return nil, ErrWorkRequestNotFound
	}
	out := make([]domain.GuestEstimate, 0)
	for _, estimate := range s.guestEstimates {
		if estimate.WorkRequestID == request.ID {
			out = append(out, estimate)
		}
	}
	slices.SortFunc(out, func(a, b domain.GuestEstimate) int { return b.CreatedAt.Compare(a.CreatedAt) })
	return out, nil
}

func (s *MemoryStore) activeInviteByHashLocked(tokenHash string, now time.Time) (memoryWorkRequestInvite, error) {
	for _, stored := range s.invites {
		if stored.TokenHash != tokenHash {
			continue
		}
		if stored.Invite.RevokedAt != nil {
			return memoryWorkRequestInvite{}, ErrInviteRevoked
		}
		if !stored.Invite.ExpiresAt.After(now.UTC()) {
			return memoryWorkRequestInvite{}, ErrInviteExpired
		}
		return stored, nil
	}
	return memoryWorkRequestInvite{}, ErrInviteNotFound
}

func (s *MemoryStore) guestEstimateCountLocked(workRequestID string) int {
	count := 0
	for _, estimate := range s.guestEstimates {
		if estimate.WorkRequestID == workRequestID {
			count++
		}
	}
	return count
}
