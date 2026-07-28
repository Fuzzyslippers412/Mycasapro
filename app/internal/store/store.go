package store

import (
	"context"
	"errors"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

var (
	ErrUserNotFound           = errors.New("user not found")
	ErrUserExists             = errors.New("user already exists")
	ErrSessionNotFound        = errors.New("session not found")
	ErrPropertyNotFound       = errors.New("property not found")
	ErrInvalidInput           = errors.New("invalid input")
	ErrOrganizationNotFound   = errors.New("organization not found")
	ErrWorkRequestNotFound    = errors.New("work request not found")
	ErrWorkRequestUnavailable = errors.New("work request unavailable")
	ErrProjectNotFound        = errors.New("project not found")
	ErrEstimateNotFound       = errors.New("estimate not found")
	ErrEstimateUnavailable    = errors.New("estimate unavailable")
	ErrInvoiceNotFound        = errors.New("invoice not found")
	ErrInvoiceUnavailable     = errors.New("invoice unavailable")
	ErrAttachmentNotFound     = errors.New("attachment not found")
	ErrInviteNotFound         = errors.New("invite not found")
	ErrInviteExpired          = errors.New("invite expired")
	ErrInviteRevoked          = errors.New("invite revoked")
	ErrForbidden              = errors.New("forbidden")
)

type CreateUserInput struct {
	Email        string
	DisplayName  string
	Role         domain.Role
	PasswordHash string
}

type UserCredentials struct {
	User         domain.User
	PasswordHash string
}

type CreateSessionInput struct {
	UserID    string
	TokenHash string
	ExpiresAt time.Time
}

type CreatePropertyInput struct {
	HomeownerUserID string
	Label           string
	AddressLine1    string
	AddressLine2    string
	City            string
	Region          string
	PostalCode      string
	CountryCode     string
}

type CreateWorkRequestInput struct {
	HomeownerUserID string
	PropertyID      string
	Title           string
	Category        string
	Area            string
	Urgency         string
	Description     string
	PreferredTiming string
}

type CreateWorkRequestAttachmentInput struct {
	HomeownerUserID string
	WorkRequestID   string
	StorageKey      string
	FileName        string
	ContentType     string
	SizeBytes       int64
	SHA256          string
}

type CreateWorkRequestInviteInput struct {
	HomeownerUserID string
	WorkRequestID   string
	TokenHash       string
	ExpiresAt       time.Time
}

type GuestEstimateLineItemInput struct {
	Label       string
	AmountCents int64
}

type CreateGuestEstimateInput struct {
	TokenHash       string
	ContractorName  string
	BusinessName    string
	Email           string
	Summary         string
	Notes           string
	AvailableTiming string
	LineItems       []GuestEstimateLineItemInput
	Now             time.Time
}

type CreateOrganizationInput struct {
	ContractorUserID string
	Name             string
}

type CreateProjectFromRequestInput struct {
	ContractorUserID string
	OrganizationID   string
	WorkRequestID    string
	Title            string
}

type EstimateLineItemInput struct {
	Label       string
	AmountCents int64
}

type CreateEstimateInput struct {
	ContractorUserID   string
	ProjectID          string
	Summary            string
	Notes              string
	DepositAmountCents int64
	LineItems          []EstimateLineItemInput
}

type CreateAppointmentInput struct {
	ContractorUserID string
	ProjectID        string
	Title            string
	Notes            string
	StartsAt         time.Time
	EndsAt           time.Time
}

type CreateInvoiceInput struct {
	ContractorUserID string
	ProjectID        string
	Summary          string
	Notes            string
	AmountCents      int64
	DueAt            time.Time
}

type RecordInvoicePaymentInput struct {
	HomeownerUserID string
	ProjectID       string
	InvoiceID       string
	AmountCents     int64
	Note            string
}

type CreateProjectMessageInput struct {
	AuthorUserID string
	AuthorRole   domain.Role
	ProjectID    string
	Visibility   domain.MessageVisibility
	Body         string
}

type Store interface {
	CreateUser(context.Context, CreateUserInput) (domain.User, error)
	GetUserByID(context.Context, string) (domain.User, error)
	GetUserCredentialsByEmail(context.Context, string) (UserCredentials, error)
	CreateSession(context.Context, CreateSessionInput) error
	GetUserBySessionTokenHash(context.Context, string, time.Time) (domain.User, error)
	DeleteSession(context.Context, string) error
	CreateProperty(context.Context, CreatePropertyInput) (domain.Property, error)
	ListProperties(context.Context, string) ([]domain.Property, error)
	CreateWorkRequest(context.Context, CreateWorkRequestInput) (domain.WorkRequest, error)
	ListWorkRequests(context.Context, string) ([]domain.WorkRequest, error)
	CreateWorkRequestAttachment(context.Context, CreateWorkRequestAttachmentInput) (domain.Attachment, error)
	ListWorkRequestAttachments(context.Context, string, string) ([]domain.Attachment, error)
	GetWorkRequestAttachment(context.Context, string, string, string) (domain.Attachment, error)
	GetWorkRequestAttachmentForContractor(context.Context, string, string, string) (domain.Attachment, error)
	CreateWorkRequestInvite(context.Context, CreateWorkRequestInviteInput) (domain.WorkRequestInvite, error)
	ListWorkRequestInvites(context.Context, string, string) ([]domain.WorkRequestInvite, error)
	RevokeWorkRequestInvite(context.Context, string, string, string, time.Time) (domain.WorkRequestInvite, error)
	GetInviteTask(context.Context, string, time.Time) (domain.InviteTask, error)
	GetWorkRequestAttachmentForInvite(context.Context, string, string, time.Time) (domain.Attachment, error)
	CreateGuestEstimate(context.Context, CreateGuestEstimateInput) (domain.GuestEstimate, error)
	ListGuestEstimates(context.Context, string, string) ([]domain.GuestEstimate, error)
	GetHomeownerDashboard(context.Context, string) (domain.HomeownerDashboard, error)
	CreateOrganization(context.Context, CreateOrganizationInput) (domain.Organization, error)
	ListOrganizations(context.Context, string) ([]domain.Organization, error)
	GetContractorDashboard(context.Context, string) (domain.ContractorDashboard, error)
	CreateProjectFromRequest(context.Context, CreateProjectFromRequestInput) (domain.Project, error)
	ListProjectsForHomeowner(context.Context, string) ([]domain.ProjectWorkspaceItem, error)
	ListProjectsForContractor(context.Context, string) ([]domain.ProjectWorkspaceItem, error)
	GetProjectDetailForHomeowner(context.Context, string, string) (domain.ProjectDetail, error)
	GetProjectDetailForContractor(context.Context, string, string) (domain.ProjectDetail, error)
	CreateEstimate(context.Context, CreateEstimateInput) (domain.Estimate, error)
	ApproveEstimate(context.Context, string, string, string) (domain.Estimate, error)
	RejectEstimate(context.Context, string, string, string) (domain.Estimate, error)
	ListEstimatesForProject(context.Context, string) ([]domain.Estimate, error)
	CreateAppointment(context.Context, CreateAppointmentInput) (domain.Appointment, error)
	ListAppointmentsForProject(context.Context, string) ([]domain.Appointment, error)
	CreateInvoice(context.Context, CreateInvoiceInput) (domain.Invoice, error)
	RecordInvoicePayment(context.Context, RecordInvoicePaymentInput) (domain.Invoice, error)
	ListInvoicesForProject(context.Context, string) ([]domain.Invoice, error)
	CreateProjectMessage(context.Context, CreateProjectMessageInput) (domain.ProjectMessage, error)
}
