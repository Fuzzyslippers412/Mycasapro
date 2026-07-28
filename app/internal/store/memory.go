package store

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"slices"
	"strings"
	"sync"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

type MemoryStore struct {
	mu             sync.RWMutex
	users          []UserCredentials
	sessions       []memorySession
	properties     []domain.Property
	workRequests   []domain.WorkRequest
	attachments    []domain.Attachment
	invites        []memoryWorkRequestInvite
	guestEstimates []domain.GuestEstimate
	organizations  []domain.Organization
	projects       []domain.Project
	estimates      []domain.Estimate
	appointments   []domain.Appointment
	invoices       []domain.Invoice
	messages       []domain.ProjectMessage
	memberships    []organizationMembership
}

type memorySession struct {
	UserID    string
	TokenHash string
	ExpiresAt time.Time
	CreatedAt time.Time
}

type memoryWorkRequestInvite struct {
	Invite    domain.WorkRequestInvite
	TokenHash string
}

type organizationMembership struct {
	OrganizationID string
	UserID         string
	Role           string
	CreatedAt      time.Time
}

func NewMemoryStore() *MemoryStore {
	return &MemoryStore{
		users:          []UserCredentials{},
		sessions:       []memorySession{},
		properties:     []domain.Property{},
		workRequests:   []domain.WorkRequest{},
		attachments:    []domain.Attachment{},
		invites:        []memoryWorkRequestInvite{},
		guestEstimates: []domain.GuestEstimate{},
		organizations:  []domain.Organization{},
		projects:       []domain.Project{},
		estimates:      []domain.Estimate{},
		appointments:   []domain.Appointment{},
		invoices:       []domain.Invoice{},
		messages:       []domain.ProjectMessage{},
		memberships:    []organizationMembership{},
	}
}

func (s *MemoryStore) CreateUser(_ context.Context, input CreateUserInput) (domain.User, error) {
	email := strings.ToLower(strings.TrimSpace(input.Email))
	displayName := strings.TrimSpace(input.DisplayName)
	passwordHash := strings.TrimSpace(input.PasswordHash)
	if email == "" || displayName == "" || passwordHash == "" || !isRegistrationRole(input.Role) {
		return domain.User{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	for _, credentials := range s.users {
		if strings.EqualFold(credentials.User.Email, email) {
			return domain.User{}, ErrUserExists
		}
	}

	user := domain.User{
		ID:          newID("usr"),
		Email:       email,
		DisplayName: displayName,
		Role:        input.Role,
		CreatedAt:   time.Now().UTC(),
	}
	s.users = append(s.users, UserCredentials{User: user, PasswordHash: passwordHash})
	return user, nil
}

func (s *MemoryStore) GetUserByID(_ context.Context, userID string) (domain.User, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, credentials := range s.users {
		if credentials.User.ID == strings.TrimSpace(userID) {
			return credentials.User, nil
		}
	}
	return domain.User{}, ErrUserNotFound
}

func (s *MemoryStore) GetUserCredentialsByEmail(_ context.Context, email string) (UserCredentials, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, credentials := range s.users {
		if strings.EqualFold(credentials.User.Email, strings.TrimSpace(email)) {
			return credentials, nil
		}
	}
	return UserCredentials{}, ErrUserNotFound
}

func (s *MemoryStore) CreateSession(_ context.Context, input CreateSessionInput) error {
	if strings.TrimSpace(input.UserID) == "" || strings.TrimSpace(input.TokenHash) == "" || input.ExpiresAt.IsZero() {
		return ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	foundUser := false
	for _, credentials := range s.users {
		if credentials.User.ID == strings.TrimSpace(input.UserID) {
			foundUser = true
			break
		}
	}
	if !foundUser {
		return ErrUserNotFound
	}
	s.sessions = append(s.sessions, memorySession{
		UserID:    strings.TrimSpace(input.UserID),
		TokenHash: strings.TrimSpace(input.TokenHash),
		ExpiresAt: input.ExpiresAt.UTC(),
		CreatedAt: time.Now().UTC(),
	})
	return nil
}

func (s *MemoryStore) GetUserBySessionTokenHash(_ context.Context, tokenHash string, now time.Time) (domain.User, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, session := range s.sessions {
		if session.TokenHash == strings.TrimSpace(tokenHash) && session.ExpiresAt.After(now) {
			for _, credentials := range s.users {
				if credentials.User.ID == session.UserID {
					return credentials.User, nil
				}
			}
			return domain.User{}, ErrUserNotFound
		}
	}
	return domain.User{}, ErrSessionNotFound
}

func (s *MemoryStore) DeleteSession(_ context.Context, tokenHash string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	for index, session := range s.sessions {
		if session.TokenHash == strings.TrimSpace(tokenHash) {
			s.sessions = append(s.sessions[:index], s.sessions[index+1:]...)
			return nil
		}
	}
	return nil
}

func isRegistrationRole(role domain.Role) bool {
	return role == domain.RoleHomeowner || role == domain.RoleContractor
}

func (s *MemoryStore) CreateProperty(_ context.Context, input CreatePropertyInput) (domain.Property, error) {
	if strings.TrimSpace(input.HomeownerUserID) == "" ||
		strings.TrimSpace(input.Label) == "" ||
		strings.TrimSpace(input.AddressLine1) == "" ||
		strings.TrimSpace(input.City) == "" ||
		strings.TrimSpace(input.Region) == "" ||
		strings.TrimSpace(input.PostalCode) == "" {
		return domain.Property{}, ErrInvalidInput
	}

	property := domain.Property{
		ID:              newID("prop"),
		HomeownerUserID: strings.TrimSpace(input.HomeownerUserID),
		Label:           strings.TrimSpace(input.Label),
		AddressLine1:    strings.TrimSpace(input.AddressLine1),
		AddressLine2:    strings.TrimSpace(input.AddressLine2),
		City:            strings.TrimSpace(input.City),
		Region:          strings.TrimSpace(input.Region),
		PostalCode:      strings.TrimSpace(input.PostalCode),
		CountryCode:     defaultString(strings.ToUpper(strings.TrimSpace(input.CountryCode)), "US"),
		CreatedAt:       time.Now().UTC(),
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	s.properties = append(s.properties, property)
	return property, nil
}

func (s *MemoryStore) ListProperties(_ context.Context, homeownerUserID string) ([]domain.Property, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	out := make([]domain.Property, 0)
	for _, property := range s.properties {
		if property.HomeownerUserID == homeownerUserID {
			out = append(out, property)
		}
	}
	slices.SortFunc(out, func(a, b domain.Property) int {
		return b.CreatedAt.Compare(a.CreatedAt)
	})
	return out, nil
}

func (s *MemoryStore) CreateWorkRequest(_ context.Context, input CreateWorkRequestInput) (domain.WorkRequest, error) {
	if strings.TrimSpace(input.HomeownerUserID) == "" ||
		strings.TrimSpace(input.PropertyID) == "" ||
		strings.TrimSpace(input.Title) == "" ||
		strings.TrimSpace(input.Category) == "" ||
		strings.TrimSpace(input.Area) == "" ||
		strings.TrimSpace(input.Urgency) == "" ||
		strings.TrimSpace(input.Description) == "" {
		return domain.WorkRequest{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.hasPropertyLocked(input.HomeownerUserID, input.PropertyID) {
		return domain.WorkRequest{}, ErrPropertyNotFound
	}

	request := domain.WorkRequest{
		ID:                newID("req"),
		PropertyID:        strings.TrimSpace(input.PropertyID),
		RequestedByUserID: strings.TrimSpace(input.HomeownerUserID),
		Title:             strings.TrimSpace(input.Title),
		Category:          strings.TrimSpace(input.Category),
		Area:              strings.TrimSpace(input.Area),
		Urgency:           strings.TrimSpace(input.Urgency),
		Description:       strings.TrimSpace(input.Description),
		PreferredTiming:   strings.TrimSpace(input.PreferredTiming),
		Status:            domain.WorkRequestStatusNew,
		Attachments:       []domain.Attachment{},
		CreatedAt:         time.Now().UTC(),
	}

	s.workRequests = append(s.workRequests, request)
	return request, nil
}

func (s *MemoryStore) ListWorkRequests(_ context.Context, homeownerUserID string) ([]domain.WorkRequest, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	out := make([]domain.WorkRequest, 0)
	for _, workRequest := range s.workRequests {
		if workRequest.RequestedByUserID == homeownerUserID {
			workRequest.Attachments = s.listWorkRequestAttachmentsLocked(workRequest.ID)
			workRequest.GuestEstimateCount = s.guestEstimateCountLocked(workRequest.ID)
			out = append(out, workRequest)
		}
	}
	slices.SortFunc(out, func(a, b domain.WorkRequest) int {
		return b.CreatedAt.Compare(a.CreatedAt)
	})
	return out, nil
}

func (s *MemoryStore) CreateWorkRequestAttachment(_ context.Context, input CreateWorkRequestAttachmentInput) (domain.Attachment, error) {
	if strings.TrimSpace(input.HomeownerUserID) == "" || strings.TrimSpace(input.WorkRequestID) == "" ||
		strings.TrimSpace(input.StorageKey) == "" || strings.TrimSpace(input.FileName) == "" ||
		strings.TrimSpace(input.ContentType) == "" || input.SizeBytes <= 0 || strings.TrimSpace(input.SHA256) == "" {
		return domain.Attachment{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	owned := false
	for _, request := range s.workRequests {
		if request.ID == strings.TrimSpace(input.WorkRequestID) && request.RequestedByUserID == strings.TrimSpace(input.HomeownerUserID) {
			owned = true
			break
		}
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
	s.attachments = append(s.attachments, attachment)
	return attachment, nil
}

func (s *MemoryStore) ListWorkRequestAttachments(_ context.Context, homeownerUserID string, workRequestID string) ([]domain.Attachment, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	owned := false
	for _, request := range s.workRequests {
		if request.ID == strings.TrimSpace(workRequestID) && request.RequestedByUserID == strings.TrimSpace(homeownerUserID) {
			owned = true
			break
		}
	}
	if !owned {
		return nil, ErrWorkRequestNotFound
	}
	return s.listWorkRequestAttachmentsLocked(strings.TrimSpace(workRequestID)), nil
}

func (s *MemoryStore) GetWorkRequestAttachment(_ context.Context, homeownerUserID string, workRequestID string, attachmentID string) (domain.Attachment, error) {
	attachments, err := s.ListWorkRequestAttachments(context.Background(), homeownerUserID, workRequestID)
	if err != nil {
		return domain.Attachment{}, err
	}
	for _, attachment := range attachments {
		if attachment.ID == strings.TrimSpace(attachmentID) {
			return attachment, nil
		}
	}
	return domain.Attachment{}, ErrAttachmentNotFound
}

func (s *MemoryStore) GetWorkRequestAttachmentForContractor(_ context.Context, contractorUserID string, workRequestID string, attachmentID string) (domain.Attachment, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	workRequest, ok := s.workRequestByIDLocked(strings.TrimSpace(workRequestID))
	if !ok {
		return domain.Attachment{}, ErrAttachmentNotFound
	}
	authorized := workRequest.Status != domain.WorkRequestStatusConverted && workRequest.Status != domain.WorkRequestStatusDeclined
	if !authorized {
		for _, project := range s.projects {
			if project.WorkRequestID == workRequest.ID && s.userBelongsToOrganizationLocked(strings.TrimSpace(contractorUserID), project.ContractorOrgID) {
				authorized = true
				break
			}
		}
	}
	if !authorized {
		return domain.Attachment{}, ErrAttachmentNotFound
	}
	for _, attachment := range s.attachments {
		if attachment.WorkRequestID == workRequest.ID && attachment.ID == strings.TrimSpace(attachmentID) {
			return attachment, nil
		}
	}
	return domain.Attachment{}, ErrAttachmentNotFound
}

func (s *MemoryStore) listWorkRequestAttachmentsLocked(workRequestID string) []domain.Attachment {
	out := make([]domain.Attachment, 0)
	for _, attachment := range s.attachments {
		if attachment.WorkRequestID == workRequestID {
			out = append(out, attachment)
		}
	}
	slices.SortFunc(out, func(a, b domain.Attachment) int { return a.CreatedAt.Compare(b.CreatedAt) })
	return out
}

func (s *MemoryStore) GetHomeownerDashboard(ctx context.Context, homeownerUserID string) (domain.HomeownerDashboard, error) {
	properties, err := s.ListProperties(ctx, homeownerUserID)
	if err != nil {
		return domain.HomeownerDashboard{}, err
	}
	workRequests, err := s.ListWorkRequests(ctx, homeownerUserID)
	if err != nil {
		return domain.HomeownerDashboard{}, err
	}
	projects, err := s.ListProjectsForHomeowner(ctx, homeownerUserID)
	if err != nil {
		return domain.HomeownerDashboard{}, err
	}

	summary := domain.DashboardSummary{
		PropertyCount:           len(properties),
		ScheduledVisitCount:     0,
		ActiveProjectCount:      len(projects),
		OutstandingInvoiceCount: 0,
		RequestsByStatus:        map[string]int{},
	}
	for _, workRequest := range workRequests {
		summary.RequestsByStatus[string(workRequest.Status)]++
		switch workRequest.Status {
		case domain.WorkRequestStatusQuoted:
			summary.PendingApprovalCount++
			summary.OpenRepairCount++
		case domain.WorkRequestStatusDeclined, domain.WorkRequestStatusConverted:
			// terminal from homeowner board perspective
		default:
			summary.OpenRepairCount++
		}
	}
	s.mu.RLock()
	for _, project := range projects {
		latest, ok := s.latestEstimateForProjectLocked(project.Project.ID)
		if ok && latest.Status == domain.EstimateStatusSent {
			summary.PendingApprovalCount++
		}
		summary.ScheduledVisitCount += len(s.listAppointmentsForProjectLocked(project.Project.ID))
		for _, invoice := range s.listInvoicesForProjectLocked(project.Project.ID) {
			if invoice.OutstandingAmountCents > 0 {
				summary.OutstandingInvoiceCount++
			}
		}
	}
	s.mu.RUnlock()

	return domain.HomeownerDashboard{
		HomeownerUserID: homeownerUserID,
		Summary:         summary,
		Properties:      properties,
		WorkRequests:    workRequests,
		ActiveProjects:  projects,
	}, nil
}

func (s *MemoryStore) CreateOrganization(_ context.Context, input CreateOrganizationInput) (domain.Organization, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" || strings.TrimSpace(input.Name) == "" {
		return domain.Organization{}, ErrInvalidInput
	}

	org := domain.Organization{
		ID:        newID("org"),
		Name:      strings.TrimSpace(input.Name),
		Kind:      "contractor",
		CreatedAt: time.Now().UTC(),
	}

	s.mu.Lock()
	defer s.mu.Unlock()
	s.organizations = append(s.organizations, org)
	s.memberships = append(s.memberships, organizationMembership{
		OrganizationID: org.ID,
		UserID:         strings.TrimSpace(input.ContractorUserID),
		Role:           string(domain.RoleContractorAdmin),
		CreatedAt:      time.Now().UTC(),
	})
	return org, nil
}

func (s *MemoryStore) ListOrganizations(_ context.Context, contractorUserID string) ([]domain.Organization, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	orgIDs := make(map[string]struct{})
	for _, membership := range s.memberships {
		if membership.UserID == contractorUserID {
			orgIDs[membership.OrganizationID] = struct{}{}
		}
	}

	out := make([]domain.Organization, 0)
	for _, organization := range s.organizations {
		if _, ok := orgIDs[organization.ID]; ok {
			out = append(out, organization)
		}
	}
	slices.SortFunc(out, func(a, b domain.Organization) int {
		return b.CreatedAt.Compare(a.CreatedAt)
	})
	return out, nil
}

func (s *MemoryStore) GetContractorDashboard(ctx context.Context, contractorUserID string) (domain.ContractorDashboard, error) {
	organizations, err := s.ListOrganizations(ctx, contractorUserID)
	if err != nil {
		return domain.ContractorDashboard{}, err
	}

	s.mu.RLock()
	defer s.mu.RUnlock()

	orgIDs := make(map[string]struct{}, len(organizations))
	for _, organization := range organizations {
		orgIDs[organization.ID] = struct{}{}
	}

	available := make([]domain.ContractorInboxItem, 0)
	for _, workRequest := range s.workRequests {
		if workRequest.Status == domain.WorkRequestStatusConverted || workRequest.Status == domain.WorkRequestStatusDeclined {
			continue
		}
		if property, ok := s.propertyByIDLocked(workRequest.PropertyID); ok {
			workRequest.Attachments = s.listWorkRequestAttachmentsLocked(workRequest.ID)
			workRequest.GuestEstimateCount = s.guestEstimateCountLocked(workRequest.ID)
			available = append(available, domain.ContractorInboxItem{
				WorkRequest: workRequest,
				Property:    property,
			})
		}
	}
	slices.SortFunc(available, func(a, b domain.ContractorInboxItem) int {
		return b.WorkRequest.CreatedAt.Compare(a.WorkRequest.CreatedAt)
	})

	projects := s.listProjectsForContractorLocked(orgIDs)

	summary := domain.ContractorDashboardSummary{
		OrganizationCount:     len(organizations),
		AvailableRequestCount: len(available),
		ActiveProjectCount:    len(projects),
	}
	for _, project := range projects {
		latest, ok := s.latestEstimateForProjectLocked(project.Project.ID)
		if !ok || latest.Status == domain.EstimateStatusRejected || latest.Status == domain.EstimateStatusDraft {
			summary.PendingQuoteCount++
		}
	}

	return domain.ContractorDashboard{
		ContractorUserID:  contractorUserID,
		Summary:           summary,
		Organizations:     organizations,
		AvailableRequests: available,
		ActiveProjects:    projects,
	}, nil
}

func (s *MemoryStore) CreateProjectFromRequest(_ context.Context, input CreateProjectFromRequestInput) (domain.Project, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.OrganizationID) == "" ||
		strings.TrimSpace(input.WorkRequestID) == "" {
		return domain.Project{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.userBelongsToOrganizationLocked(input.ContractorUserID, input.OrganizationID) {
		return domain.Project{}, ErrForbidden
	}

	var requestIndex = -1
	for idx := range s.workRequests {
		if s.workRequests[idx].ID == input.WorkRequestID {
			requestIndex = idx
			break
		}
	}
	if requestIndex < 0 {
		return domain.Project{}, ErrWorkRequestNotFound
	}

	workRequest := s.workRequests[requestIndex]
	if workRequest.Status == domain.WorkRequestStatusConverted || workRequest.Status == domain.WorkRequestStatusDeclined {
		return domain.Project{}, ErrWorkRequestUnavailable
	}

	title := strings.TrimSpace(input.Title)
	if title == "" {
		title = workRequest.Title
	}

	project := domain.Project{
		ID:              newID("proj"),
		PropertyID:      workRequest.PropertyID,
		WorkRequestID:   workRequest.ID,
		ContractorOrgID: input.OrganizationID,
		Title:           title,
		Status:          domain.ProjectStatusDraft,
		CreatedAt:       time.Now().UTC(),
	}

	s.projects = append(s.projects, project)
	s.workRequests[requestIndex].Status = domain.WorkRequestStatusConverted
	return project, nil
}

func (s *MemoryStore) ListProjectsForHomeowner(_ context.Context, homeownerUserID string) ([]domain.ProjectWorkspaceItem, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	out := make([]domain.ProjectWorkspaceItem, 0)
	for _, project := range s.projects {
		property, ok := s.propertyByIDLocked(project.PropertyID)
		if !ok || property.HomeownerUserID != homeownerUserID {
			continue
		}
		out = append(out, s.buildProjectWorkspaceLocked(project, property))
	}
	slices.SortFunc(out, func(a, b domain.ProjectWorkspaceItem) int {
		return b.Project.CreatedAt.Compare(a.Project.CreatedAt)
	})
	return out, nil
}

func (s *MemoryStore) ListProjectsForContractor(ctx context.Context, contractorUserID string) ([]domain.ProjectWorkspaceItem, error) {
	organizations, err := s.ListOrganizations(ctx, contractorUserID)
	if err != nil {
		return nil, err
	}

	orgIDs := make(map[string]struct{}, len(organizations))
	for _, organization := range organizations {
		orgIDs[organization.ID] = struct{}{}
	}

	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.listProjectsForContractorLocked(orgIDs), nil
}

func (s *MemoryStore) GetProjectDetailForHomeowner(_ context.Context, homeownerUserID string, projectID string) (domain.ProjectDetail, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	for _, project := range s.projects {
		if project.ID != projectID {
			continue
		}
		property, ok := s.propertyByIDLocked(project.PropertyID)
		if !ok || property.HomeownerUserID != homeownerUserID {
			return domain.ProjectDetail{}, ErrProjectNotFound
		}
		item := s.buildProjectWorkspaceLocked(project, property)
		estimates := s.listEstimatesForProjectLocked(project.ID)
		appointments := s.listAppointmentsForProjectLocked(project.ID)
		invoices := s.listInvoicesForProjectLocked(project.ID)
		messages := s.listMessagesForProjectLocked(project.ID, false)
		return domain.ProjectDetail{
			ViewerRole:   "homeowner",
			Item:         item,
			Estimates:    estimates,
			Appointments: appointments,
			Invoices:     invoices,
			Messages:     messages,
			Timeline:     buildSyntheticTimeline(item, estimates, appointments, invoices, messages),
		}, nil
	}
	return domain.ProjectDetail{}, ErrProjectNotFound
}

func (s *MemoryStore) GetProjectDetailForContractor(ctx context.Context, contractorUserID string, projectID string) (domain.ProjectDetail, error) {
	organizations, err := s.ListOrganizations(ctx, contractorUserID)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
	orgIDs := make(map[string]struct{}, len(organizations))
	for _, organization := range organizations {
		orgIDs[organization.ID] = struct{}{}
	}

	s.mu.RLock()
	defer s.mu.RUnlock()
	for _, project := range s.projects {
		if project.ID != projectID {
			continue
		}
		if _, ok := orgIDs[project.ContractorOrgID]; !ok {
			return domain.ProjectDetail{}, ErrProjectNotFound
		}
		property, ok := s.propertyByIDLocked(project.PropertyID)
		if !ok {
			return domain.ProjectDetail{}, ErrProjectNotFound
		}
		item := s.buildProjectWorkspaceLocked(project, property)
		estimates := s.listEstimatesForProjectLocked(project.ID)
		appointments := s.listAppointmentsForProjectLocked(project.ID)
		invoices := s.listInvoicesForProjectLocked(project.ID)
		messages := s.listMessagesForProjectLocked(project.ID, true)
		return domain.ProjectDetail{
			ViewerRole:   "contractor",
			Item:         item,
			Estimates:    estimates,
			Appointments: appointments,
			Invoices:     invoices,
			Messages:     messages,
			Timeline:     buildSyntheticTimeline(item, estimates, appointments, invoices, messages),
		}, nil
	}
	return domain.ProjectDetail{}, ErrProjectNotFound
}

func (s *MemoryStore) CreateEstimate(_ context.Context, input CreateEstimateInput) (domain.Estimate, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Summary) == "" ||
		len(input.LineItems) == 0 {
		return domain.Estimate{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	project, ok := s.projectByIDLocked(input.ProjectID)
	if !ok {
		return domain.Estimate{}, ErrProjectNotFound
	}
	if !s.userBelongsToOrganizationLocked(input.ContractorUserID, project.ContractorOrgID) {
		return domain.Estimate{}, ErrForbidden
	}

	total := int64(0)
	lineItems := make([]domain.EstimateLineItem, 0, len(input.LineItems))
	for idx, item := range input.LineItems {
		if strings.TrimSpace(item.Label) == "" || item.AmountCents <= 0 {
			return domain.Estimate{}, ErrInvalidInput
		}
		total += item.AmountCents
		lineItems = append(lineItems, domain.EstimateLineItem{
			ID:          newID("eli"),
			Label:       strings.TrimSpace(item.Label),
			AmountCents: item.AmountCents,
			Position:    idx,
		})
	}
	if total <= 0 || input.DepositAmountCents < 0 || input.DepositAmountCents > total {
		return domain.Estimate{}, ErrInvalidInput
	}

	now := time.Now().UTC()
	estimate := domain.Estimate{
		ID:                 newID("est"),
		ProjectID:          project.ID,
		ContractorOrgID:    project.ContractorOrgID,
		Summary:            strings.TrimSpace(input.Summary),
		Notes:              strings.TrimSpace(input.Notes),
		DepositAmountCents: input.DepositAmountCents,
		TotalAmountCents:   total,
		Status:             domain.EstimateStatusSent,
		LineItems:          lineItems,
		CreatedAt:          now,
		UpdatedAt:          now,
		SentAt:             &now,
	}

	s.estimates = append(s.estimates, estimate)
	return estimate, nil
}

func (s *MemoryStore) ApproveEstimate(_ context.Context, homeownerUserID string, projectID string, estimateID string) (domain.Estimate, error) {
	return s.decideEstimate(homeownerUserID, projectID, estimateID, domain.EstimateStatusApproved)
}

func (s *MemoryStore) RejectEstimate(_ context.Context, homeownerUserID string, projectID string, estimateID string) (domain.Estimate, error) {
	return s.decideEstimate(homeownerUserID, projectID, estimateID, domain.EstimateStatusRejected)
}

func (s *MemoryStore) ListEstimatesForProject(_ context.Context, projectID string) ([]domain.Estimate, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.listEstimatesForProjectLocked(projectID), nil
}

func (s *MemoryStore) CreateAppointment(_ context.Context, input CreateAppointmentInput) (domain.Appointment, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Title) == "" ||
		input.StartsAt.IsZero() ||
		input.EndsAt.IsZero() ||
		!input.EndsAt.After(input.StartsAt) {
		return domain.Appointment{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	project, ok := s.projectByIDLocked(input.ProjectID)
	if !ok {
		return domain.Appointment{}, ErrProjectNotFound
	}
	if !s.userBelongsToOrganizationLocked(input.ContractorUserID, project.ContractorOrgID) {
		return domain.Appointment{}, ErrForbidden
	}

	appointment := domain.Appointment{
		ID:              newID("apt"),
		ProjectID:       project.ID,
		ContractorOrgID: project.ContractorOrgID,
		Title:           strings.TrimSpace(input.Title),
		Notes:           strings.TrimSpace(input.Notes),
		StartsAt:        input.StartsAt.UTC(),
		EndsAt:          input.EndsAt.UTC(),
		Status:          domain.AppointmentStatusScheduled,
		CreatedAt:       time.Now().UTC(),
	}

	s.appointments = append(s.appointments, appointment)
	return appointment, nil
}

func (s *MemoryStore) ListAppointmentsForProject(_ context.Context, projectID string) ([]domain.Appointment, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.listAppointmentsForProjectLocked(projectID), nil
}

func (s *MemoryStore) CreateInvoice(_ context.Context, input CreateInvoiceInput) (domain.Invoice, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Summary) == "" ||
		input.AmountCents <= 0 ||
		input.DueAt.IsZero() {
		return domain.Invoice{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	project, ok := s.projectByIDLocked(input.ProjectID)
	if !ok {
		return domain.Invoice{}, ErrProjectNotFound
	}
	if !s.userBelongsToOrganizationLocked(input.ContractorUserID, project.ContractorOrgID) {
		return domain.Invoice{}, ErrForbidden
	}

	now := time.Now().UTC()
	invoice := domain.Invoice{
		ID:                     newID("inv"),
		ProjectID:              project.ID,
		ContractorOrgID:        project.ContractorOrgID,
		Summary:                strings.TrimSpace(input.Summary),
		Notes:                  strings.TrimSpace(input.Notes),
		AmountCents:            input.AmountCents,
		AmountPaidCents:        0,
		OutstandingAmountCents: input.AmountCents,
		Status:                 domain.InvoiceStatusSent,
		DueAt:                  input.DueAt.UTC(),
		Payments:               []domain.Payment{},
		CreatedAt:              now,
		UpdatedAt:              now,
		IssuedAt:               now,
	}

	s.invoices = append(s.invoices, invoice)
	return invoice, nil
}

func (s *MemoryStore) RecordInvoicePayment(_ context.Context, input RecordInvoicePaymentInput) (domain.Invoice, error) {
	if strings.TrimSpace(input.HomeownerUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.InvoiceID) == "" ||
		input.AmountCents <= 0 {
		return domain.Invoice{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	project, ok := s.projectByIDLocked(input.ProjectID)
	if !ok {
		return domain.Invoice{}, ErrProjectNotFound
	}
	property, ok := s.propertyByIDLocked(project.PropertyID)
	if !ok || property.HomeownerUserID != strings.TrimSpace(input.HomeownerUserID) {
		return domain.Invoice{}, ErrProjectNotFound
	}

	for idx := range s.invoices {
		if s.invoices[idx].ID != input.InvoiceID || s.invoices[idx].ProjectID != input.ProjectID {
			continue
		}
		if s.invoices[idx].OutstandingAmountCents <= 0 || s.invoices[idx].Status == domain.InvoiceStatusPaid {
			return domain.Invoice{}, ErrInvoiceUnavailable
		}
		if input.AmountCents > s.invoices[idx].OutstandingAmountCents {
			return domain.Invoice{}, ErrInvalidInput
		}

		now := time.Now().UTC()
		payment := domain.Payment{
			ID:          newID("pay"),
			InvoiceID:   s.invoices[idx].ID,
			PayerUserID: strings.TrimSpace(input.HomeownerUserID),
			AmountCents: input.AmountCents,
			Note:        strings.TrimSpace(input.Note),
			PaidAt:      now,
			CreatedAt:   now,
		}
		s.invoices[idx].Payments = append(s.invoices[idx].Payments, payment)
		s.invoices[idx].AmountPaidCents += input.AmountCents
		s.invoices[idx].OutstandingAmountCents = s.invoices[idx].AmountCents - s.invoices[idx].AmountPaidCents
		s.invoices[idx].UpdatedAt = now
		if s.invoices[idx].OutstandingAmountCents == 0 {
			s.invoices[idx].Status = domain.InvoiceStatusPaid
			s.invoices[idx].PaidAt = &now
		} else {
			s.invoices[idx].Status = domain.InvoiceStatusPartiallyPaid
			s.invoices[idx].PaidAt = nil
		}
		return s.invoices[idx], nil
	}

	return domain.Invoice{}, ErrInvoiceNotFound
}

func (s *MemoryStore) ListInvoicesForProject(_ context.Context, projectID string) ([]domain.Invoice, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.listInvoicesForProjectLocked(projectID), nil
}

func (s *MemoryStore) CreateProjectMessage(_ context.Context, input CreateProjectMessageInput) (domain.ProjectMessage, error) {
	if strings.TrimSpace(input.AuthorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Body) == "" {
		return domain.ProjectMessage{}, ErrInvalidInput
	}

	if input.Visibility != domain.MessageVisibilityShared && input.Visibility != domain.MessageVisibilityInternal {
		return domain.ProjectMessage{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	project, ok := s.projectByIDLocked(input.ProjectID)
	if !ok {
		return domain.ProjectMessage{}, ErrProjectNotFound
	}

	switch input.AuthorRole {
	case domain.RoleHomeowner:
		property, ok := s.propertyByIDLocked(project.PropertyID)
		if !ok || property.HomeownerUserID != strings.TrimSpace(input.AuthorUserID) {
			return domain.ProjectMessage{}, ErrProjectNotFound
		}
		if input.Visibility != domain.MessageVisibilityShared {
			return domain.ProjectMessage{}, ErrForbidden
		}
	case domain.RoleContractor, domain.RoleContractorAdmin, domain.RoleCrewMember:
		if !s.userBelongsToOrganizationLocked(strings.TrimSpace(input.AuthorUserID), project.ContractorOrgID) {
			return domain.ProjectMessage{}, ErrForbidden
		}
	default:
		return domain.ProjectMessage{}, ErrForbidden
	}

	message := domain.ProjectMessage{
		ID:           newID("msg"),
		ProjectID:    project.ID,
		AuthorUserID: strings.TrimSpace(input.AuthorUserID),
		AuthorRole:   input.AuthorRole,
		Visibility:   input.Visibility,
		Body:         strings.TrimSpace(input.Body),
		CreatedAt:    time.Now().UTC(),
	}

	s.messages = append(s.messages, message)
	return message, nil
}

func (s *MemoryStore) hasPropertyLocked(homeownerUserID string, propertyID string) bool {
	for _, property := range s.properties {
		if property.ID == propertyID && property.HomeownerUserID == homeownerUserID {
			return true
		}
	}
	return false
}

func (s *MemoryStore) propertyByIDLocked(propertyID string) (domain.Property, bool) {
	for _, property := range s.properties {
		if property.ID == propertyID {
			return property, true
		}
	}
	return domain.Property{}, false
}

func (s *MemoryStore) userBelongsToOrganizationLocked(userID string, organizationID string) bool {
	for _, membership := range s.memberships {
		if membership.UserID == userID && membership.OrganizationID == organizationID {
			return true
		}
	}
	return false
}

func (s *MemoryStore) workRequestByIDLocked(workRequestID string) (domain.WorkRequest, bool) {
	for _, workRequest := range s.workRequests {
		if workRequest.ID == workRequestID {
			return workRequest, true
		}
	}
	return domain.WorkRequest{}, false
}

func (s *MemoryStore) projectByIDLocked(projectID string) (domain.Project, bool) {
	for _, project := range s.projects {
		if project.ID == projectID {
			return project, true
		}
	}
	return domain.Project{}, false
}

func (s *MemoryStore) latestEstimateForProjectLocked(projectID string) (domain.Estimate, bool) {
	estimates := s.listEstimatesForProjectLocked(projectID)
	if len(estimates) == 0 {
		return domain.Estimate{}, false
	}
	return estimates[0], true
}

func (s *MemoryStore) listEstimatesForProjectLocked(projectID string) []domain.Estimate {
	out := make([]domain.Estimate, 0)
	for _, estimate := range s.estimates {
		if estimate.ProjectID == projectID {
			out = append(out, estimate)
		}
	}
	slices.SortFunc(out, func(a, b domain.Estimate) int {
		return b.CreatedAt.Compare(a.CreatedAt)
	})
	return out
}

func (s *MemoryStore) listAppointmentsForProjectLocked(projectID string) []domain.Appointment {
	out := make([]domain.Appointment, 0)
	for _, appointment := range s.appointments {
		if appointment.ProjectID == projectID {
			out = append(out, appointment)
		}
	}
	slices.SortFunc(out, func(a, b domain.Appointment) int {
		if compare := a.StartsAt.Compare(b.StartsAt); compare != 0 {
			return compare
		}
		return a.CreatedAt.Compare(b.CreatedAt)
	})
	return out
}

func (s *MemoryStore) listInvoicesForProjectLocked(projectID string) []domain.Invoice {
	out := make([]domain.Invoice, 0)
	for _, invoice := range s.invoices {
		if invoice.ProjectID != projectID {
			continue
		}
		if len(invoice.Payments) > 1 {
			slices.SortFunc(invoice.Payments, func(a, b domain.Payment) int {
				if compare := b.PaidAt.Compare(a.PaidAt); compare != 0 {
					return compare
				}
				return b.CreatedAt.Compare(a.CreatedAt)
			})
		}
		out = append(out, invoice)
	}
	slices.SortFunc(out, func(a, b domain.Invoice) int {
		return b.CreatedAt.Compare(a.CreatedAt)
	})
	return out
}

func (s *MemoryStore) listMessagesForProjectLocked(projectID string, includeInternal bool) []domain.ProjectMessage {
	out := make([]domain.ProjectMessage, 0)
	for _, message := range s.messages {
		if message.ProjectID != projectID {
			continue
		}
		if !includeInternal && message.Visibility == domain.MessageVisibilityInternal {
			continue
		}
		out = append(out, message)
	}
	slices.SortFunc(out, func(a, b domain.ProjectMessage) int {
		if compare := a.CreatedAt.Compare(b.CreatedAt); compare != 0 {
			return compare
		}
		return strings.Compare(a.ID, b.ID)
	})
	return out
}

func (s *MemoryStore) buildProjectWorkspaceLocked(project domain.Project, property domain.Property) domain.ProjectWorkspaceItem {
	item := domain.ProjectWorkspaceItem{
		Project:  project,
		Property: property,
	}
	if project.WorkRequestID != "" {
		if workRequest, ok := s.workRequestByIDLocked(project.WorkRequestID); ok {
			workRequest.Attachments = s.listWorkRequestAttachmentsLocked(workRequest.ID)
			workRequest.GuestEstimateCount = s.guestEstimateCountLocked(workRequest.ID)
			item.WorkRequest = &workRequest
		}
	}
	return item
}

func (s *MemoryStore) listProjectsForContractorLocked(orgIDs map[string]struct{}) []domain.ProjectWorkspaceItem {
	projects := make([]domain.ProjectWorkspaceItem, 0)
	for _, project := range s.projects {
		if _, ok := orgIDs[project.ContractorOrgID]; !ok {
			continue
		}
		if property, ok := s.propertyByIDLocked(project.PropertyID); ok {
			projects = append(projects, s.buildProjectWorkspaceLocked(project, property))
		}
	}
	slices.SortFunc(projects, func(a, b domain.ProjectWorkspaceItem) int {
		return b.Project.CreatedAt.Compare(a.Project.CreatedAt)
	})
	return projects
}

func (s *MemoryStore) decideEstimate(homeownerUserID string, projectID string, estimateID string, status domain.EstimateStatus) (domain.Estimate, error) {
	if strings.TrimSpace(homeownerUserID) == "" || strings.TrimSpace(projectID) == "" || strings.TrimSpace(estimateID) == "" {
		return domain.Estimate{}, ErrInvalidInput
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	project, ok := s.projectByIDLocked(projectID)
	if !ok {
		return domain.Estimate{}, ErrProjectNotFound
	}
	property, ok := s.propertyByIDLocked(project.PropertyID)
	if !ok || property.HomeownerUserID != homeownerUserID {
		return domain.Estimate{}, ErrProjectNotFound
	}

	for idx := range s.estimates {
		if s.estimates[idx].ID != estimateID || s.estimates[idx].ProjectID != projectID {
			continue
		}
		if s.estimates[idx].Status != domain.EstimateStatusSent {
			return domain.Estimate{}, ErrEstimateUnavailable
		}
		now := time.Now().UTC()
		s.estimates[idx].Status = status
		s.estimates[idx].UpdatedAt = now
		s.estimates[idx].DecidedAt = &now
		for projectIdx := range s.projects {
			if s.projects[projectIdx].ID == projectID {
				if status == domain.EstimateStatusApproved {
					s.projects[projectIdx].Status = domain.ProjectStatusApproved
				}
				break
			}
		}
		return s.estimates[idx], nil
	}
	return domain.Estimate{}, ErrEstimateNotFound
}

func newID(prefix string) string {
	var buf [8]byte
	if _, err := rand.Read(buf[:]); err != nil {
		return prefix + "-" + strconvTime()
	}
	return prefix + "-" + hex.EncodeToString(buf[:])
}

func strconvTime() string {
	return strings.ReplaceAll(time.Now().UTC().Format("20060102150405.000000000"), ".", "")
}

func defaultString(value string, fallback string) string {
	if strings.TrimSpace(value) == "" {
		return fallback
	}
	return value
}
