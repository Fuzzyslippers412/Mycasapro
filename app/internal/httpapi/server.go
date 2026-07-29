package httpapi

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/config"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/filestore"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/store"
)

type Server struct {
	cfg   config.Config
	mux   *http.ServeMux
	store store.Store
	files filestore.Store
}

func NewServer(cfg config.Config) *http.Server {
	return NewServerWithStore(cfg, store.NewMemoryStore())
}

func NewServerWithStore(cfg config.Config, repo store.Store) *http.Server {
	return NewServerWithFileStore(cfg, repo, filestore.NewMemoryStore())
}

func NewServerWithFileStore(cfg config.Config, repo store.Store, files filestore.Store) *http.Server {
	api := &Server{
		cfg:   cfg,
		mux:   http.NewServeMux(),
		store: repo,
		files: files,
	}
	api.routes()

	return &http.Server{
		Addr:              cfg.Addr,
		Handler:           api.withMiddleware(api.mux),
		ReadHeaderTimeout: 5 * time.Second,
		IdleTimeout:       60 * time.Second,
		MaxHeaderBytes:    1 << 20,
	}
}

func (s *Server) routes() {
	s.mux.HandleFunc("GET /", s.handleRoot)
	s.mux.HandleFunc("GET /healthz", s.handleHealth)
	s.mux.HandleFunc("GET /api/v1/meta", s.handleMeta)
	s.mux.HandleFunc("POST /api/v1/auth/register", s.handleRegister)
	s.mux.HandleFunc("POST /api/v1/auth/login", s.handleLogin)
	s.mux.HandleFunc("POST /api/v1/auth/logout", s.handleLogout)
	s.mux.HandleFunc("GET /api/v1/auth/me", s.handleCurrentUser)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/dashboard", s.handleHomeownerDashboard)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/properties", s.handleListProperties)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/properties", s.handleCreateProperty)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/work-requests", s.handleListWorkRequests)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/work-requests", s.handleCreateWorkRequest)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/attachments", s.handleListWorkRequestAttachments)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/attachments", s.handleUploadWorkRequestAttachment)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/attachments/{attachmentID}", s.handleDownloadWorkRequestAttachment)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/invites", s.handleListWorkRequestInvites)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/invites", s.handleCreateWorkRequestInvite)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/invites/{inviteID}/revoke", s.handleRevokeWorkRequestInvite)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/work-requests/{workRequestID}/guest-estimates", s.handleListGuestEstimates)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/projects", s.handleListHomeownerProjects)
	s.mux.HandleFunc("GET /api/v1/homeowners/{homeownerID}/projects/{projectID}", s.handleGetHomeownerProject)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/projects/{projectID}/messages", s.handleCreateHomeownerMessage)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/projects/{projectID}/estimates/{estimateID}/approve", s.handleApproveEstimate)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/projects/{projectID}/estimates/{estimateID}/reject", s.handleRejectEstimate)
	s.mux.HandleFunc("POST /api/v1/homeowners/{homeownerID}/projects/{projectID}/invoices/{invoiceID}/payments", s.handleRecordInvoicePayment)
	s.mux.HandleFunc("GET /api/v1/contractors/{contractorID}/dashboard", s.handleContractorDashboard)
	s.mux.HandleFunc("GET /api/v1/contractors/{contractorID}/work-requests/{workRequestID}/attachments/{attachmentID}", s.handleDownloadContractorWorkRequestAttachment)
	s.mux.HandleFunc("GET /api/v1/contractors/{contractorID}/organizations", s.handleListOrganizations)
	s.mux.HandleFunc("POST /api/v1/contractors/{contractorID}/organizations", s.handleCreateOrganization)
	s.mux.HandleFunc("GET /api/v1/contractors/{contractorID}/projects", s.handleListContractorProjects)
	s.mux.HandleFunc("GET /api/v1/contractors/{contractorID}/projects/{projectID}", s.handleGetContractorProject)
	s.mux.HandleFunc("POST /api/v1/contractors/{contractorID}/projects/{projectID}/messages", s.handleCreateContractorMessage)
	s.mux.HandleFunc("POST /api/v1/contractors/{contractorID}/projects/{projectID}/estimates", s.handleCreateEstimate)
	s.mux.HandleFunc("POST /api/v1/contractors/{contractorID}/projects/{projectID}/appointments", s.handleCreateAppointment)
	s.mux.HandleFunc("POST /api/v1/contractors/{contractorID}/projects/{projectID}/invoices", s.handleCreateInvoice)
	s.mux.HandleFunc("POST /api/v1/contractors/{contractorID}/organizations/{organizationID}/projects", s.handleCreateProjectFromRequest)
	s.mux.HandleFunc("GET /api/v1/invites/{token}", s.handleGetInviteTask)
	s.mux.HandleFunc("POST /api/v1/invites/{token}/estimates", s.handleCreateGuestEstimate)
	s.mux.HandleFunc("GET /api/v1/invites/{token}/attachments/{attachmentID}", s.handleDownloadInviteAttachment)
}

func (s *Server) handleRoot(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"name":           s.cfg.AppName,
		"product":        "home-maintenance",
		"status":         "ok",
		"web_url":        s.cfg.WebURL,
		"store_backend":  s.cfg.StoreBackend,
		"email_delivery": s.cfg.EmailDeliveryEnabled(),
	})
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	healthCtx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(healthCtx); err != nil {
		writeJSON(w, http.StatusServiceUnavailable, map[string]any{
			"ok": false, "service": "mycasapro-app", "env": s.cfg.Env, "store_backend": s.cfg.StoreBackend,
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"ok":             true,
		"service":        "mycasapro-app",
		"env":            s.cfg.Env,
		"database":       strings.TrimSpace(s.cfg.DatabaseURL) != "",
		"store_backend":  s.cfg.StoreBackend,
		"email_delivery": s.cfg.EmailDeliveryEnabled(),
		"time":           time.Now().UTC().Format(time.RFC3339),
	})
}

func (s *Server) handleMeta(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"name":           s.cfg.AppName,
		"product":        "home-maintenance",
		"store_backend":  s.cfg.StoreBackend,
		"email_delivery": s.cfg.EmailDeliveryEnabled(),
		"roles": []string{
			"homeowner",
			"contractor",
			"contractor_admin",
			"crew_member",
			"platform_admin",
		},
		"modules": []string{
			"properties",
			"work_requests",
			"projects",
			"estimates",
			"appointments",
			"invoices",
			"payments",
			"messages",
		},
	})
}

func (s *Server) withMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		s.applySecurityHeaders(w)
		originAllowed := s.applyCORS(w, r)
		if r.Method == http.MethodOptions {
			if !originAllowed {
				writeError(w, http.StatusForbidden, "origin_not_allowed", "request origin is not allowed")
				return
			}
			w.WriteHeader(http.StatusNoContent)
			return
		}
		if strings.TrimSpace(r.Header.Get("Origin")) != "" && !originAllowed {
			writeError(w, http.StatusForbidden, "origin_not_allowed", "request origin is not allowed")
			return
		}

		r = s.withRequestPrincipal(r)
		if !s.authorizeScopedPath(w, r) {
			return
		}

		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, requestLogPath(r.URL.Path), time.Since(start))
	})
}

func requestLogPath(path string) string {
	if strings.HasPrefix(path, "/api/v1/invites/") {
		return "/api/v1/invites/[redacted]"
	}
	return path
}

func (s *Server) applySecurityHeaders(w http.ResponseWriter) {
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("X-Frame-Options", "DENY")
	w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
	w.Header().Set("Cache-Control", "no-store")
}

func (s *Server) applyCORS(w http.ResponseWriter, r *http.Request) bool {
	origin := strings.TrimSpace(r.Header.Get("Origin"))
	if origin == "" {
		return true
	}
	for _, allowed := range s.cfg.AllowedOrigins {
		if origin == allowed {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Credentials", "true")
			w.Header().Set("Vary", "Origin")
			w.Header().Set("Access-Control-Allow-Headers", "Authorization, Content-Type")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
			return true
		}
	}
	return false
}

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

type createPropertyRequest struct {
	Label        string `json:"label"`
	AddressLine1 string `json:"address_line_1"`
	AddressLine2 string `json:"address_line_2"`
	City         string `json:"city"`
	Region       string `json:"region"`
	PostalCode   string `json:"postal_code"`
	CountryCode  string `json:"country_code"`
}

type createWorkRequestRequest struct {
	PropertyID      string `json:"property_id"`
	Title           string `json:"title"`
	Category        string `json:"category"`
	Area            string `json:"area"`
	Urgency         string `json:"urgency"`
	Description     string `json:"description"`
	PreferredTiming string `json:"preferred_timing"`
}

type createOrganizationRequest struct {
	Name string `json:"name"`
}

type createProjectFromRequestRequest struct {
	WorkRequestID string `json:"work_request_id"`
	Title         string `json:"title"`
}

type estimateLineItemRequest struct {
	Label       string `json:"label"`
	AmountCents int64  `json:"amount_cents"`
}

type createEstimateRequest struct {
	Summary            string                    `json:"summary"`
	Notes              string                    `json:"notes"`
	DepositAmountCents int64                     `json:"deposit_amount_cents"`
	LineItems          []estimateLineItemRequest `json:"line_items"`
}

type createAppointmentRequest struct {
	Title    string    `json:"title"`
	Notes    string    `json:"notes"`
	StartsAt time.Time `json:"starts_at"`
	EndsAt   time.Time `json:"ends_at"`
}

type createInvoiceRequest struct {
	Summary     string    `json:"summary"`
	Notes       string    `json:"notes"`
	AmountCents int64     `json:"amount_cents"`
	DueAt       time.Time `json:"due_at"`
}

type recordInvoicePaymentRequest struct {
	AmountCents int64  `json:"amount_cents"`
	Note        string `json:"note"`
}

type createMessageRequest struct {
	Body       string `json:"body"`
	Visibility string `json:"visibility"`
}

func (s *Server) handleHomeownerDashboard(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}

	dashboard, err := s.store.GetHomeownerDashboard(r.Context(), homeownerID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "dashboard_unavailable", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, dashboard)
}

func (s *Server) handleListProperties(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}

	properties, err := s.store.ListProperties(r.Context(), homeownerID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "properties_unavailable", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"homeowner_user_id": homeownerID,
		"properties":        properties,
	})
}

func (s *Server) handleCreateProperty(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}

	var req createPropertyRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	property, err := s.store.CreateProperty(r.Context(), store.CreatePropertyInput{
		HomeownerUserID: homeownerID,
		Label:           req.Label,
		AddressLine1:    req.AddressLine1,
		AddressLine2:    req.AddressLine2,
		City:            req.City,
		Region:          req.Region,
		PostalCode:      req.PostalCode,
		CountryCode:     req.CountryCode,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_property", "label, address, city, region, and postal code are required")
		default:
			writeError(w, http.StatusInternalServerError, "property_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, property)
}

func (s *Server) handleListWorkRequests(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}

	workRequests, err := s.store.ListWorkRequests(r.Context(), homeownerID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "work_requests_unavailable", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"homeowner_user_id": homeownerID,
		"work_requests":     workRequests,
	})
}

func (s *Server) handleCreateWorkRequest(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}

	var req createWorkRequestRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	workRequest, err := s.store.CreateWorkRequest(r.Context(), store.CreateWorkRequestInput{
		HomeownerUserID: homeownerID,
		PropertyID:      req.PropertyID,
		Title:           req.Title,
		Category:        req.Category,
		Area:            req.Area,
		Urgency:         req.Urgency,
		Description:     req.Description,
		PreferredTiming: req.PreferredTiming,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_work_request", "property, title, category, area, urgency, and description are required")
		case errors.Is(err, store.ErrPropertyNotFound):
			writeError(w, http.StatusNotFound, "property_not_found", "the selected property does not belong to this homeowner")
		default:
			writeError(w, http.StatusInternalServerError, "work_request_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, workRequest)
}

func (s *Server) handleListHomeownerProjects(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}

	projects, err := s.store.ListProjectsForHomeowner(r.Context(), homeownerID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "projects_unavailable", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"homeowner_user_id": homeownerID,
		"projects":          projects,
	})
}

func (s *Server) handleGetHomeownerProject(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}

	project, err := s.store.GetProjectDetailForHomeowner(r.Context(), homeownerID, projectID)
	if err != nil {
		switch {
		case errors.Is(err, store.ErrProjectNotFound):
			writeError(w, http.StatusNotFound, "project_not_found", "project not found")
		default:
			writeError(w, http.StatusInternalServerError, "project_unavailable", err.Error())
		}
		return
	}
	writeJSON(w, http.StatusOK, project)
}

func (s *Server) handleContractorDashboard(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}

	dashboard, err := s.store.GetContractorDashboard(r.Context(), contractorID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "dashboard_unavailable", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, dashboard)
}

func (s *Server) handleListOrganizations(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}

	organizations, err := s.store.ListOrganizations(r.Context(), contractorID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "organizations_unavailable", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"contractor_user_id": contractorID,
		"organizations":      organizations,
	})
}

func (s *Server) handleCreateOrganization(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}

	var req createOrganizationRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	organization, err := s.store.CreateOrganization(r.Context(), store.CreateOrganizationInput{
		ContractorUserID: contractorID,
		Name:             req.Name,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_organization", "organization name is required")
		default:
			writeError(w, http.StatusInternalServerError, "organization_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, organization)
}

func (s *Server) handleListContractorProjects(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}

	projects, err := s.store.ListProjectsForContractor(r.Context(), contractorID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "projects_unavailable", err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"contractor_user_id": contractorID,
		"projects":           projects,
	})
}

func (s *Server) handleGetContractorProject(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}

	project, err := s.store.GetProjectDetailForContractor(r.Context(), contractorID, projectID)
	if err != nil {
		switch {
		case errors.Is(err, store.ErrProjectNotFound):
			writeError(w, http.StatusNotFound, "project_not_found", "project not found")
		default:
			writeError(w, http.StatusInternalServerError, "project_unavailable", err.Error())
		}
		return
	}
	writeJSON(w, http.StatusOK, project)
}

func (s *Server) handleCreateHomeownerMessage(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}

	var req createMessageRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	message, err := s.store.CreateProjectMessage(r.Context(), store.CreateProjectMessageInput{
		AuthorUserID: homeownerID,
		AuthorRole:   domain.RoleHomeowner,
		ProjectID:    projectID,
		Visibility:   domain.MessageVisibilityShared,
		Body:         req.Body,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_message", "message body is required")
		case errors.Is(err, store.ErrProjectNotFound):
			writeError(w, http.StatusNotFound, "project_not_found", "project not found")
		default:
			writeError(w, http.StatusInternalServerError, "message_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, message)
}

func (s *Server) handleCreateContractorMessage(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}

	var req createMessageRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	visibility := domain.MessageVisibilityShared
	if strings.TrimSpace(req.Visibility) != "" {
		visibility = domain.MessageVisibility(strings.TrimSpace(req.Visibility))
	}

	message, err := s.store.CreateProjectMessage(r.Context(), store.CreateProjectMessageInput{
		AuthorUserID: contractorID,
		AuthorRole:   domain.RoleContractor,
		ProjectID:    projectID,
		Visibility:   visibility,
		Body:         req.Body,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_message", "message body and valid visibility are required")
		case errors.Is(err, store.ErrForbidden):
			writeError(w, http.StatusForbidden, "forbidden", "contractor cannot post to this project")
		case errors.Is(err, store.ErrProjectNotFound):
			writeError(w, http.StatusNotFound, "project_not_found", "project not found")
		default:
			writeError(w, http.StatusInternalServerError, "message_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, message)
}

func (s *Server) handleCreateEstimate(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}

	var req createEstimateRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	lineItems := make([]store.EstimateLineItemInput, 0, len(req.LineItems))
	for _, item := range req.LineItems {
		lineItems = append(lineItems, store.EstimateLineItemInput{
			Label:       item.Label,
			AmountCents: item.AmountCents,
		})
	}

	estimate, err := s.store.CreateEstimate(r.Context(), store.CreateEstimateInput{
		ContractorUserID:   contractorID,
		ProjectID:          projectID,
		Summary:            req.Summary,
		Notes:              req.Notes,
		DepositAmountCents: req.DepositAmountCents,
		LineItems:          lineItems,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_estimate", "summary and at least one positive line item are required")
		case errors.Is(err, store.ErrForbidden):
			writeError(w, http.StatusForbidden, "forbidden", "contractor cannot estimate this project")
		case errors.Is(err, store.ErrProjectNotFound):
			writeError(w, http.StatusNotFound, "project_not_found", "project not found")
		default:
			writeError(w, http.StatusInternalServerError, "estimate_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, estimate)
}

func (s *Server) handleCreateAppointment(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}

	var req createAppointmentRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	appointment, err := s.store.CreateAppointment(r.Context(), store.CreateAppointmentInput{
		ContractorUserID: contractorID,
		ProjectID:        projectID,
		Title:            req.Title,
		Notes:            req.Notes,
		StartsAt:         req.StartsAt,
		EndsAt:           req.EndsAt,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_appointment", "title, start time, and end time are required")
		case errors.Is(err, store.ErrForbidden):
			writeError(w, http.StatusForbidden, "forbidden", "contractor cannot schedule this project")
		case errors.Is(err, store.ErrProjectNotFound):
			writeError(w, http.StatusNotFound, "project_not_found", "project not found")
		default:
			writeError(w, http.StatusInternalServerError, "appointment_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, appointment)
}

func (s *Server) handleCreateInvoice(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}

	var req createInvoiceRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	invoice, err := s.store.CreateInvoice(r.Context(), store.CreateInvoiceInput{
		ContractorUserID: contractorID,
		ProjectID:        projectID,
		Summary:          req.Summary,
		Notes:            req.Notes,
		AmountCents:      req.AmountCents,
		DueAt:            req.DueAt,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_invoice", "summary, amount, and due date are required")
		case errors.Is(err, store.ErrForbidden):
			writeError(w, http.StatusForbidden, "forbidden", "contractor cannot invoice this project")
		case errors.Is(err, store.ErrProjectNotFound):
			writeError(w, http.StatusNotFound, "project_not_found", "project not found")
		default:
			writeError(w, http.StatusInternalServerError, "invoice_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, invoice)
}

func (s *Server) handleRecordInvoicePayment(w http.ResponseWriter, r *http.Request) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}
	invoiceID, ok := requirePathValue(w, r, "invoiceID")
	if !ok {
		return
	}

	var req recordInvoicePaymentRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	invoice, err := s.store.RecordInvoicePayment(r.Context(), store.RecordInvoicePaymentInput{
		HomeownerUserID: homeownerID,
		ProjectID:       projectID,
		InvoiceID:       invoiceID,
		AmountCents:     req.AmountCents,
		Note:            req.Note,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_payment", "payment amount must be positive and cannot exceed the balance")
		case errors.Is(err, store.ErrProjectNotFound), errors.Is(err, store.ErrInvoiceNotFound):
			writeError(w, http.StatusNotFound, "invoice_not_found", "invoice not found")
		case errors.Is(err, store.ErrInvoiceUnavailable):
			writeError(w, http.StatusConflict, "invoice_unavailable", "invoice is already fully paid")
		default:
			writeError(w, http.StatusInternalServerError, "invoice_payment_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusOK, invoice)
}

func (s *Server) handleApproveEstimate(w http.ResponseWriter, r *http.Request) {
	s.handleEstimateDecision(w, r, true)
}

func (s *Server) handleRejectEstimate(w http.ResponseWriter, r *http.Request) {
	s.handleEstimateDecision(w, r, false)
}

func (s *Server) handleEstimateDecision(w http.ResponseWriter, r *http.Request, approve bool) {
	homeownerID, ok := requirePathValue(w, r, "homeownerID")
	if !ok {
		return
	}
	projectID, ok := requirePathValue(w, r, "projectID")
	if !ok {
		return
	}
	estimateID, ok := requirePathValue(w, r, "estimateID")
	if !ok {
		return
	}

	var (
		estimate domain.Estimate
		err      error
	)
	if approve {
		estimate, err = s.store.ApproveEstimate(r.Context(), homeownerID, projectID, estimateID)
	} else {
		estimate, err = s.store.RejectEstimate(r.Context(), homeownerID, projectID, estimateID)
	}
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_estimate_decision", "homeowner, project, and estimate identifiers are required")
		case errors.Is(err, store.ErrProjectNotFound), errors.Is(err, store.ErrEstimateNotFound):
			writeError(w, http.StatusNotFound, "estimate_not_found", "estimate not found")
		case errors.Is(err, store.ErrEstimateUnavailable):
			writeError(w, http.StatusConflict, "estimate_unavailable", "estimate has already been decided")
		default:
			writeError(w, http.StatusInternalServerError, "estimate_decision_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusOK, estimate)
}

func (s *Server) handleCreateProjectFromRequest(w http.ResponseWriter, r *http.Request) {
	contractorID, ok := requirePathValue(w, r, "contractorID")
	if !ok {
		return
	}
	organizationID, ok := requirePathValue(w, r, "organizationID")
	if !ok {
		return
	}

	var req createProjectFromRequestRequest
	if err := decodeJSON(r, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid_json", err.Error())
		return
	}

	project, err := s.store.CreateProjectFromRequest(r.Context(), store.CreateProjectFromRequestInput{
		ContractorUserID: contractorID,
		OrganizationID:   organizationID,
		WorkRequestID:    req.WorkRequestID,
		Title:            req.Title,
	})
	if err != nil {
		switch {
		case errors.Is(err, store.ErrInvalidInput):
			writeError(w, http.StatusBadRequest, "invalid_project_request", "organization and work request are required")
		case errors.Is(err, store.ErrForbidden):
			writeError(w, http.StatusForbidden, "forbidden", "contractor does not belong to this organization")
		case errors.Is(err, store.ErrWorkRequestNotFound):
			writeError(w, http.StatusNotFound, "work_request_not_found", "work request not found")
		case errors.Is(err, store.ErrWorkRequestUnavailable):
			writeError(w, http.StatusConflict, "work_request_unavailable", "work request is no longer available")
		default:
			writeError(w, http.StatusInternalServerError, "project_create_failed", err.Error())
		}
		return
	}

	writeJSON(w, http.StatusCreated, project)
}

func requirePathValue(w http.ResponseWriter, r *http.Request, key string) (string, bool) {
	value := strings.TrimSpace(r.PathValue(key))
	if value == "" {
		writeError(w, http.StatusBadRequest, "missing_path_value", key+" is required")
		return "", false
	}
	return value, true
}

func decodeJSON(r *http.Request, dst any) error {
	defer r.Body.Close()
	decoder := json.NewDecoder(io.LimitReader(r.Body, 1<<20))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(dst); err != nil {
		return err
	}
	if err := decoder.Decode(&struct{}{}); err != io.EOF {
		return errors.New("request body must contain a single JSON object")
	}
	return nil
}

func writeError(w http.ResponseWriter, status int, code string, message string) {
	writeJSON(w, status, map[string]string{
		"error":   code,
		"message": message,
	})
}
