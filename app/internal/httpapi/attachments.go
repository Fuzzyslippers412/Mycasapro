package httpapi

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"io"
	"mime"
	"net/http"
	"path/filepath"
	"strings"
	"unicode"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/filestore"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/store"
)

const (
	maxAttachmentBytes       = 10 << 20
	maxAttachmentsPerRequest = 5
)

func (s *Server) handleUploadWorkRequestAttachment(w http.ResponseWriter, r *http.Request) {
	homeownerID, workRequestID, ok := attachmentPathValues(w, r)
	if !ok {
		return
	}

	existing, err := s.store.ListWorkRequestAttachments(r.Context(), homeownerID, workRequestID)
	if err != nil {
		writeAttachmentStoreError(w, err)
		return
	}
	if len(existing) >= maxAttachmentsPerRequest {
		writeError(w, http.StatusConflict, "attachment_limit", "a repair request can contain up to five files")
		return
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxAttachmentBytes+(1<<20))
	if err := r.ParseMultipartForm(maxAttachmentBytes); err != nil {
		var maxErr *http.MaxBytesError
		if errors.As(err, &maxErr) {
			writeError(w, http.StatusRequestEntityTooLarge, "file_too_large", "files must be 10 MB or smaller")
			return
		}
		writeError(w, http.StatusBadRequest, "invalid_upload", "send one file using the file field")
		return
	}
	if r.MultipartForm != nil {
		defer r.MultipartForm.RemoveAll()
	}

	file, header, err := r.FormFile("file")
	if err != nil {
		writeError(w, http.StatusBadRequest, "file_required", "choose a photo or PDF to upload")
		return
	}
	defer file.Close()

	data, err := io.ReadAll(io.LimitReader(file, maxAttachmentBytes+1))
	if err != nil {
		writeError(w, http.StatusBadRequest, "upload_failed", "unable to read the uploaded file")
		return
	}
	if len(data) == 0 {
		writeError(w, http.StatusBadRequest, "empty_file", "the selected file is empty")
		return
	}
	if len(data) > maxAttachmentBytes {
		writeError(w, http.StatusRequestEntityTooLarge, "file_too_large", "files must be 10 MB or smaller")
		return
	}

	contentType, ok := allowedAttachmentType(data, header.Header.Get("Content-Type"))
	if !ok {
		writeError(w, http.StatusUnsupportedMediaType, "unsupported_file", "supported files are JPEG, PNG, WebP, HEIC, and PDF")
		return
	}
	fileName := safeFileName(header.Filename)
	if fileName == "" {
		writeError(w, http.StatusBadRequest, "invalid_file_name", "the uploaded file name is invalid")
		return
	}
	storageKey, err := newStorageKey()
	if err != nil {
		writeError(w, http.StatusInternalServerError, "upload_failed", "unable to allocate file storage")
		return
	}
	if err := s.files.Save(r.Context(), storageKey, data); err != nil {
		writeError(w, http.StatusInternalServerError, "upload_failed", "unable to persist the uploaded file")
		return
	}

	digest := sha256.Sum256(data)
	attachment, err := s.store.CreateWorkRequestAttachment(r.Context(), store.CreateWorkRequestAttachmentInput{
		HomeownerUserID: homeownerID,
		WorkRequestID:   workRequestID,
		StorageKey:      storageKey,
		FileName:        fileName,
		ContentType:     contentType,
		SizeBytes:       int64(len(data)),
		SHA256:          hex.EncodeToString(digest[:]),
	})
	if err != nil {
		_ = s.files.Delete(r.Context(), storageKey)
		writeAttachmentStoreError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, attachmentPayload(attachment, homeownerID, workRequestID))
}

func (s *Server) handleListWorkRequestAttachments(w http.ResponseWriter, r *http.Request) {
	homeownerID, workRequestID, ok := attachmentPathValues(w, r)
	if !ok {
		return
	}
	attachments, err := s.store.ListWorkRequestAttachments(r.Context(), homeownerID, workRequestID)
	if err != nil {
		writeAttachmentStoreError(w, err)
		return
	}
	payload := make([]map[string]any, 0, len(attachments))
	for _, attachment := range attachments {
		payload = append(payload, attachmentPayload(attachment, homeownerID, workRequestID))
	}
	writeJSON(w, http.StatusOK, map[string]any{"attachments": payload})
}

func (s *Server) handleDownloadWorkRequestAttachment(w http.ResponseWriter, r *http.Request) {
	homeownerID, workRequestID, ok := attachmentPathValues(w, r)
	if !ok {
		return
	}
	attachmentID, ok := requirePathValue(w, r, "attachmentID")
	if !ok {
		return
	}
	attachment, err := s.store.GetWorkRequestAttachment(r.Context(), homeownerID, workRequestID, attachmentID)
	if err != nil {
		writeAttachmentStoreError(w, err)
		return
	}
	s.serveAttachment(w, r, attachment)
}

func (s *Server) handleDownloadContractorWorkRequestAttachment(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}
	workRequestID, ok := requirePathValue(w, r, "workRequestID")
	if !ok {
		return
	}
	attachmentID, ok := requirePathValue(w, r, "attachmentID")
	if !ok {
		return
	}
	attachment, err := s.store.GetWorkRequestAttachmentForContractor(r.Context(), contractorID, workRequestID, attachmentID)
	if err != nil {
		writeAttachmentStoreError(w, err)
		return
	}
	s.serveAttachment(w, r, attachment)
}

func (s *Server) serveAttachment(w http.ResponseWriter, r *http.Request, attachment domain.Attachment) {
	data, err := s.files.Read(r.Context(), attachment.StorageKey)
	if errors.Is(err, filestore.ErrNotFound) {
		writeError(w, http.StatusNotFound, "attachment_missing", "the file is no longer available")
		return
	}
	if err != nil {
		writeError(w, http.StatusInternalServerError, "attachment_unavailable", "unable to read the file")
		return
	}

	w.Header().Set("Content-Type", attachment.ContentType)
	w.Header().Set("Content-Length", int64String(int64(len(data))))
	w.Header().Set("Content-Disposition", mime.FormatMediaType("inline", map[string]string{"filename": attachment.FileName}))
	w.Header().Set("Cache-Control", "private, no-store")
	w.Header().Set("X-Content-SHA256", attachment.SHA256)
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(data)
}

func attachmentPathValues(w http.ResponseWriter, r *http.Request) (string, string, bool) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return "", "", false
	}
	workRequestID, ok := requirePathValue(w, r, "workRequestID")
	return homeownerID, workRequestID, ok
}

func attachmentPayload(attachment domain.Attachment, homeownerID string, workRequestID string) map[string]any {
	return map[string]any{
		"id":                  attachment.ID,
		"work_request_id":     attachment.WorkRequestID,
		"uploaded_by_user_id": attachment.UploadedByUserID,
		"file_name":           attachment.FileName,
		"content_type":        attachment.ContentType,
		"size_bytes":          attachment.SizeBytes,
		"sha256":              attachment.SHA256,
		"created_at":          attachment.CreatedAt,
		"content_path":        "/api/v1/homeowners/" + homeownerID + "/work-requests/" + workRequestID + "/attachments/" + attachment.ID,
	}
}

func writeAttachmentStoreError(w http.ResponseWriter, err error) {
	switch {
	case errors.Is(err, store.ErrWorkRequestNotFound):
		writeError(w, http.StatusNotFound, "work_request_not_found", "repair request not found")
	case errors.Is(err, store.ErrAttachmentNotFound):
		writeError(w, http.StatusNotFound, "attachment_not_found", "attachment not found")
	case errors.Is(err, store.ErrInvalidInput):
		writeError(w, http.StatusBadRequest, "invalid_attachment", "attachment metadata is invalid")
	default:
		writeError(w, http.StatusInternalServerError, "attachment_failed", "unable to complete the attachment request")
	}
}

func allowedAttachmentType(data []byte, declared string) (string, bool) {
	detected := http.DetectContentType(data)
	switch detected {
	case "image/jpeg", "image/png", "image/webp", "application/pdf":
		return detected, true
	}
	if isHEIC(data) && strings.HasPrefix(strings.ToLower(strings.TrimSpace(declared)), "image/") {
		return "image/heic", true
	}
	return "", false
}

func isHEIC(data []byte) bool {
	if len(data) < 12 || string(data[4:8]) != "ftyp" {
		return false
	}
	brand := string(data[8:12])
	switch brand {
	case "heic", "heix", "hevc", "hevx", "mif1", "msf1":
		return true
	default:
		return false
	}
}

func safeFileName(value string) string {
	value = filepath.Base(strings.TrimSpace(value))
	value = strings.Map(func(char rune) rune {
		if unicode.IsControl(char) || char == '/' || char == '\\' {
			return -1
		}
		return char
	}, value)
	value = strings.TrimSpace(value)
	if len(value) > 180 {
		value = value[:180]
	}
	return value
}

func newStorageKey() (string, error) {
	raw := make([]byte, 24)
	if _, err := rand.Read(raw); err != nil {
		return "", err
	}
	return "file_" + base64.RawURLEncoding.EncodeToString(raw), nil
}

func int64String(value int64) string {
	if value == 0 {
		return "0"
	}
	var buffer [20]byte
	index := len(buffer)
	for value > 0 {
		index--
		buffer[index] = byte('0' + value%10)
		value /= 10
	}
	return string(buffer[index:])
}
