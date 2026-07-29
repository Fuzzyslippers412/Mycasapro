package store

import (
	"context"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func TestMemoryStoreDashboardSummary(t *testing.T) {
	repo := NewMemoryStore()
	ctx := context.Background()

	property, err := repo.CreateProperty(ctx, CreatePropertyInput{
		HomeownerUserID: "homeowner-1",
		Label:           "Primary Home",
		AddressLine1:    "1 Main St",
		City:            "Seattle",
		Region:          "WA",
		PostalCode:      "98101",
	})
	if err != nil {
		t.Fatalf("create property: %v", err)
	}

	if _, err := repo.CreateWorkRequest(ctx, CreateWorkRequestInput{
		HomeownerUserID: "homeowner-1",
		PropertyID:      property.ID,
		Title:           "HVAC tune-up",
		Category:        "hvac",
		Area:            "utility",
		Urgency:         "low",
		Description:     "Need seasonal service.",
	}); err != nil {
		t.Fatalf("create work request: %v", err)
	}

	dashboard, err := repo.GetHomeownerDashboard(ctx, "homeowner-1")
	if err != nil {
		t.Fatalf("dashboard: %v", err)
	}

	if dashboard.Summary.PropertyCount != 1 {
		t.Fatalf("property count mismatch: got=%d", dashboard.Summary.PropertyCount)
	}
	if dashboard.Summary.OpenRepairCount != 1 {
		t.Fatalf("open repair count mismatch: got=%d", dashboard.Summary.OpenRepairCount)
	}
	if dashboard.Summary.RequestsByStatus[string(domain.WorkRequestStatusNew)] != 1 {
		t.Fatalf("status count mismatch: got=%d", dashboard.Summary.RequestsByStatus[string(domain.WorkRequestStatusNew)])
	}
}

func TestMemoryStoreRejectsUnknownPropertyForWorkRequest(t *testing.T) {
	repo := NewMemoryStore()

	_, err := repo.CreateWorkRequest(context.Background(), CreateWorkRequestInput{
		HomeownerUserID: "homeowner-1",
		PropertyID:      "prop-missing",
		Title:           "Outlet not working",
		Category:        "electrical",
		Area:            "hallway",
		Urgency:         "medium",
		Description:     "No power at the outlet.",
	})
	if err != ErrPropertyNotFound {
		t.Fatalf("expected ErrPropertyNotFound, got=%v", err)
	}
}

func TestMemoryStoreInviteExpiryAndRevocation(t *testing.T) {
	repo := NewMemoryStore()
	ctx := context.Background()
	now := time.Now().UTC()
	property, err := repo.CreateProperty(ctx, CreatePropertyInput{
		HomeownerUserID: "homeowner-invite-lifecycle", Label: "Home", AddressLine1: "1 Private Road",
		City: "Oakland", Region: "CA", PostalCode: "94612", CountryCode: "US",
	})
	if err != nil {
		t.Fatalf("create property: %v", err)
	}
	request, err := repo.CreateWorkRequest(ctx, CreateWorkRequestInput{
		HomeownerUserID: "homeowner-invite-lifecycle", PropertyID: property.ID, Title: "Repair a window latch",
		Category: "general", Area: "Bedroom", Urgency: "medium", Description: "The latch no longer closes.",
	})
	if err != nil {
		t.Fatalf("create work request: %v", err)
	}
	expiringHash := strings.Repeat("a", 64)
	if _, err := repo.CreateWorkRequestInvite(ctx, CreateWorkRequestInviteInput{
		HomeownerUserID: "homeowner-invite-lifecycle", WorkRequestID: request.ID,
		TokenHash: expiringHash, ExpiresAt: now.Add(time.Minute),
	}); err != nil {
		t.Fatalf("create expiring invite: %v", err)
	}
	if _, err := repo.GetInviteTask(ctx, expiringHash, now); err != nil {
		t.Fatalf("active invite unavailable: %v", err)
	}
	if _, err := repo.GetInviteTask(ctx, expiringHash, now.Add(2*time.Minute)); err != ErrInviteExpired {
		t.Fatalf("expected expired invite, got=%v", err)
	}

	revokedHash := strings.Repeat("b", 64)
	invite, err := repo.CreateWorkRequestInvite(ctx, CreateWorkRequestInviteInput{
		HomeownerUserID: "homeowner-invite-lifecycle", WorkRequestID: request.ID,
		TokenHash: revokedHash, ExpiresAt: now.Add(time.Hour),
	})
	if err != nil {
		t.Fatalf("create revocable invite: %v", err)
	}
	if _, err := repo.RevokeWorkRequestInvite(ctx, "homeowner-invite-lifecycle", request.ID, invite.ID, now); err != nil {
		t.Fatalf("revoke invite: %v", err)
	}
	if _, err := repo.GetInviteTask(ctx, revokedHash, now); err != ErrInviteRevoked {
		t.Fatalf("expected revoked invite, got=%v", err)
	}
}

func TestMemoryStoreLimitsEmailInvitationAbuse(t *testing.T) {
	repo := NewMemoryStore()
	ctx := context.Background()
	property, err := repo.CreateProperty(ctx, CreatePropertyInput{
		HomeownerUserID: "homeowner-rate", Label: "Home", AddressLine1: "1 Main St", City: "Oakland", Region: "CA", PostalCode: "94607",
	})
	if err != nil {
		t.Fatal(err)
	}
	request, err := repo.CreateWorkRequest(ctx, CreateWorkRequestInput{
		HomeownerUserID: "homeowner-rate", PropertyID: property.ID, Title: "Repair", Category: "general",
		Area: "entry", Urgency: "medium", Description: "Repair needed",
	})
	if err != nil {
		t.Fatal(err)
	}
	for index := 0; index < maxEmailInvitesPerHour; index++ {
		_, err := repo.CreateWorkRequestInvite(ctx, CreateWorkRequestInviteInput{
			HomeownerUserID: "homeowner-rate", WorkRequestID: request.ID, TokenHash: fmt.Sprintf("%064x", index+1),
			RecipientEmail: fmt.Sprintf("contractor-%d@example.com", index), EmailSubject: "Invitation",
			EmailTextBody: "Review", EmailHTMLBody: "<p>Review</p>", ExpiresAt: time.Now().UTC().Add(time.Hour),
		})
		if err != nil {
			t.Fatalf("create invitation %d: %v", index, err)
		}
	}
	_, err = repo.CreateWorkRequestInvite(ctx, CreateWorkRequestInviteInput{
		HomeownerUserID: "homeowner-rate", WorkRequestID: request.ID, TokenHash: strings.Repeat("f", 64),
		RecipientEmail: "overflow@example.com", EmailSubject: "Invitation", EmailTextBody: "Review",
		EmailHTMLBody: "<p>Review</p>", ExpiresAt: time.Now().UTC().Add(time.Hour),
	})
	if err != ErrInviteRateLimited {
		t.Fatalf("email invitation over limit returned %v", err)
	}
}

func TestMemoryStoreContractorCanConvertRequestToProject(t *testing.T) {
	repo := NewMemoryStore()
	ctx := context.Background()

	property, err := repo.CreateProperty(ctx, CreatePropertyInput{
		HomeownerUserID: "homeowner-1",
		Label:           "Primary Home",
		AddressLine1:    "1 Main St",
		City:            "Seattle",
		Region:          "WA",
		PostalCode:      "98101",
	})
	if err != nil {
		t.Fatalf("create property: %v", err)
	}

	request, err := repo.CreateWorkRequest(ctx, CreateWorkRequestInput{
		HomeownerUserID: "homeowner-1",
		PropertyID:      property.ID,
		Title:           "Deck repair",
		Category:        "carpentry",
		Area:            "backyard",
		Urgency:         "medium",
		Description:     "Loose boards on the deck stairs.",
	})
	if err != nil {
		t.Fatalf("create work request: %v", err)
	}

	org, err := repo.CreateOrganization(ctx, CreateOrganizationInput{
		ContractorUserID: "contractor-1",
		Name:             "West Hill Contractors",
	})
	if err != nil {
		t.Fatalf("create organization: %v", err)
	}

	project, err := repo.CreateProjectFromRequest(ctx, CreateProjectFromRequestInput{
		ContractorUserID: "contractor-1",
		OrganizationID:   org.ID,
		WorkRequestID:    request.ID,
	})
	if err != nil {
		t.Fatalf("create project from request: %v", err)
	}
	if project.ContractorOrgID != org.ID {
		t.Fatalf("contractor org mismatch: got=%s want=%s", project.ContractorOrgID, org.ID)
	}

	dashboard, err := repo.GetContractorDashboard(ctx, "contractor-1")
	if err != nil {
		t.Fatalf("dashboard: %v", err)
	}
	if dashboard.Summary.ActiveProjectCount != 1 {
		t.Fatalf("active project count mismatch: got=%d", dashboard.Summary.ActiveProjectCount)
	}
	if dashboard.Summary.AvailableRequestCount != 0 {
		t.Fatalf("available request count mismatch: got=%d", dashboard.Summary.AvailableRequestCount)
	}
}

func TestMemoryStoreProjectDetailForHomeowner(t *testing.T) {
	repo := NewMemoryStore()
	ctx := context.Background()

	property, err := repo.CreateProperty(ctx, CreatePropertyInput{
		HomeownerUserID: "homeowner-9",
		Label:           "Cottage",
		AddressLine1:    "9 Lake Rd",
		City:            "Bellingham",
		Region:          "WA",
		PostalCode:      "98225",
	})
	if err != nil {
		t.Fatalf("create property: %v", err)
	}

	request, err := repo.CreateWorkRequest(ctx, CreateWorkRequestInput{
		HomeownerUserID: "homeowner-9",
		PropertyID:      property.ID,
		Title:           "Roof leak",
		Category:        "roofing",
		Area:            "attic",
		Urgency:         "urgent",
		Description:     "Leak during heavy rain.",
	})
	if err != nil {
		t.Fatalf("create work request: %v", err)
	}

	org, err := repo.CreateOrganization(ctx, CreateOrganizationInput{
		ContractorUserID: "contractor-9",
		Name:             "Peak Roofing",
	})
	if err != nil {
		t.Fatalf("create organization: %v", err)
	}

	project, err := repo.CreateProjectFromRequest(ctx, CreateProjectFromRequestInput{
		ContractorUserID: "contractor-9",
		OrganizationID:   org.ID,
		WorkRequestID:    request.ID,
	})
	if err != nil {
		t.Fatalf("create project: %v", err)
	}

	detail, err := repo.GetProjectDetailForHomeowner(ctx, "homeowner-9", project.ID)
	if err != nil {
		t.Fatalf("project detail: %v", err)
	}
	if detail.ViewerRole != "homeowner" {
		t.Fatalf("viewer role mismatch: got=%s", detail.ViewerRole)
	}
	if detail.Item.WorkRequest == nil || detail.Item.WorkRequest.ID != request.ID {
		t.Fatalf("expected linked request in project detail")
	}
	if len(detail.Timeline) < 2 {
		t.Fatalf("expected timeline events, got=%d", len(detail.Timeline))
	}
}

func TestMemoryStoreEstimateLifecycle(t *testing.T) {
	repo := NewMemoryStore()
	ctx := context.Background()

	property, err := repo.CreateProperty(ctx, CreatePropertyInput{
		HomeownerUserID: "homeowner-10",
		Label:           "Bungalow",
		AddressLine1:    "100 Palm St",
		City:            "Long Beach",
		Region:          "CA",
		PostalCode:      "90802",
	})
	if err != nil {
		t.Fatalf("create property: %v", err)
	}

	request, err := repo.CreateWorkRequest(ctx, CreateWorkRequestInput{
		HomeownerUserID: "homeowner-10",
		PropertyID:      property.ID,
		Title:           "Fence repair",
		Category:        "carpentry",
		Area:            "yard",
		Urgency:         "medium",
		Description:     "Two boards are loose after the last storm.",
	})
	if err != nil {
		t.Fatalf("create work request: %v", err)
	}

	org, err := repo.CreateOrganization(ctx, CreateOrganizationInput{
		ContractorUserID: "contractor-10",
		Name:             "Pacific Fixers",
	})
	if err != nil {
		t.Fatalf("create organization: %v", err)
	}

	project, err := repo.CreateProjectFromRequest(ctx, CreateProjectFromRequestInput{
		ContractorUserID: "contractor-10",
		OrganizationID:   org.ID,
		WorkRequestID:    request.ID,
	})
	if err != nil {
		t.Fatalf("create project: %v", err)
	}

	estimate, err := repo.CreateEstimate(ctx, CreateEstimateInput{
		ContractorUserID:   "contractor-10",
		ProjectID:          project.ID,
		Summary:            "Fence board replacement and reinforcement",
		DepositAmountCents: 7500,
		LineItems: []EstimateLineItemInput{
			{Label: "Labor", AmountCents: 18000},
			{Label: "Materials", AmountCents: 7000},
		},
	})
	if err != nil {
		t.Fatalf("create estimate: %v", err)
	}
	if estimate.TotalAmountCents != 25000 {
		t.Fatalf("estimate total mismatch: got=%d", estimate.TotalAmountCents)
	}

	contractorDashboard, err := repo.GetContractorDashboard(ctx, "contractor-10")
	if err != nil {
		t.Fatalf("contractor dashboard: %v", err)
	}
	if contractorDashboard.Summary.PendingQuoteCount != 0 {
		t.Fatalf("pending quote count mismatch after estimate: got=%d", contractorDashboard.Summary.PendingQuoteCount)
	}

	homeownerDashboard, err := repo.GetHomeownerDashboard(ctx, "homeowner-10")
	if err != nil {
		t.Fatalf("homeowner dashboard: %v", err)
	}
	if homeownerDashboard.Summary.PendingApprovalCount != 1 {
		t.Fatalf("pending approval count mismatch: got=%d", homeownerDashboard.Summary.PendingApprovalCount)
	}

	approved, err := repo.ApproveEstimate(ctx, "homeowner-10", project.ID, estimate.ID)
	if err != nil {
		t.Fatalf("approve estimate: %v", err)
	}
	if approved.Status != domain.EstimateStatusApproved {
		t.Fatalf("estimate status mismatch: got=%s", approved.Status)
	}

	appointment, err := repo.CreateAppointment(ctx, CreateAppointmentInput{
		ContractorUserID: "contractor-10",
		ProjectID:        project.ID,
		Title:            "Initial site visit",
		StartsAt:         approved.UpdatedAt.Add(24 * time.Hour),
		EndsAt:           approved.UpdatedAt.Add(26 * time.Hour),
	})
	if err != nil {
		t.Fatalf("create appointment: %v", err)
	}
	if appointment.Status != domain.AppointmentStatusScheduled {
		t.Fatalf("appointment status mismatch: got=%s", appointment.Status)
	}

	invoice, err := repo.CreateInvoice(ctx, CreateInvoiceInput{
		ContractorUserID: "contractor-10",
		ProjectID:        project.ID,
		Summary:          "Deposit invoice",
		Notes:            "Due before materials are ordered.",
		AmountCents:      7500,
		DueAt:            approved.UpdatedAt.Add(72 * time.Hour),
	})
	if err != nil {
		t.Fatalf("create invoice: %v", err)
	}
	if invoice.OutstandingAmountCents != 7500 {
		t.Fatalf("invoice outstanding mismatch: got=%d", invoice.OutstandingAmountCents)
	}

	homeownerDashboard, err = repo.GetHomeownerDashboard(ctx, "homeowner-10")
	if err != nil {
		t.Fatalf("homeowner dashboard after invoice: %v", err)
	}
	if homeownerDashboard.Summary.OutstandingInvoiceCount != 1 {
		t.Fatalf("outstanding invoice count mismatch after invoice: got=%d", homeownerDashboard.Summary.OutstandingInvoiceCount)
	}

	invoice, err = repo.RecordInvoicePayment(ctx, RecordInvoicePaymentInput{
		HomeownerUserID: "homeowner-10",
		ProjectID:       project.ID,
		InvoiceID:       invoice.ID,
		AmountCents:     2500,
		Note:            "First installment from homeowner portal.",
	})
	if err != nil {
		t.Fatalf("record partial payment: %v", err)
	}
	if invoice.Status != domain.InvoiceStatusPartiallyPaid {
		t.Fatalf("invoice status mismatch after partial payment: got=%s", invoice.Status)
	}
	if invoice.OutstandingAmountCents != 5000 {
		t.Fatalf("invoice outstanding mismatch after partial payment: got=%d", invoice.OutstandingAmountCents)
	}

	invoice, err = repo.RecordInvoicePayment(ctx, RecordInvoicePaymentInput{
		HomeownerUserID: "homeowner-10",
		ProjectID:       project.ID,
		InvoiceID:       invoice.ID,
		AmountCents:     5000,
		Note:            "Final deposit payment.",
	})
	if err != nil {
		t.Fatalf("record final payment: %v", err)
	}
	if invoice.Status != domain.InvoiceStatusPaid {
		t.Fatalf("invoice status mismatch after full payment: got=%s", invoice.Status)
	}
	if invoice.OutstandingAmountCents != 0 {
		t.Fatalf("invoice outstanding mismatch after full payment: got=%d", invoice.OutstandingAmountCents)
	}

	detail, err := repo.GetProjectDetailForHomeowner(ctx, "homeowner-10", project.ID)
	if err != nil {
		t.Fatalf("project detail: %v", err)
	}
	if detail.Item.Project.Status != domain.ProjectStatusApproved {
		t.Fatalf("project status mismatch: got=%s", detail.Item.Project.Status)
	}
	if len(detail.Estimates) != 1 {
		t.Fatalf("estimate count mismatch: got=%d", len(detail.Estimates))
	}
	if detail.Estimates[0].Status != domain.EstimateStatusApproved {
		t.Fatalf("detail estimate status mismatch: got=%s", detail.Estimates[0].Status)
	}
	if len(detail.Appointments) != 1 {
		t.Fatalf("appointment count mismatch: got=%d", len(detail.Appointments))
	}
	if len(detail.Invoices) != 1 {
		t.Fatalf("invoice count mismatch: got=%d", len(detail.Invoices))
	}
	if len(detail.Invoices[0].Payments) != 2 {
		t.Fatalf("invoice payment count mismatch: got=%d", len(detail.Invoices[0].Payments))
	}
	if len(detail.Timeline) < 8 {
		t.Fatalf("expected estimate lifecycle in timeline, got=%d events", len(detail.Timeline))
	}

	homeownerDashboard, err = repo.GetHomeownerDashboard(ctx, "homeowner-10")
	if err != nil {
		t.Fatalf("homeowner dashboard after schedule: %v", err)
	}
	if homeownerDashboard.Summary.ScheduledVisitCount != 1 {
		t.Fatalf("scheduled visit count mismatch: got=%d", homeownerDashboard.Summary.ScheduledVisitCount)
	}
	if homeownerDashboard.Summary.OutstandingInvoiceCount != 0 {
		t.Fatalf("outstanding invoice count mismatch after full payment: got=%d", homeownerDashboard.Summary.OutstandingInvoiceCount)
	}
}

func TestMemoryStoreProjectMessagesRespectVisibility(t *testing.T) {
	repo := NewMemoryStore()
	ctx := context.Background()

	property, err := repo.CreateProperty(ctx, CreatePropertyInput{
		HomeownerUserID: "homeowner-20",
		Label:           "Loft",
		AddressLine1:    "500 Union St",
		City:            "Seattle",
		Region:          "WA",
		PostalCode:      "98101",
	})
	if err != nil {
		t.Fatalf("create property: %v", err)
	}

	request, err := repo.CreateWorkRequest(ctx, CreateWorkRequestInput{
		HomeownerUserID: "homeowner-20",
		PropertyID:      property.ID,
		Title:           "Cabinet hinge repair",
		Category:        "carpentry",
		Area:            "kitchen",
		Urgency:         "low",
		Description:     "Upper cabinet door is sagging.",
	})
	if err != nil {
		t.Fatalf("create work request: %v", err)
	}

	org, err := repo.CreateOrganization(ctx, CreateOrganizationInput{
		ContractorUserID: "contractor-20",
		Name:             "Crafted Homes",
	})
	if err != nil {
		t.Fatalf("create organization: %v", err)
	}

	project, err := repo.CreateProjectFromRequest(ctx, CreateProjectFromRequestInput{
		ContractorUserID: "contractor-20",
		OrganizationID:   org.ID,
		WorkRequestID:    request.ID,
	})
	if err != nil {
		t.Fatalf("create project: %v", err)
	}

	if _, err := repo.CreateProjectMessage(ctx, CreateProjectMessageInput{
		AuthorUserID: "contractor-20",
		AuthorRole:   domain.RoleContractor,
		ProjectID:    project.ID,
		Visibility:   domain.MessageVisibilityShared,
		Body:         "We can stop by tomorrow afternoon for a quick look.",
	}); err != nil {
		t.Fatalf("create contractor shared message: %v", err)
	}

	if _, err := repo.CreateProjectMessage(ctx, CreateProjectMessageInput{
		AuthorUserID: "contractor-20",
		AuthorRole:   domain.RoleContractor,
		ProjectID:    project.ID,
		Visibility:   domain.MessageVisibilityInternal,
		Body:         "Bring spare hinge kit from van stock.",
	}); err != nil {
		t.Fatalf("create contractor internal message: %v", err)
	}

	if _, err := repo.CreateProjectMessage(ctx, CreateProjectMessageInput{
		AuthorUserID: "homeowner-20",
		AuthorRole:   domain.RoleHomeowner,
		ProjectID:    project.ID,
		Visibility:   domain.MessageVisibilityShared,
		Body:         "Tomorrow afternoon works for me.",
	}); err != nil {
		t.Fatalf("create homeowner shared message: %v", err)
	}

	homeownerDetail, err := repo.GetProjectDetailForHomeowner(ctx, "homeowner-20", project.ID)
	if err != nil {
		t.Fatalf("homeowner detail: %v", err)
	}
	if len(homeownerDetail.Messages) != 2 {
		t.Fatalf("homeowner message count mismatch: got=%d", len(homeownerDetail.Messages))
	}
	for _, message := range homeownerDetail.Messages {
		if message.Visibility != domain.MessageVisibilityShared {
			t.Fatalf("homeowner should not see internal message visibility=%s", message.Visibility)
		}
	}

	contractorDetail, err := repo.GetProjectDetailForContractor(ctx, "contractor-20", project.ID)
	if err != nil {
		t.Fatalf("contractor detail: %v", err)
	}
	if len(contractorDetail.Messages) != 3 {
		t.Fatalf("contractor message count mismatch: got=%d", len(contractorDetail.Messages))
	}
	internalFound := false
	for _, message := range contractorDetail.Messages {
		if message.Visibility == domain.MessageVisibilityInternal {
			internalFound = true
			break
		}
	}
	if !internalFound {
		t.Fatal("expected internal note in contractor view")
	}
}
