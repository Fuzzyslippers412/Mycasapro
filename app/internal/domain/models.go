package domain

import "time"

type Role string

const (
	RoleHomeowner       Role = "homeowner"
	RoleContractor      Role = "contractor"
	RoleContractorAdmin Role = "contractor_admin"
	RoleCrewMember      Role = "crew_member"
	RolePlatformAdmin   Role = "platform_admin"
)

type User struct {
	ID          string    `json:"id"`
	Email       string    `json:"email"`
	DisplayName string    `json:"display_name"`
	Role        Role      `json:"role"`
	CreatedAt   time.Time `json:"created_at"`
}

type Organization struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Kind      string    `json:"kind"`
	CreatedAt time.Time `json:"created_at"`
}

type Property struct {
	ID              string    `json:"id"`
	HomeownerUserID string    `json:"homeowner_user_id"`
	Label           string    `json:"label"`
	AddressLine1    string    `json:"address_line_1"`
	AddressLine2    string    `json:"address_line_2,omitempty"`
	City            string    `json:"city"`
	Region          string    `json:"region"`
	PostalCode      string    `json:"postal_code"`
	CountryCode     string    `json:"country_code"`
	CreatedAt       time.Time `json:"created_at"`
}

type WorkRequestStatus string

const (
	WorkRequestStatusNew       WorkRequestStatus = "new"
	WorkRequestStatusReviewing WorkRequestStatus = "reviewing"
	WorkRequestStatusQuoted    WorkRequestStatus = "quoted"
	WorkRequestStatusApproved  WorkRequestStatus = "approved"
	WorkRequestStatusDeclined  WorkRequestStatus = "declined"
	WorkRequestStatusConverted WorkRequestStatus = "converted"
)

type WorkRequest struct {
	ID                 string            `json:"id"`
	PropertyID         string            `json:"property_id"`
	RequestedByUserID  string            `json:"requested_by_user_id"`
	Title              string            `json:"title"`
	Category           string            `json:"category"`
	Area               string            `json:"area"`
	Urgency            string            `json:"urgency"`
	Description        string            `json:"description"`
	PreferredTiming    string            `json:"preferred_timing,omitempty"`
	Status             WorkRequestStatus `json:"status"`
	Attachments        []Attachment      `json:"attachments"`
	GuestEstimateCount int               `json:"guest_estimate_count"`
	CreatedAt          time.Time         `json:"created_at"`
}

type WorkRequestInvite struct {
	ID              string     `json:"id"`
	WorkRequestID   string     `json:"work_request_id"`
	HomeownerUserID string     `json:"homeowner_user_id"`
	ExpiresAt       time.Time  `json:"expires_at"`
	RevokedAt       *time.Time `json:"revoked_at,omitempty"`
	CreatedAt       time.Time  `json:"created_at"`
}

type InviteProperty struct {
	Label       string `json:"label"`
	City        string `json:"city"`
	Region      string `json:"region"`
	CountryCode string `json:"country_code"`
}

type InviteTask struct {
	Invite      WorkRequestInvite `json:"invite"`
	WorkRequest WorkRequest       `json:"work_request"`
	Property    InviteProperty    `json:"property"`
}

type GuestEstimateLineItem struct {
	ID              string `json:"id"`
	GuestEstimateID string `json:"guest_estimate_id"`
	Label           string `json:"label"`
	AmountCents     int64  `json:"amount_cents"`
	Position        int    `json:"position"`
}

type GuestEstimate struct {
	ID               string                  `json:"id"`
	InviteID         string                  `json:"invite_id"`
	WorkRequestID    string                  `json:"work_request_id"`
	ContractorName   string                  `json:"contractor_name"`
	BusinessName     string                  `json:"business_name,omitempty"`
	Email            string                  `json:"email"`
	Summary          string                  `json:"summary"`
	Notes            string                  `json:"notes,omitempty"`
	AvailableTiming  string                  `json:"available_timing,omitempty"`
	TotalAmountCents int64                   `json:"total_amount_cents"`
	LineItems        []GuestEstimateLineItem `json:"line_items"`
	CreatedAt        time.Time               `json:"created_at"`
}

type Attachment struct {
	ID               string    `json:"id"`
	WorkRequestID    string    `json:"work_request_id,omitempty"`
	ProjectID        string    `json:"project_id,omitempty"`
	UploadedByUserID string    `json:"uploaded_by_user_id"`
	FileName         string    `json:"file_name"`
	ContentType      string    `json:"content_type"`
	SizeBytes        int64     `json:"size_bytes"`
	SHA256           string    `json:"sha256"`
	StorageKey       string    `json:"-"`
	CreatedAt        time.Time `json:"created_at"`
}

type ProjectStatus string

const (
	ProjectStatusDraft      ProjectStatus = "draft"
	ProjectStatusApproved   ProjectStatus = "approved"
	ProjectStatusScheduled  ProjectStatus = "scheduled"
	ProjectStatusInProgress ProjectStatus = "in_progress"
	ProjectStatusBlocked    ProjectStatus = "blocked"
	ProjectStatusCompleted  ProjectStatus = "completed"
	ProjectStatusClosed     ProjectStatus = "closed"
	ProjectStatusCancelled  ProjectStatus = "cancelled"
)

type Project struct {
	ID              string        `json:"id"`
	PropertyID      string        `json:"property_id"`
	WorkRequestID   string        `json:"work_request_id"`
	ContractorOrgID string        `json:"contractor_org_id"`
	Title           string        `json:"title"`
	Status          ProjectStatus `json:"status"`
	CreatedAt       time.Time     `json:"created_at"`
}

type DashboardSummary struct {
	PropertyCount           int            `json:"property_count"`
	OpenRepairCount         int            `json:"open_repair_count"`
	PendingApprovalCount    int            `json:"pending_approval_count"`
	ScheduledVisitCount     int            `json:"scheduled_visit_count"`
	ActiveProjectCount      int            `json:"active_project_count"`
	OutstandingInvoiceCount int            `json:"outstanding_invoice_count"`
	RequestsByStatus        map[string]int `json:"requests_by_status"`
}

type HomeownerDashboard struct {
	HomeownerUserID string                 `json:"homeowner_user_id"`
	Summary         DashboardSummary       `json:"summary"`
	Properties      []Property             `json:"properties"`
	WorkRequests    []WorkRequest          `json:"work_requests"`
	ActiveProjects  []ProjectWorkspaceItem `json:"active_projects"`
}

type ContractorInboxItem struct {
	WorkRequest WorkRequest `json:"work_request"`
	Property    Property    `json:"property"`
}

type ProjectWorkspaceItem struct {
	Project     Project      `json:"project"`
	Property    Property     `json:"property"`
	WorkRequest *WorkRequest `json:"work_request,omitempty"`
}

type EstimateStatus string

const (
	EstimateStatusDraft    EstimateStatus = "draft"
	EstimateStatusSent     EstimateStatus = "sent"
	EstimateStatusApproved EstimateStatus = "approved"
	EstimateStatusRejected EstimateStatus = "rejected"
)

type EstimateLineItem struct {
	ID          string `json:"id"`
	Label       string `json:"label"`
	AmountCents int64  `json:"amount_cents"`
	Position    int    `json:"position"`
}

type Estimate struct {
	ID                 string             `json:"id"`
	ProjectID          string             `json:"project_id"`
	ContractorOrgID    string             `json:"contractor_org_id"`
	Summary            string             `json:"summary"`
	Notes              string             `json:"notes,omitempty"`
	DepositAmountCents int64              `json:"deposit_amount_cents"`
	TotalAmountCents   int64              `json:"total_amount_cents"`
	Status             EstimateStatus     `json:"status"`
	LineItems          []EstimateLineItem `json:"line_items"`
	CreatedAt          time.Time          `json:"created_at"`
	UpdatedAt          time.Time          `json:"updated_at"`
	SentAt             *time.Time         `json:"sent_at,omitempty"`
	DecidedAt          *time.Time         `json:"decided_at,omitempty"`
}

type AppointmentStatus string

const (
	AppointmentStatusScheduled AppointmentStatus = "scheduled"
	AppointmentStatusCompleted AppointmentStatus = "completed"
	AppointmentStatusCancelled AppointmentStatus = "cancelled"
)

type Appointment struct {
	ID              string            `json:"id"`
	ProjectID       string            `json:"project_id"`
	ContractorOrgID string            `json:"contractor_org_id"`
	Title           string            `json:"title"`
	Notes           string            `json:"notes,omitempty"`
	StartsAt        time.Time         `json:"starts_at"`
	EndsAt          time.Time         `json:"ends_at"`
	Status          AppointmentStatus `json:"status"`
	CreatedAt       time.Time         `json:"created_at"`
}

type InvoiceStatus string

const (
	InvoiceStatusSent          InvoiceStatus = "sent"
	InvoiceStatusPartiallyPaid InvoiceStatus = "partially_paid"
	InvoiceStatusPaid          InvoiceStatus = "paid"
)

type Payment struct {
	ID          string    `json:"id"`
	InvoiceID   string    `json:"invoice_id"`
	PayerUserID string    `json:"payer_user_id"`
	AmountCents int64     `json:"amount_cents"`
	Note        string    `json:"note,omitempty"`
	PaidAt      time.Time `json:"paid_at"`
	CreatedAt   time.Time `json:"created_at"`
}

type Invoice struct {
	ID                     string        `json:"id"`
	ProjectID              string        `json:"project_id"`
	ContractorOrgID        string        `json:"contractor_org_id"`
	Summary                string        `json:"summary"`
	Notes                  string        `json:"notes,omitempty"`
	AmountCents            int64         `json:"amount_cents"`
	AmountPaidCents        int64         `json:"amount_paid_cents"`
	OutstandingAmountCents int64         `json:"outstanding_amount_cents"`
	Status                 InvoiceStatus `json:"status"`
	DueAt                  time.Time     `json:"due_at"`
	Payments               []Payment     `json:"payments"`
	CreatedAt              time.Time     `json:"created_at"`
	UpdatedAt              time.Time     `json:"updated_at"`
	IssuedAt               time.Time     `json:"issued_at"`
	PaidAt                 *time.Time    `json:"paid_at,omitempty"`
}

type MessageVisibility string

const (
	MessageVisibilityShared   MessageVisibility = "shared"
	MessageVisibilityInternal MessageVisibility = "internal"
)

type ProjectMessage struct {
	ID           string            `json:"id"`
	ProjectID    string            `json:"project_id"`
	AuthorUserID string            `json:"author_user_id"`
	AuthorRole   Role              `json:"author_role"`
	Visibility   MessageVisibility `json:"visibility"`
	Body         string            `json:"body"`
	CreatedAt    time.Time         `json:"created_at"`
}

type ContractorDashboardSummary struct {
	OrganizationCount     int `json:"organization_count"`
	AvailableRequestCount int `json:"available_request_count"`
	ActiveProjectCount    int `json:"active_project_count"`
	PendingQuoteCount     int `json:"pending_quote_count"`
}

type ContractorDashboard struct {
	ContractorUserID  string                     `json:"contractor_user_id"`
	Summary           ContractorDashboardSummary `json:"summary"`
	Organizations     []Organization             `json:"organizations"`
	AvailableRequests []ContractorInboxItem      `json:"available_requests"`
	ActiveProjects    []ProjectWorkspaceItem     `json:"active_projects"`
}

type ProjectTimelineEvent struct {
	ID          string    `json:"id"`
	EventType   string    `json:"event_type"`
	Title       string    `json:"title"`
	Description string    `json:"description"`
	CreatedAt   time.Time `json:"created_at"`
}

type ProjectDetail struct {
	ViewerRole   string                 `json:"viewer_role"`
	Item         ProjectWorkspaceItem   `json:"item"`
	Estimates    []Estimate             `json:"estimates"`
	Appointments []Appointment          `json:"appointments"`
	Invoices     []Invoice              `json:"invoices"`
	Messages     []ProjectMessage       `json:"messages"`
	Timeline     []ProjectTimelineEvent `json:"timeline"`
}
