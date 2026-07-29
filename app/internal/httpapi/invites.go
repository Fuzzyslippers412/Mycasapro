package httpapi

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"net/http"
	"net/mail"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/notification"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/store"
)

const inviteLifetime = 7 * 24 * time.Hour

type createGuestEstimateRequest struct {
	ContractorName  string                         `json:"contractor_name"`
	BusinessName    string                         `json:"business_name"`
	Email           string                         `json:"email"`
	Summary         string                         `json:"summary"`
	Notes           string                         `json:"notes"`
	AvailableTiming string                         `json:"available_timing"`
	LineItems       []guestEstimateLineItemRequest `json:"line_items"`
}

type guestEstimateLineItemRequest struct {
	Label       string `json:"label"`
	AmountCents int64  `json:"amount_cents"`
}

type createWorkRequestInviteRequest struct {
	RecipientName  string `json:"recipient_name"`
	RecipientEmail string `json:"recipient_email"`
}

func (s *Server) handleCreateWorkRequestInvite(w http.ResponseWriter, r *http.Request) {
	homeownerID, workRequestID, ok := attachmentPathValues(w, r)
	if !ok {
		return
	}
	token, tokenHash, err := newInviteToken()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "invite_failed", "unable to create a secure share link")
		return
	}
	var req createWorkRequestInviteRequest
	if r.ContentLength != 0 {
		if err := decodeJSON(r, &req); err != nil {
			writeError(w, http.StatusBadRequest, "invalid_invitation", "send a valid contractor name and email")
			return
		}
	}
	req.RecipientName = strings.TrimSpace(req.RecipientName)
	req.RecipientEmail = strings.ToLower(strings.TrimSpace(req.RecipientEmail))
	if len(req.RecipientName) > 120 {
		writeError(w, http.StatusBadRequest, "invalid_invitation", "contractor name is too long")
		return
	}
	shareURL := strings.TrimRight(s.cfg.WebURL, "/") + "/invite/" + token
	expiresAt := time.Now().UTC().Add(inviteLifetime)
	message := notification.Message{}
	if req.RecipientEmail != "" {
		address, parseErr := mail.ParseAddress(req.RecipientEmail)
		if parseErr != nil || !strings.EqualFold(address.Address, req.RecipientEmail) || len(req.RecipientEmail) > 320 {
			writeError(w, http.StatusBadRequest, "invalid_invitation", "enter a valid contractor email")
			return
		}
		if !s.cfg.EmailDeliveryEnabled() {
			writeError(w, http.StatusServiceUnavailable, "email_unavailable", "email delivery is not configured; create a private link instead")
			return
		}
		message = notification.WorkRequestInvitation(s.cfg.AppName, req.RecipientName, shareURL, expiresAt)
	}
	invite, err := s.store.CreateWorkRequestInvite(r.Context(), store.CreateWorkRequestInviteInput{
		HomeownerUserID: homeownerID,
		WorkRequestID:   workRequestID,
		TokenHash:       tokenHash,
		RecipientName:   req.RecipientName,
		RecipientEmail:  req.RecipientEmail,
		EmailSubject:    message.Subject,
		EmailTextBody:   message.TextBody,
		EmailHTMLBody:   message.HTMLBody,
		ExpiresAt:       expiresAt,
	})
	if err != nil {
		writeInviteStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, map[string]any{
		"invite":    invite,
		"share_url": shareURL,
	})
}

func (s *Server) handleListWorkRequestInvites(w http.ResponseWriter, r *http.Request) {
	homeownerID, workRequestID, ok := attachmentPathValues(w, r)
	if !ok {
		return
	}
	invites, err := s.store.ListWorkRequestInvites(r.Context(), homeownerID, workRequestID)
	if err != nil {
		writeInviteStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"invites": invites})
}

func (s *Server) handleRevokeWorkRequestInvite(w http.ResponseWriter, r *http.Request) {
	homeownerID, workRequestID, ok := attachmentPathValues(w, r)
	if !ok {
		return
	}
	inviteID, ok := requirePathValue(w, r, "inviteID")
	if !ok {
		return
	}
	invite, err := s.store.RevokeWorkRequestInvite(r.Context(), homeownerID, workRequestID, inviteID, time.Now().UTC())
	if err != nil {
		writeInviteStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, invite)
}

func (s *Server) handleGetInviteTask(w http.ResponseWriter, r *http.Request) {
	token, tokenHash, ok := inviteTokenPath(w, r)
	if !ok {
		return
	}
	task, err := s.store.GetInviteTask(r.Context(), tokenHash, time.Now().UTC())
	if err != nil {
		writeInviteStoreError(w, err)
		return
	}
	attachments := make([]map[string]any, 0, len(task.WorkRequest.Attachments))
	for _, attachment := range task.WorkRequest.Attachments {
		attachments = append(attachments, map[string]any{
			"id": attachment.ID, "file_name": attachment.FileName, "content_type": attachment.ContentType,
			"size_bytes":   attachment.SizeBytes,
			"content_path": "/api/v1/invites/" + token + "/attachments/" + attachment.ID,
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"invite": map[string]any{
			"id": task.Invite.ID, "expires_at": task.Invite.ExpiresAt, "created_at": task.Invite.CreatedAt,
		},
		"property": task.Property,
		"work_request": map[string]any{
			"id": task.WorkRequest.ID, "title": task.WorkRequest.Title, "category": task.WorkRequest.Category,
			"area": task.WorkRequest.Area, "urgency": task.WorkRequest.Urgency,
			"description": task.WorkRequest.Description, "preferred_timing": task.WorkRequest.PreferredTiming,
			"attachments": attachments, "created_at": task.WorkRequest.CreatedAt,
		},
	})
}

func (s *Server) handleDownloadInviteAttachment(w http.ResponseWriter, r *http.Request) {
	_, tokenHash, ok := inviteTokenPath(w, r)
	if !ok {
		return
	}
	attachmentID, ok := requirePathValue(w, r, "attachmentID")
	if !ok {
		return
	}
	attachment, err := s.store.GetWorkRequestAttachmentForInvite(r.Context(), tokenHash, attachmentID, time.Now().UTC())
	if err != nil {
		writeInviteStoreError(w, err)
		return
	}
	s.serveAttachment(w, r, attachment)
}

func (s *Server) handleCreateGuestEstimate(w http.ResponseWriter, r *http.Request) {
	_, tokenHash, ok := inviteTokenPath(w, r)
	if !ok {
		return
	}
	var req createGuestEstimateRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_estimate", "send valid estimate details")
		return
	}
	lineItems := make([]store.GuestEstimateLineItemInput, 0, len(req.LineItems))
	for _, item := range req.LineItems {
		lineItems = append(lineItems, store.GuestEstimateLineItemInput{Label: item.Label, AmountCents: item.AmountCents})
	}
	estimate, err := s.store.CreateGuestEstimate(r.Context(), store.CreateGuestEstimateInput{
		TokenHash: tokenHash, ContractorName: req.ContractorName, BusinessName: req.BusinessName, Email: req.Email,
		Summary: req.Summary, Notes: req.Notes, AvailableTiming: req.AvailableTiming, LineItems: lineItems, Now: time.Now().UTC(),
	})
	if err != nil {
		writeInviteStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, estimate)
}

func (s *Server) handleListGuestEstimates(w http.ResponseWriter, r *http.Request) {
	homeownerID, workRequestID, ok := attachmentPathValues(w, r)
	if !ok {
		return
	}
	estimates, err := s.store.ListGuestEstimates(r.Context(), homeownerID, workRequestID)
	if err != nil {
		writeInviteStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"estimates": estimates})
}

func inviteTokenPath(w http.ResponseWriter, r *http.Request) (string, string, bool) {
	token, ok := requirePathValue(w, r, "token")
	if !ok {
		return "", "", false
	}
	raw, err := base64.RawURLEncoding.DecodeString(token)
	if err != nil || len(raw) != 32 {
		writeError(w, http.StatusNotFound, "invite_not_found", "this share link is not available")
		return "", "", false
	}
	digest := sha256.Sum256(raw)
	return token, hex.EncodeToString(digest[:]), true
}

func newInviteToken() (string, string, error) {
	raw := make([]byte, 32)
	if _, err := rand.Read(raw); err != nil {
		return "", "", err
	}
	digest := sha256.Sum256(raw)
	return base64.RawURLEncoding.EncodeToString(raw), hex.EncodeToString(digest[:]), nil
}

func writeInviteStoreError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, store.ErrWorkRequestNotFound):
		writeError(w, http.StatusNotFound, "work_request_not_found", "repair request not found")
	case errors.Is(err, store.ErrInviteNotFound):
		writeError(w, http.StatusNotFound, "invite_not_found", "this share link is not available")
	case errors.Is(err, store.ErrInviteExpired):
		writeError(w, http.StatusGone, "invite_expired", "this share link has expired")
	case errors.Is(err, store.ErrInviteRevoked):
		writeError(w, http.StatusGone, "invite_revoked", "this share link has been revoked")
	case errors.Is(err, store.ErrInviteRateLimited):
		w.Header().Set("Retry-After", "3600")
		writeError(w, http.StatusTooManyRequests, "invitation_rate_limited", "too many email invitations were created recently; try again later")
	case errors.Is(err, store.ErrAttachmentNotFound):
		writeError(w, http.StatusNotFound, "attachment_not_found", "attachment not found")
	case errors.Is(err, store.ErrEstimateUnavailable):
		writeError(w, http.StatusConflict, "estimate_already_submitted", "an estimate from this email has already been submitted")
	case errors.Is(err, store.ErrInvalidInput):
		writeError(w, http.StatusBadRequest, "invalid_invite_request", "check the submitted information and try again")
	default:
		writeError(w, http.StatusInternalServerError, "invite_failed", "unable to complete the shared task request")
	}
}
