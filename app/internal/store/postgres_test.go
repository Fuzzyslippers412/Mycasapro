package store

import (
	"context"
	"testing"
	"time"

	sqlmock "github.com/DATA-DOG/go-sqlmock"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

func TestPostgresStoreCreateProperty(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	repo := NewPostgresStore(db)

	mock.ExpectBegin()
	mock.ExpectExec("insert into properties").
		WithArgs(
			sqlmock.AnyArg(),
			"homeowner-1",
			"Main House",
			"100 Oak St",
			"",
			"Seattle",
			"WA",
			"98101",
			"US",
			sqlmock.AnyArg(),
		).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	property, err := repo.CreateProperty(context.Background(), CreatePropertyInput{
		HomeownerUserID: "homeowner-1",
		Label:           "Main House",
		AddressLine1:    "100 Oak St",
		City:            "Seattle",
		Region:          "WA",
		PostalCode:      "98101",
		CountryCode:     "US",
	})
	if err != nil {
		t.Fatalf("create property: %v", err)
	}
	if property.HomeownerUserID != "homeowner-1" {
		t.Fatalf("homeowner mismatch: got=%s", property.HomeownerUserID)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("expectations: %v", err)
	}
}

func TestPostgresStoreCreateProjectFromRequest(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	repo := NewPostgresStore(db)
	now := time.Now().UTC()

	mock.ExpectBegin()
	mock.ExpectQuery("select exists \\(select 1 from organizations where id = \\$1\\)").
		WithArgs("org-1").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(true))
	mock.ExpectQuery("select exists \\(").
		WithArgs("org-1", "contractor-1").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(true))
	mock.ExpectQuery("select id, property_id, requested_by_user_id, title, category, area, urgency, description, preferred_timing, status, created_at").
		WithArgs("req-1").
		WillReturnRows(sqlmock.NewRows([]string{
			"id", "property_id", "requested_by_user_id", "title", "category", "area", "urgency", "description", "preferred_timing", "status", "created_at",
		}).AddRow("req-1", "prop-1", "homeowner-1", "Sink leak", "plumbing", "kitchen", "high", "Leak under sink", "weekday mornings", "new", now))
	mock.ExpectExec("insert into projects").
		WithArgs(sqlmock.AnyArg(), "prop-1", "req-1", "org-1", "Sink leak", string(domain.ProjectStatusDraft), sqlmock.AnyArg()).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectExec("update work_requests").
		WithArgs("req-1", string(domain.WorkRequestStatusConverted)).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectExec("insert into property_assignments").
		WithArgs("prop-1", "org-1", "service_provider", sqlmock.AnyArg()).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	project, err := repo.CreateProjectFromRequest(context.Background(), CreateProjectFromRequestInput{
		ContractorUserID: "contractor-1",
		OrganizationID:   "org-1",
		WorkRequestID:    "req-1",
	})
	if err != nil {
		t.Fatalf("create project from request: %v", err)
	}
	if project.ContractorOrgID != "org-1" {
		t.Fatalf("contractor org mismatch: got=%s", project.ContractorOrgID)
	}
	if project.WorkRequestID != "req-1" {
		t.Fatalf("work request mismatch: got=%s", project.WorkRequestID)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("expectations: %v", err)
	}
}

func TestPostgresStoreCreateEstimate(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	repo := NewPostgresStore(db)

	mock.ExpectBegin()
	mock.ExpectQuery("select id, contractor_org_id from projects").
		WithArgs("proj-2").
		WillReturnRows(sqlmock.NewRows([]string{"id", "contractor_org_id"}).AddRow("proj-2", "org-2"))
	mock.ExpectQuery("select exists \\(").
		WithArgs("org-2", "contractor-2").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(true))
	mock.ExpectExec("insert into estimates").
		WithArgs(
			sqlmock.AnyArg(),
			"proj-2",
			"org-2",
			"Swap outlet and test circuit",
			"",
			int64(2500),
			int64(12000),
			string(domain.EstimateStatusSent),
			sqlmock.AnyArg(),
			sqlmock.AnyArg(),
			sqlmock.AnyArg(),
			nil,
		).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectExec("insert into estimate_line_items").
		WithArgs(sqlmock.AnyArg(), sqlmock.AnyArg(), "Labor", int64(9000), 0).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectExec("insert into estimate_line_items").
		WithArgs(sqlmock.AnyArg(), sqlmock.AnyArg(), "Materials", int64(3000), 1).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	estimate, err := repo.CreateEstimate(context.Background(), CreateEstimateInput{
		ContractorUserID:   "contractor-2",
		ProjectID:          "proj-2",
		Summary:            "Swap outlet and test circuit",
		DepositAmountCents: 2500,
		LineItems: []EstimateLineItemInput{
			{Label: "Labor", AmountCents: 9000},
			{Label: "Materials", AmountCents: 3000},
		},
	})
	if err != nil {
		t.Fatalf("create estimate: %v", err)
	}
	if estimate.TotalAmountCents != 12000 {
		t.Fatalf("estimate total mismatch: got=%d", estimate.TotalAmountCents)
	}
	if len(estimate.LineItems) != 2 {
		t.Fatalf("line item count mismatch: got=%d", len(estimate.LineItems))
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("expectations: %v", err)
	}
}

func TestPostgresStoreCreateAppointment(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	repo := NewPostgresStore(db)
	startsAt := time.Date(2026, time.August, 1, 17, 0, 0, 0, time.UTC)
	endsAt := startsAt.Add(time.Hour)

	mock.ExpectBegin()
	mock.ExpectQuery("select id, contractor_org_id from projects").
		WithArgs("proj-3").
		WillReturnRows(sqlmock.NewRows([]string{"id", "contractor_org_id"}).AddRow("proj-3", "org-3"))
	mock.ExpectQuery("select exists \\(").
		WithArgs("org-3", "contractor-3").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(true))
	mock.ExpectExec("insert into appointments").
		WithArgs(sqlmock.AnyArg(), "proj-3", "org-3", "Walkthrough", "Bring ladder.", startsAt, endsAt, string(domain.AppointmentStatusScheduled), sqlmock.AnyArg()).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	appointment, err := repo.CreateAppointment(context.Background(), CreateAppointmentInput{
		ContractorUserID: "contractor-3",
		ProjectID:        "proj-3",
		Title:            "Walkthrough",
		Notes:            "Bring ladder.",
		StartsAt:         startsAt,
		EndsAt:           endsAt,
	})
	if err != nil {
		t.Fatalf("create appointment: %v", err)
	}
	if appointment.Status != domain.AppointmentStatusScheduled {
		t.Fatalf("appointment status mismatch: got=%s", appointment.Status)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("expectations: %v", err)
	}
}

func TestPostgresStoreCreateInvoice(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	repo := NewPostgresStore(db)
	dueAt := time.Date(2026, time.August, 3, 17, 0, 0, 0, time.UTC)

	mock.ExpectBegin()
	mock.ExpectQuery("select id, contractor_org_id from projects").
		WithArgs("proj-4").
		WillReturnRows(sqlmock.NewRows([]string{"id", "contractor_org_id"}).AddRow("proj-4", "org-4"))
	mock.ExpectQuery("select exists \\(").
		WithArgs("org-4", "contractor-4").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(true))
	mock.ExpectExec("insert into invoices").
		WithArgs(sqlmock.AnyArg(), "proj-4", "org-4", "Deposit invoice", "", int64(6500), int64(0), int64(6500), string(domain.InvoiceStatusSent), dueAt, sqlmock.AnyArg(), sqlmock.AnyArg(), sqlmock.AnyArg(), nil).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	invoice, err := repo.CreateInvoice(context.Background(), CreateInvoiceInput{
		ContractorUserID: "contractor-4",
		ProjectID:        "proj-4",
		Summary:          "Deposit invoice",
		AmountCents:      6500,
		DueAt:            dueAt,
	})
	if err != nil {
		t.Fatalf("create invoice: %v", err)
	}
	if invoice.OutstandingAmountCents != 6500 {
		t.Fatalf("outstanding amount mismatch: got=%d", invoice.OutstandingAmountCents)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("expectations: %v", err)
	}
}

func TestPostgresStoreRecordInvoicePayment(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	repo := NewPostgresStore(db)
	now := time.Date(2026, time.August, 2, 12, 0, 0, 0, time.UTC)

	mock.ExpectBegin()
	mock.ExpectQuery("select p.homeowner_user_id").
		WithArgs("proj-4").
		WillReturnRows(sqlmock.NewRows([]string{"homeowner_user_id"}).AddRow("homeowner-4"))
	mock.ExpectQuery("select amount_cents, amount_paid_cents, outstanding_amount_cents, status").
		WithArgs("inv-4", "proj-4").
		WillReturnRows(sqlmock.NewRows([]string{"amount_cents", "amount_paid_cents", "outstanding_amount_cents", "status"}).AddRow(int64(6500), int64(0), int64(6500), string(domain.InvoiceStatusSent)))
	mock.ExpectExec("insert into invoice_payments").
		WithArgs(sqlmock.AnyArg(), "inv-4", "homeowner-4", int64(6500), "Paid in full.", sqlmock.AnyArg(), sqlmock.AnyArg()).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectExec("update invoices").
		WithArgs("inv-4", int64(6500), int64(0), string(domain.InvoiceStatusPaid), sqlmock.AnyArg(), sqlmock.AnyArg()).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectQuery("select id, project_id, contractor_org_id, summary, notes, amount_cents, amount_paid_cents, outstanding_amount_cents, status, due_at, created_at, updated_at, issued_at, paid_at").
		WithArgs("inv-4").
		WillReturnRows(sqlmock.NewRows([]string{
			"id", "project_id", "contractor_org_id", "summary", "notes", "amount_cents", "amount_paid_cents", "outstanding_amount_cents", "status", "due_at", "created_at", "updated_at", "issued_at", "paid_at",
		}).AddRow("inv-4", "proj-4", "org-4", "Deposit invoice", "", int64(6500), int64(6500), int64(0), string(domain.InvoiceStatusPaid), now.Add(24*time.Hour), now, now, now, now))
	mock.ExpectQuery("select id, invoice_id, payer_user_id, amount_cents, note, paid_at, created_at").
		WithArgs("inv-4").
		WillReturnRows(sqlmock.NewRows([]string{"id", "invoice_id", "payer_user_id", "amount_cents", "note", "paid_at", "created_at"}).AddRow("pay-4", "inv-4", "homeowner-4", int64(6500), "Paid in full.", now, now))
	mock.ExpectCommit()

	invoice, err := repo.RecordInvoicePayment(context.Background(), RecordInvoicePaymentInput{
		HomeownerUserID: "homeowner-4",
		ProjectID:       "proj-4",
		InvoiceID:       "inv-4",
		AmountCents:     6500,
		Note:            "Paid in full.",
	})
	if err != nil {
		t.Fatalf("record invoice payment: %v", err)
	}
	if invoice.Status != domain.InvoiceStatusPaid {
		t.Fatalf("invoice status mismatch: got=%s", invoice.Status)
	}
	if len(invoice.Payments) != 1 {
		t.Fatalf("payment count mismatch: got=%d", len(invoice.Payments))
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("expectations: %v", err)
	}
}

func TestPostgresStoreCreateProjectMessage(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("sqlmock: %v", err)
	}
	defer db.Close()

	repo := NewPostgresStore(db)

	mock.ExpectBegin()
	mock.ExpectQuery("select pr.id, pr.contractor_org_id, p.homeowner_user_id").
		WithArgs("proj-5").
		WillReturnRows(sqlmock.NewRows([]string{"id", "contractor_org_id", "homeowner_user_id"}).AddRow("proj-5", "org-5", "homeowner-5"))
	mock.ExpectQuery("select exists \\(").
		WithArgs("org-5", "contractor-5").
		WillReturnRows(sqlmock.NewRows([]string{"exists"}).AddRow(true))
	mock.ExpectExec("insert into project_messages").
		WithArgs(sqlmock.AnyArg(), "proj-5", "contractor-5", string(domain.RoleContractor), string(domain.MessageVisibilityInternal), "Bring replacement switch plate.", sqlmock.AnyArg()).
		WillReturnResult(sqlmock.NewResult(1, 1))
	mock.ExpectCommit()

	message, err := repo.CreateProjectMessage(context.Background(), CreateProjectMessageInput{
		AuthorUserID: "contractor-5",
		AuthorRole:   domain.RoleContractor,
		ProjectID:    "proj-5",
		Visibility:   domain.MessageVisibilityInternal,
		Body:         "Bring replacement switch plate.",
	})
	if err != nil {
		t.Fatalf("create project message: %v", err)
	}
	if message.Visibility != domain.MessageVisibilityInternal {
		t.Fatalf("message visibility mismatch: got=%s", message.Visibility)
	}
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Fatalf("expectations: %v", err)
	}
}
