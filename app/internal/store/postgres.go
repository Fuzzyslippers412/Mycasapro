package store

import (
	"context"
	"database/sql"
	"errors"
	"strings"
	"time"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
)

type PostgresStore struct {
	db *sql.DB
}

func NewPostgresStore(db *sql.DB) *PostgresStore {
	return &PostgresStore{db: db}
}

func (s *PostgresStore) Ping(ctx context.Context) error {
	return s.db.PingContext(ctx)
}

func (s *PostgresStore) CreateProperty(ctx context.Context, input CreatePropertyInput) (domain.Property, error) {
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

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Property{}, err
	}
	defer rollback(tx)

	_, err = tx.ExecContext(ctx, `
		insert into properties (
			id, homeowner_user_id, label, address_line_1, address_line_2, city, region, postal_code, country_code, created_at
		) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
	`, property.ID, property.HomeownerUserID, property.Label, property.AddressLine1, property.AddressLine2, property.City, property.Region, property.PostalCode, property.CountryCode, property.CreatedAt)
	if err != nil {
		return domain.Property{}, err
	}
	if err := tx.Commit(); err != nil {
		return domain.Property{}, err
	}
	return property, nil
}

func (s *PostgresStore) ListProperties(ctx context.Context, homeownerUserID string) ([]domain.Property, error) {
	rows, err := s.db.QueryContext(ctx, `
		select id, homeowner_user_id, label, address_line_1, address_line_2, city, region, postal_code, country_code, created_at
		from properties
		where homeowner_user_id = $1
		order by created_at desc
	`, strings.TrimSpace(homeownerUserID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]domain.Property, 0)
	for rows.Next() {
		property, err := scanProperty(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, property)
	}
	return out, rows.Err()
}

func (s *PostgresStore) CreateWorkRequest(ctx context.Context, input CreateWorkRequestInput) (domain.WorkRequest, error) {
	if strings.TrimSpace(input.HomeownerUserID) == "" ||
		strings.TrimSpace(input.PropertyID) == "" ||
		strings.TrimSpace(input.Title) == "" ||
		strings.TrimSpace(input.Category) == "" ||
		strings.TrimSpace(input.Area) == "" ||
		strings.TrimSpace(input.Urgency) == "" ||
		strings.TrimSpace(input.Description) == "" {
		return domain.WorkRequest{}, ErrInvalidInput
	}

	workRequest := domain.WorkRequest{
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

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.WorkRequest{}, err
	}
	defer rollback(tx)

	var exists bool
	if err := tx.QueryRowContext(ctx, `
		select exists (
			select 1
			from properties
			where id = $1 and homeowner_user_id = $2
		)
	`, workRequest.PropertyID, workRequest.RequestedByUserID).Scan(&exists); err != nil {
		return domain.WorkRequest{}, err
	}
	if !exists {
		return domain.WorkRequest{}, ErrPropertyNotFound
	}

	_, err = tx.ExecContext(ctx, `
		insert into work_requests (
			id, property_id, requested_by_user_id, title, category, area, urgency, description, preferred_timing, status, created_at
		) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
	`, workRequest.ID, workRequest.PropertyID, workRequest.RequestedByUserID, workRequest.Title, workRequest.Category, workRequest.Area, workRequest.Urgency, workRequest.Description, workRequest.PreferredTiming, string(workRequest.Status), workRequest.CreatedAt)
	if err != nil {
		return domain.WorkRequest{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.WorkRequest{}, err
	}
	return workRequest, nil
}

func (s *PostgresStore) ListWorkRequests(ctx context.Context, homeownerUserID string) ([]domain.WorkRequest, error) {
	rows, err := s.db.QueryContext(ctx, `
		select id, property_id, requested_by_user_id, title, category, area, urgency, description, preferred_timing, status, created_at
		from work_requests
		where requested_by_user_id = $1
		order by created_at desc
	`, strings.TrimSpace(homeownerUserID))
	if err != nil {
		return nil, err
	}
	out := make([]domain.WorkRequest, 0)
	for rows.Next() {
		workRequest, err := scanWorkRequest(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, workRequest)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	for index := range out {
		attachments, err := s.ListWorkRequestAttachments(ctx, homeownerUserID, out[index].ID)
		if err != nil {
			return nil, err
		}
		out[index].Attachments = attachments
		out[index].GuestEstimateCount, err = s.guestEstimateCount(ctx, out[index].ID)
		if err != nil {
			return nil, err
		}
	}
	return out, nil
}

func (s *PostgresStore) GetHomeownerDashboard(ctx context.Context, homeownerUserID string) (domain.HomeownerDashboard, error) {
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
		default:
			summary.OpenRepairCount++
		}
	}
	for _, project := range projects {
		latest, ok, err := s.latestEstimateForProject(ctx, project.Project.ID)
		if err != nil {
			return domain.HomeownerDashboard{}, err
		}
		if ok && latest.Status == domain.EstimateStatusSent {
			summary.PendingApprovalCount++
		}
		appointments, err := s.ListAppointmentsForProject(ctx, project.Project.ID)
		if err != nil {
			return domain.HomeownerDashboard{}, err
		}
		summary.ScheduledVisitCount += len(appointments)
		invoices, err := s.ListInvoicesForProject(ctx, project.Project.ID)
		if err != nil {
			return domain.HomeownerDashboard{}, err
		}
		for _, invoice := range invoices {
			if invoice.OutstandingAmountCents > 0 {
				summary.OutstandingInvoiceCount++
			}
		}
	}

	return domain.HomeownerDashboard{
		HomeownerUserID: homeownerUserID,
		Summary:         summary,
		Properties:      properties,
		WorkRequests:    workRequests,
		ActiveProjects:  projects,
	}, nil
}

func (s *PostgresStore) CreateOrganization(ctx context.Context, input CreateOrganizationInput) (domain.Organization, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" || strings.TrimSpace(input.Name) == "" {
		return domain.Organization{}, ErrInvalidInput
	}

	organization := domain.Organization{
		ID:        newID("org"),
		Name:      strings.TrimSpace(input.Name),
		Kind:      "contractor",
		CreatedAt: time.Now().UTC(),
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Organization{}, err
	}
	defer rollback(tx)

	_, err = tx.ExecContext(ctx, `
		insert into organizations (id, name, kind, created_at)
		values ($1,$2,$3,$4)
	`, organization.ID, organization.Name, organization.Kind, organization.CreatedAt)
	if err != nil {
		return domain.Organization{}, err
	}

	_, err = tx.ExecContext(ctx, `
		insert into organization_members (organization_id, user_id, role, created_at)
		values ($1,$2,$3,$4)
		on conflict (organization_id, user_id) do update set role = excluded.role
	`, organization.ID, strings.TrimSpace(input.ContractorUserID), string(domain.RoleContractorAdmin), time.Now().UTC())
	if err != nil {
		return domain.Organization{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.Organization{}, err
	}
	return organization, nil
}

func (s *PostgresStore) ListOrganizations(ctx context.Context, contractorUserID string) ([]domain.Organization, error) {
	rows, err := s.db.QueryContext(ctx, `
		select o.id, o.name, o.kind, o.created_at
		from organizations o
		join organization_members om on om.organization_id = o.id
		where om.user_id = $1
		order by o.created_at desc
	`, strings.TrimSpace(contractorUserID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]domain.Organization, 0)
	for rows.Next() {
		var org domain.Organization
		if err := rows.Scan(&org.ID, &org.Name, &org.Kind, &org.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, org)
	}
	return out, rows.Err()
}

func (s *PostgresStore) GetContractorDashboard(ctx context.Context, contractorUserID string) (domain.ContractorDashboard, error) {
	organizations, err := s.ListOrganizations(ctx, contractorUserID)
	if err != nil {
		return domain.ContractorDashboard{}, err
	}

	requestRows, err := s.db.QueryContext(ctx, `
		select
			wr.id, wr.property_id, wr.requested_by_user_id, wr.title, wr.category, wr.area, wr.urgency, wr.description, wr.preferred_timing, wr.status, wr.created_at,
			p.id, p.homeowner_user_id, p.label, p.address_line_1, p.address_line_2, p.city, p.region, p.postal_code, p.country_code, p.created_at
		from work_requests wr
		join properties p on p.id = wr.property_id
		where wr.status not in ($1, $2)
		order by wr.created_at desc
	`, string(domain.WorkRequestStatusConverted), string(domain.WorkRequestStatusDeclined))
	if err != nil {
		return domain.ContractorDashboard{}, err
	}
	available := make([]domain.ContractorInboxItem, 0)
	for requestRows.Next() {
		workRequest, property, err := scanInboxItem(requestRows)
		if err != nil {
			return domain.ContractorDashboard{}, err
		}
		available = append(available, domain.ContractorInboxItem{
			WorkRequest: workRequest,
			Property:    property,
		})
	}
	if err := requestRows.Err(); err != nil {
		_ = requestRows.Close()
		return domain.ContractorDashboard{}, err
	}
	if err := requestRows.Close(); err != nil {
		return domain.ContractorDashboard{}, err
	}
	for index := range available {
		attachments, err := s.listWorkRequestAttachmentsByID(ctx, available[index].WorkRequest.ID)
		if err != nil {
			return domain.ContractorDashboard{}, err
		}
		available[index].WorkRequest.Attachments = attachments
	}

	projects, err := s.ListProjectsForContractor(ctx, contractorUserID)
	if err != nil {
		return domain.ContractorDashboard{}, err
	}

	summary := domain.ContractorDashboardSummary{
		OrganizationCount:     len(organizations),
		AvailableRequestCount: len(available),
		ActiveProjectCount:    len(projects),
	}
	for _, project := range projects {
		latest, ok, err := s.latestEstimateForProject(ctx, project.Project.ID)
		if err != nil {
			return domain.ContractorDashboard{}, err
		}
		if !ok || latest.Status == domain.EstimateStatusRejected || latest.Status == domain.EstimateStatusDraft {
			summary.PendingQuoteCount++
		}
	}

	return domain.ContractorDashboard{
		ContractorUserID:  strings.TrimSpace(contractorUserID),
		Summary:           summary,
		Organizations:     organizations,
		AvailableRequests: available,
		ActiveProjects:    projects,
	}, nil
}

func (s *PostgresStore) CreateProjectFromRequest(ctx context.Context, input CreateProjectFromRequestInput) (domain.Project, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.OrganizationID) == "" ||
		strings.TrimSpace(input.WorkRequestID) == "" {
		return domain.Project{}, ErrInvalidInput
	}

	tx, err := s.db.BeginTx(ctx, &sql.TxOptions{})
	if err != nil {
		return domain.Project{}, err
	}
	defer rollback(tx)

	var orgExists bool
	if err := tx.QueryRowContext(ctx, `select exists (select 1 from organizations where id = $1)`, strings.TrimSpace(input.OrganizationID)).Scan(&orgExists); err != nil {
		return domain.Project{}, err
	}
	if !orgExists {
		return domain.Project{}, ErrOrganizationNotFound
	}

	var membershipExists bool
	if err := tx.QueryRowContext(ctx, `
		select exists (
			select 1
			from organization_members
			where organization_id = $1 and user_id = $2
		)
	`, strings.TrimSpace(input.OrganizationID), strings.TrimSpace(input.ContractorUserID)).Scan(&membershipExists); err != nil {
		return domain.Project{}, err
	}
	if !membershipExists {
		return domain.Project{}, ErrForbidden
	}

	var workRequest domain.WorkRequest
	row := tx.QueryRowContext(ctx, `
		select id, property_id, requested_by_user_id, title, category, area, urgency, description, preferred_timing, status, created_at
		from work_requests
		where id = $1
		for update
	`, strings.TrimSpace(input.WorkRequestID))
	if err := scanWorkRequestRow(row, &workRequest); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Project{}, ErrWorkRequestNotFound
		}
		return domain.Project{}, err
	}

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
		ContractorOrgID: strings.TrimSpace(input.OrganizationID),
		Title:           title,
		Status:          domain.ProjectStatusDraft,
		CreatedAt:       time.Now().UTC(),
	}

	_, err = tx.ExecContext(ctx, `
		insert into projects (id, property_id, work_request_id, contractor_org_id, title, status, created_at)
		values ($1,$2,$3,$4,$5,$6,$7)
	`, project.ID, project.PropertyID, project.WorkRequestID, project.ContractorOrgID, project.Title, string(project.Status), project.CreatedAt)
	if err != nil {
		return domain.Project{}, err
	}

	_, err = tx.ExecContext(ctx, `
		update work_requests
		set status = $2
		where id = $1
	`, workRequest.ID, string(domain.WorkRequestStatusConverted))
	if err != nil {
		return domain.Project{}, err
	}

	_, err = tx.ExecContext(ctx, `
		insert into property_assignments (property_id, organization_id, relationship_type, created_at)
		values ($1,$2,$3,$4)
		on conflict (property_id, organization_id) do update set relationship_type = excluded.relationship_type
	`, project.PropertyID, project.ContractorOrgID, "service_provider", time.Now().UTC())
	if err != nil {
		return domain.Project{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.Project{}, err
	}
	return project, nil
}

func (s *PostgresStore) ListProjectsForHomeowner(ctx context.Context, homeownerUserID string) ([]domain.ProjectWorkspaceItem, error) {
	rows, err := s.db.QueryContext(ctx, projectWorkspaceSelect+`
		where p.homeowner_user_id = $1
		order by pr.created_at desc
	`, strings.TrimSpace(homeownerUserID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]domain.ProjectWorkspaceItem, 0)
	for rows.Next() {
		item, err := scanProjectWorkspaceItem(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, item)
	}
	return out, rows.Err()
}

func (s *PostgresStore) ListProjectsForContractor(ctx context.Context, contractorUserID string) ([]domain.ProjectWorkspaceItem, error) {
	rows, err := s.db.QueryContext(ctx, projectWorkspaceSelect+`
		join organization_members om on om.organization_id = pr.contractor_org_id
		where om.user_id = $1
		order by pr.created_at desc
	`, strings.TrimSpace(contractorUserID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	out := make([]domain.ProjectWorkspaceItem, 0)
	for rows.Next() {
		item, err := scanProjectWorkspaceItem(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, item)
	}
	return out, rows.Err()
}

func (s *PostgresStore) GetProjectDetailForHomeowner(ctx context.Context, homeownerUserID string, projectID string) (domain.ProjectDetail, error) {
	row := s.db.QueryRowContext(ctx, projectWorkspaceSelect+`
		where p.homeowner_user_id = $1 and pr.id = $2
	`, strings.TrimSpace(homeownerUserID), strings.TrimSpace(projectID))

	item, err := scanProjectWorkspaceItem(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.ProjectDetail{}, ErrProjectNotFound
		}
		return domain.ProjectDetail{}, err
	}
	if item.WorkRequest != nil {
		item.WorkRequest.Attachments, err = s.listWorkRequestAttachmentsByID(ctx, item.WorkRequest.ID)
		if err != nil {
			return domain.ProjectDetail{}, err
		}
	}
	estimates, err := s.ListEstimatesForProject(ctx, item.Project.ID)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
	appointments, err := s.ListAppointmentsForProject(ctx, item.Project.ID)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
	invoices, err := s.ListInvoicesForProject(ctx, item.Project.ID)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
	messages, err := s.listMessagesForProjectUsing(ctx, s.db, item.Project.ID, false)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
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

func (s *PostgresStore) GetProjectDetailForContractor(ctx context.Context, contractorUserID string, projectID string) (domain.ProjectDetail, error) {
	row := s.db.QueryRowContext(ctx, projectWorkspaceSelect+`
		join organization_members om on om.organization_id = pr.contractor_org_id
		where om.user_id = $1 and pr.id = $2
	`, strings.TrimSpace(contractorUserID), strings.TrimSpace(projectID))

	item, err := scanProjectWorkspaceItem(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.ProjectDetail{}, ErrProjectNotFound
		}
		return domain.ProjectDetail{}, err
	}
	if item.WorkRequest != nil {
		item.WorkRequest.Attachments, err = s.listWorkRequestAttachmentsByID(ctx, item.WorkRequest.ID)
		if err != nil {
			return domain.ProjectDetail{}, err
		}
	}
	estimates, err := s.ListEstimatesForProject(ctx, item.Project.ID)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
	appointments, err := s.ListAppointmentsForProject(ctx, item.Project.ID)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
	invoices, err := s.ListInvoicesForProject(ctx, item.Project.ID)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
	messages, err := s.listMessagesForProjectUsing(ctx, s.db, item.Project.ID, true)
	if err != nil {
		return domain.ProjectDetail{}, err
	}
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

func (s *PostgresStore) CreateEstimate(ctx context.Context, input CreateEstimateInput) (domain.Estimate, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Summary) == "" ||
		len(input.LineItems) == 0 {
		return domain.Estimate{}, ErrInvalidInput
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Estimate{}, err
	}
	defer rollback(tx)

	var projectID string
	var contractorOrgID sql.NullString
	if err := tx.QueryRowContext(ctx, `
		select id, contractor_org_id
		from projects
		where id = $1
	`, strings.TrimSpace(input.ProjectID)).Scan(&projectID, &contractorOrgID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Estimate{}, ErrProjectNotFound
		}
		return domain.Estimate{}, err
	}

	var membershipExists bool
	if err := tx.QueryRowContext(ctx, `
		select exists (
			select 1
			from organization_members
			where organization_id = $1 and user_id = $2
		)
	`, contractorOrgID.String, strings.TrimSpace(input.ContractorUserID)).Scan(&membershipExists); err != nil {
		return domain.Estimate{}, err
	}
	if !membershipExists {
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
		ProjectID:          projectID,
		ContractorOrgID:    contractorOrgID.String,
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

	_, err = tx.ExecContext(ctx, `
		insert into estimates (
			id, project_id, contractor_org_id, summary, notes, deposit_amount_cents, total_amount_cents, status, created_at, updated_at, sent_at, decided_at
		) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
	`, estimate.ID, estimate.ProjectID, estimate.ContractorOrgID, estimate.Summary, estimate.Notes, estimate.DepositAmountCents, estimate.TotalAmountCents, string(estimate.Status), estimate.CreatedAt, estimate.UpdatedAt, estimate.SentAt, estimate.DecidedAt)
	if err != nil {
		return domain.Estimate{}, err
	}

	for _, item := range estimate.LineItems {
		if _, err := tx.ExecContext(ctx, `
			insert into estimate_line_items (id, estimate_id, label, amount_cents, position)
			values ($1,$2,$3,$4,$5)
		`, item.ID, estimate.ID, item.Label, item.AmountCents, item.Position); err != nil {
			return domain.Estimate{}, err
		}
	}

	if err := tx.Commit(); err != nil {
		return domain.Estimate{}, err
	}
	return estimate, nil
}

func (s *PostgresStore) ApproveEstimate(ctx context.Context, homeownerUserID string, projectID string, estimateID string) (domain.Estimate, error) {
	return s.decideEstimate(ctx, homeownerUserID, projectID, estimateID, domain.EstimateStatusApproved)
}

func (s *PostgresStore) RejectEstimate(ctx context.Context, homeownerUserID string, projectID string, estimateID string) (domain.Estimate, error) {
	return s.decideEstimate(ctx, homeownerUserID, projectID, estimateID, domain.EstimateStatusRejected)
}

func (s *PostgresStore) ListEstimatesForProject(ctx context.Context, projectID string) ([]domain.Estimate, error) {
	return s.listEstimatesForProjectUsing(ctx, s.db, strings.TrimSpace(projectID))
}

func (s *PostgresStore) CreateAppointment(ctx context.Context, input CreateAppointmentInput) (domain.Appointment, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Title) == "" ||
		input.StartsAt.IsZero() ||
		input.EndsAt.IsZero() ||
		!input.EndsAt.After(input.StartsAt) {
		return domain.Appointment{}, ErrInvalidInput
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Appointment{}, err
	}
	defer rollback(tx)

	var projectID string
	var contractorOrgID sql.NullString
	if err := tx.QueryRowContext(ctx, `
		select id, contractor_org_id
		from projects
		where id = $1
	`, strings.TrimSpace(input.ProjectID)).Scan(&projectID, &contractorOrgID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Appointment{}, ErrProjectNotFound
		}
		return domain.Appointment{}, err
	}

	var membershipExists bool
	if err := tx.QueryRowContext(ctx, `
		select exists (
			select 1
			from organization_members
			where organization_id = $1 and user_id = $2
		)
	`, contractorOrgID.String, strings.TrimSpace(input.ContractorUserID)).Scan(&membershipExists); err != nil {
		return domain.Appointment{}, err
	}
	if !membershipExists {
		return domain.Appointment{}, ErrForbidden
	}

	appointment := domain.Appointment{
		ID:              newID("apt"),
		ProjectID:       projectID,
		ContractorOrgID: contractorOrgID.String,
		Title:           strings.TrimSpace(input.Title),
		Notes:           strings.TrimSpace(input.Notes),
		StartsAt:        input.StartsAt.UTC(),
		EndsAt:          input.EndsAt.UTC(),
		Status:          domain.AppointmentStatusScheduled,
		CreatedAt:       time.Now().UTC(),
	}

	if _, err := tx.ExecContext(ctx, `
		insert into appointments (id, project_id, contractor_org_id, title, notes, starts_at, ends_at, status, created_at)
		values ($1,$2,$3,$4,$5,$6,$7,$8,$9)
	`, appointment.ID, appointment.ProjectID, appointment.ContractorOrgID, appointment.Title, appointment.Notes, appointment.StartsAt, appointment.EndsAt, string(appointment.Status), appointment.CreatedAt); err != nil {
		return domain.Appointment{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.Appointment{}, err
	}
	return appointment, nil
}

func (s *PostgresStore) ListAppointmentsForProject(ctx context.Context, projectID string) ([]domain.Appointment, error) {
	rows, err := s.db.QueryContext(ctx, `
		select id, project_id, contractor_org_id, title, notes, starts_at, ends_at, status, created_at
		from appointments
		where project_id = $1
		order by starts_at asc, created_at asc
	`, strings.TrimSpace(projectID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	appointments := make([]domain.Appointment, 0)
	for rows.Next() {
		appointment, err := scanAppointment(rows)
		if err != nil {
			return nil, err
		}
		appointments = append(appointments, appointment)
	}
	return appointments, rows.Err()
}

func (s *PostgresStore) CreateInvoice(ctx context.Context, input CreateInvoiceInput) (domain.Invoice, error) {
	if strings.TrimSpace(input.ContractorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Summary) == "" ||
		input.AmountCents <= 0 ||
		input.DueAt.IsZero() {
		return domain.Invoice{}, ErrInvalidInput
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Invoice{}, err
	}
	defer rollback(tx)

	var projectID string
	var contractorOrgID sql.NullString
	if err := tx.QueryRowContext(ctx, `
		select id, contractor_org_id
		from projects
		where id = $1
	`, strings.TrimSpace(input.ProjectID)).Scan(&projectID, &contractorOrgID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Invoice{}, ErrProjectNotFound
		}
		return domain.Invoice{}, err
	}

	var membershipExists bool
	if err := tx.QueryRowContext(ctx, `
		select exists (
			select 1
			from organization_members
			where organization_id = $1 and user_id = $2
		)
	`, contractorOrgID.String, strings.TrimSpace(input.ContractorUserID)).Scan(&membershipExists); err != nil {
		return domain.Invoice{}, err
	}
	if !membershipExists {
		return domain.Invoice{}, ErrForbidden
	}

	now := time.Now().UTC()
	invoice := domain.Invoice{
		ID:                     newID("inv"),
		ProjectID:              projectID,
		ContractorOrgID:        contractorOrgID.String,
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

	if _, err := tx.ExecContext(ctx, `
		insert into invoices (
			id, project_id, contractor_org_id, summary, notes, amount_cents, amount_paid_cents, outstanding_amount_cents, status, due_at, created_at, updated_at, issued_at, paid_at
		) values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
	`, invoice.ID, invoice.ProjectID, invoice.ContractorOrgID, invoice.Summary, invoice.Notes, invoice.AmountCents, invoice.AmountPaidCents, invoice.OutstandingAmountCents, string(invoice.Status), invoice.DueAt, invoice.CreatedAt, invoice.UpdatedAt, invoice.IssuedAt, invoice.PaidAt); err != nil {
		return domain.Invoice{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.Invoice{}, err
	}
	return invoice, nil
}

func (s *PostgresStore) RecordInvoicePayment(ctx context.Context, input RecordInvoicePaymentInput) (domain.Invoice, error) {
	if strings.TrimSpace(input.HomeownerUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.InvoiceID) == "" ||
		input.AmountCents <= 0 {
		return domain.Invoice{}, ErrInvalidInput
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Invoice{}, err
	}
	defer rollback(tx)

	var ownerID string
	if err := tx.QueryRowContext(ctx, `
		select p.homeowner_user_id
		from projects pr
		join properties p on p.id = pr.property_id
		where pr.id = $1
	`, strings.TrimSpace(input.ProjectID)).Scan(&ownerID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Invoice{}, ErrProjectNotFound
		}
		return domain.Invoice{}, err
	}
	if ownerID != strings.TrimSpace(input.HomeownerUserID) {
		return domain.Invoice{}, ErrProjectNotFound
	}

	var totalAmount int64
	var paidAmount int64
	var outstandingAmount int64
	var status string
	if err := tx.QueryRowContext(ctx, `
		select amount_cents, amount_paid_cents, outstanding_amount_cents, status
		from invoices
		where id = $1 and project_id = $2
		for update
	`, strings.TrimSpace(input.InvoiceID), strings.TrimSpace(input.ProjectID)).Scan(&totalAmount, &paidAmount, &outstandingAmount, &status); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Invoice{}, ErrInvoiceNotFound
		}
		return domain.Invoice{}, err
	}
	if outstandingAmount <= 0 || domain.InvoiceStatus(status) == domain.InvoiceStatusPaid {
		return domain.Invoice{}, ErrInvoiceUnavailable
	}
	if input.AmountCents > outstandingAmount {
		return domain.Invoice{}, ErrInvalidInput
	}

	now := time.Now().UTC()
	payment := domain.Payment{
		ID:          newID("pay"),
		InvoiceID:   strings.TrimSpace(input.InvoiceID),
		PayerUserID: strings.TrimSpace(input.HomeownerUserID),
		AmountCents: input.AmountCents,
		Note:        strings.TrimSpace(input.Note),
		PaidAt:      now,
		CreatedAt:   now,
	}

	if _, err := tx.ExecContext(ctx, `
		insert into invoice_payments (id, invoice_id, payer_user_id, amount_cents, note, paid_at, created_at)
		values ($1,$2,$3,$4,$5,$6,$7)
	`, payment.ID, payment.InvoiceID, payment.PayerUserID, payment.AmountCents, payment.Note, payment.PaidAt, payment.CreatedAt); err != nil {
		return domain.Invoice{}, err
	}

	newPaid := paidAmount + input.AmountCents
	newOutstanding := totalAmount - newPaid
	newStatus := domain.InvoiceStatusPartiallyPaid
	var paidAt *time.Time
	if newOutstanding == 0 {
		newStatus = domain.InvoiceStatusPaid
		paidAt = &now
	} else if newPaid == 0 {
		newStatus = domain.InvoiceStatusSent
	}

	if _, err := tx.ExecContext(ctx, `
		update invoices
		set amount_paid_cents = $2, outstanding_amount_cents = $3, status = $4, updated_at = $5, paid_at = $6
		where id = $1
	`, strings.TrimSpace(input.InvoiceID), newPaid, newOutstanding, string(newStatus), now, paidAt); err != nil {
		return domain.Invoice{}, err
	}

	invoice, err := s.getInvoiceByIDUsing(ctx, tx, strings.TrimSpace(input.InvoiceID))
	if err != nil {
		return domain.Invoice{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.Invoice{}, err
	}
	return invoice, nil
}

func (s *PostgresStore) ListInvoicesForProject(ctx context.Context, projectID string) ([]domain.Invoice, error) {
	return s.listInvoicesForProjectUsing(ctx, s.db, strings.TrimSpace(projectID))
}

func (s *PostgresStore) CreateProjectMessage(ctx context.Context, input CreateProjectMessageInput) (domain.ProjectMessage, error) {
	if strings.TrimSpace(input.AuthorUserID) == "" ||
		strings.TrimSpace(input.ProjectID) == "" ||
		strings.TrimSpace(input.Body) == "" {
		return domain.ProjectMessage{}, ErrInvalidInput
	}

	if input.Visibility != domain.MessageVisibilityShared && input.Visibility != domain.MessageVisibilityInternal {
		return domain.ProjectMessage{}, ErrInvalidInput
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.ProjectMessage{}, err
	}
	defer rollback(tx)

	var projectID string
	var contractorOrgID sql.NullString
	var homeownerUserID string
	if err := tx.QueryRowContext(ctx, `
		select pr.id, pr.contractor_org_id, p.homeowner_user_id
		from projects pr
		join properties p on p.id = pr.property_id
		where pr.id = $1
	`, strings.TrimSpace(input.ProjectID)).Scan(&projectID, &contractorOrgID, &homeownerUserID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.ProjectMessage{}, ErrProjectNotFound
		}
		return domain.ProjectMessage{}, err
	}

	switch input.AuthorRole {
	case domain.RoleHomeowner:
		if homeownerUserID != strings.TrimSpace(input.AuthorUserID) {
			return domain.ProjectMessage{}, ErrProjectNotFound
		}
		if input.Visibility != domain.MessageVisibilityShared {
			return domain.ProjectMessage{}, ErrForbidden
		}
	case domain.RoleContractor, domain.RoleContractorAdmin, domain.RoleCrewMember:
		var membershipExists bool
		if err := tx.QueryRowContext(ctx, `
			select exists (
				select 1
				from organization_members
				where organization_id = $1 and user_id = $2
			)
		`, contractorOrgID.String, strings.TrimSpace(input.AuthorUserID)).Scan(&membershipExists); err != nil {
			return domain.ProjectMessage{}, err
		}
		if !membershipExists {
			return domain.ProjectMessage{}, ErrForbidden
		}
	default:
		return domain.ProjectMessage{}, ErrForbidden
	}

	message := domain.ProjectMessage{
		ID:           newID("msg"),
		ProjectID:    projectID,
		AuthorUserID: strings.TrimSpace(input.AuthorUserID),
		AuthorRole:   input.AuthorRole,
		Visibility:   input.Visibility,
		Body:         strings.TrimSpace(input.Body),
		CreatedAt:    time.Now().UTC(),
	}

	if _, err := tx.ExecContext(ctx, `
		insert into project_messages (id, project_id, author_user_id, author_role, visibility, body, created_at)
		values ($1,$2,$3,$4,$5,$6,$7)
	`, message.ID, message.ProjectID, message.AuthorUserID, string(message.AuthorRole), string(message.Visibility), message.Body, message.CreatedAt); err != nil {
		return domain.ProjectMessage{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.ProjectMessage{}, err
	}
	return message, nil
}

func (s *PostgresStore) latestEstimateForProject(ctx context.Context, projectID string) (domain.Estimate, bool, error) {
	estimates, err := s.ListEstimatesForProject(ctx, projectID)
	if err != nil {
		return domain.Estimate{}, false, err
	}
	if len(estimates) == 0 {
		return domain.Estimate{}, false, nil
	}
	return estimates[0], true, nil
}

func (s *PostgresStore) decideEstimate(ctx context.Context, homeownerUserID string, projectID string, estimateID string, status domain.EstimateStatus) (domain.Estimate, error) {
	if strings.TrimSpace(homeownerUserID) == "" || strings.TrimSpace(projectID) == "" || strings.TrimSpace(estimateID) == "" {
		return domain.Estimate{}, ErrInvalidInput
	}

	tx, err := s.db.BeginTx(ctx, nil)
	if err != nil {
		return domain.Estimate{}, err
	}
	defer rollback(tx)

	var ownerID string
	if err := tx.QueryRowContext(ctx, `
		select p.homeowner_user_id
		from projects pr
		join properties p on p.id = pr.property_id
		where pr.id = $1
	`, strings.TrimSpace(projectID)).Scan(&ownerID); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Estimate{}, ErrProjectNotFound
		}
		return domain.Estimate{}, err
	}
	if ownerID != strings.TrimSpace(homeownerUserID) {
		return domain.Estimate{}, ErrProjectNotFound
	}

	var currentStatus string
	if err := tx.QueryRowContext(ctx, `
		select status
		from estimates
		where id = $1 and project_id = $2
		for update
	`, strings.TrimSpace(estimateID), strings.TrimSpace(projectID)).Scan(&currentStatus); err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Estimate{}, ErrEstimateNotFound
		}
		return domain.Estimate{}, err
	}
	if domain.EstimateStatus(currentStatus) != domain.EstimateStatusSent {
		return domain.Estimate{}, ErrEstimateUnavailable
	}

	now := time.Now().UTC()
	if _, err := tx.ExecContext(ctx, `
		update estimates
		set status = $2, updated_at = $3, decided_at = $3
		where id = $1
	`, strings.TrimSpace(estimateID), string(status), now); err != nil {
		return domain.Estimate{}, err
	}

	if status == domain.EstimateStatusApproved {
		if _, err := tx.ExecContext(ctx, `
			update projects
			set status = $2
			where id = $1
		`, strings.TrimSpace(projectID), string(domain.ProjectStatusApproved)); err != nil {
			return domain.Estimate{}, err
		}
	}

	estimate, err := s.getEstimateByIDUsing(ctx, tx, strings.TrimSpace(estimateID))
	if err != nil {
		return domain.Estimate{}, err
	}

	if err := tx.Commit(); err != nil {
		return domain.Estimate{}, err
	}
	return estimate, nil
}

func scanProperty(scanner interface{ Scan(...any) error }) (domain.Property, error) {
	var property domain.Property
	err := scanner.Scan(
		&property.ID,
		&property.HomeownerUserID,
		&property.Label,
		&property.AddressLine1,
		&property.AddressLine2,
		&property.City,
		&property.Region,
		&property.PostalCode,
		&property.CountryCode,
		&property.CreatedAt,
	)
	return property, err
}

func scanWorkRequest(scanner interface{ Scan(...any) error }) (domain.WorkRequest, error) {
	workRequest := domain.WorkRequest{Attachments: []domain.Attachment{}}
	err := scanWorkRequestRow(scanner, &workRequest)
	return workRequest, err
}

func scanWorkRequestRow(scanner interface{ Scan(...any) error }, workRequest *domain.WorkRequest) error {
	var status string
	if err := scanner.Scan(
		&workRequest.ID,
		&workRequest.PropertyID,
		&workRequest.RequestedByUserID,
		&workRequest.Title,
		&workRequest.Category,
		&workRequest.Area,
		&workRequest.Urgency,
		&workRequest.Description,
		&workRequest.PreferredTiming,
		&status,
		&workRequest.CreatedAt,
	); err != nil {
		return err
	}
	workRequest.Status = domain.WorkRequestStatus(status)
	return nil
}

func scanInboxItem(scanner interface{ Scan(...any) error }) (domain.WorkRequest, domain.Property, error) {
	workRequest := domain.WorkRequest{Attachments: []domain.Attachment{}}
	var property domain.Property
	var status string
	err := scanner.Scan(
		&workRequest.ID,
		&workRequest.PropertyID,
		&workRequest.RequestedByUserID,
		&workRequest.Title,
		&workRequest.Category,
		&workRequest.Area,
		&workRequest.Urgency,
		&workRequest.Description,
		&workRequest.PreferredTiming,
		&status,
		&workRequest.CreatedAt,
		&property.ID,
		&property.HomeownerUserID,
		&property.Label,
		&property.AddressLine1,
		&property.AddressLine2,
		&property.City,
		&property.Region,
		&property.PostalCode,
		&property.CountryCode,
		&property.CreatedAt,
	)
	workRequest.Status = domain.WorkRequestStatus(status)
	return workRequest, property, err
}

const projectWorkspaceSelect = `
	select
		pr.id, pr.property_id, pr.work_request_id, pr.contractor_org_id, pr.title, pr.status, pr.created_at,
		p.id, p.homeowner_user_id, p.label, p.address_line_1, p.address_line_2, p.city, p.region, p.postal_code, p.country_code, p.created_at,
		wr.id, wr.property_id, wr.requested_by_user_id, wr.title, wr.category, wr.area, wr.urgency, wr.description, wr.preferred_timing, wr.status, wr.created_at
	from projects pr
	join properties p on p.id = pr.property_id
	left join work_requests wr on wr.id = pr.work_request_id
`

func scanProjectWorkspaceItem(scanner interface{ Scan(...any) error }) (domain.ProjectWorkspaceItem, error) {
	var item domain.ProjectWorkspaceItem
	var projectStatus string
	var requestStatus sql.NullString
	var requestID sql.NullString
	var requestPropertyID sql.NullString
	var requestUserID sql.NullString
	var requestTitle sql.NullString
	var requestCategory sql.NullString
	var requestArea sql.NullString
	var requestUrgency sql.NullString
	var requestDescription sql.NullString
	var requestPreferredTiming sql.NullString
	var requestCreatedAt sql.NullTime

	err := scanner.Scan(
		&item.Project.ID,
		&item.Project.PropertyID,
		&item.Project.WorkRequestID,
		&item.Project.ContractorOrgID,
		&item.Project.Title,
		&projectStatus,
		&item.Project.CreatedAt,
		&item.Property.ID,
		&item.Property.HomeownerUserID,
		&item.Property.Label,
		&item.Property.AddressLine1,
		&item.Property.AddressLine2,
		&item.Property.City,
		&item.Property.Region,
		&item.Property.PostalCode,
		&item.Property.CountryCode,
		&item.Property.CreatedAt,
		&requestID,
		&requestPropertyID,
		&requestUserID,
		&requestTitle,
		&requestCategory,
		&requestArea,
		&requestUrgency,
		&requestDescription,
		&requestPreferredTiming,
		&requestStatus,
		&requestCreatedAt,
	)
	if err != nil {
		return domain.ProjectWorkspaceItem{}, err
	}

	item.Project.Status = domain.ProjectStatus(projectStatus)
	if requestID.Valid {
		item.WorkRequest = &domain.WorkRequest{
			ID:                requestID.String,
			PropertyID:        requestPropertyID.String,
			RequestedByUserID: requestUserID.String,
			Title:             requestTitle.String,
			Category:          requestCategory.String,
			Area:              requestArea.String,
			Urgency:           requestUrgency.String,
			Description:       requestDescription.String,
			PreferredTiming:   requestPreferredTiming.String,
			Status:            domain.WorkRequestStatus(requestStatus.String),
			Attachments:       []domain.Attachment{},
			CreatedAt:         requestCreatedAt.Time,
		}
	}
	return item, nil
}

type sqlQuerier interface {
	QueryContext(context.Context, string, ...any) (*sql.Rows, error)
	QueryRowContext(context.Context, string, ...any) *sql.Row
}

func (s *PostgresStore) listEstimatesForProjectUsing(ctx context.Context, db sqlQuerier, projectID string) ([]domain.Estimate, error) {
	rows, err := db.QueryContext(ctx, `
		select id, project_id, contractor_org_id, summary, notes, deposit_amount_cents, total_amount_cents, status, created_at, updated_at, sent_at, decided_at
		from estimates
		where project_id = $1
		order by created_at desc
	`, strings.TrimSpace(projectID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	estimates := make([]domain.Estimate, 0)
	for rows.Next() {
		estimate, err := scanEstimate(rows)
		if err != nil {
			return nil, err
		}
		estimates = append(estimates, estimate)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	for idx := range estimates {
		lineItems, err := listEstimateLineItemsUsing(ctx, db, estimates[idx].ID)
		if err != nil {
			return nil, err
		}
		estimates[idx].LineItems = lineItems
	}

	return estimates, nil
}

func (s *PostgresStore) getEstimateByIDUsing(ctx context.Context, db sqlQuerier, estimateID string) (domain.Estimate, error) {
	row := db.QueryRowContext(ctx, `
		select id, project_id, contractor_org_id, summary, notes, deposit_amount_cents, total_amount_cents, status, created_at, updated_at, sent_at, decided_at
		from estimates
		where id = $1
	`, strings.TrimSpace(estimateID))

	estimate, err := scanEstimate(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Estimate{}, ErrEstimateNotFound
		}
		return domain.Estimate{}, err
	}

	lineItems, err := listEstimateLineItemsUsing(ctx, db, estimate.ID)
	if err != nil {
		return domain.Estimate{}, err
	}
	estimate.LineItems = lineItems

	return estimate, nil
}

func listEstimateLineItemsUsing(ctx context.Context, db sqlQuerier, estimateID string) ([]domain.EstimateLineItem, error) {
	rows, err := db.QueryContext(ctx, `
		select id, label, amount_cents, position
		from estimate_line_items
		where estimate_id = $1
		order by position asc, id asc
	`, strings.TrimSpace(estimateID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	lineItems := make([]domain.EstimateLineItem, 0)
	for rows.Next() {
		var item domain.EstimateLineItem
		if err := rows.Scan(&item.ID, &item.Label, &item.AmountCents, &item.Position); err != nil {
			return nil, err
		}
		lineItems = append(lineItems, item)
	}
	return lineItems, rows.Err()
}

func (s *PostgresStore) listInvoicesForProjectUsing(ctx context.Context, db sqlQuerier, projectID string) ([]domain.Invoice, error) {
	rows, err := db.QueryContext(ctx, `
		select id, project_id, contractor_org_id, summary, notes, amount_cents, amount_paid_cents, outstanding_amount_cents, status, due_at, created_at, updated_at, issued_at, paid_at
		from invoices
		where project_id = $1
		order by created_at desc
	`, strings.TrimSpace(projectID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	invoices := make([]domain.Invoice, 0)
	for rows.Next() {
		invoice, err := scanInvoice(rows)
		if err != nil {
			return nil, err
		}
		invoices = append(invoices, invoice)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	for idx := range invoices {
		payments, err := listInvoicePaymentsUsing(ctx, db, invoices[idx].ID)
		if err != nil {
			return nil, err
		}
		invoices[idx].Payments = payments
	}

	return invoices, nil
}

func (s *PostgresStore) getInvoiceByIDUsing(ctx context.Context, db sqlQuerier, invoiceID string) (domain.Invoice, error) {
	row := db.QueryRowContext(ctx, `
		select id, project_id, contractor_org_id, summary, notes, amount_cents, amount_paid_cents, outstanding_amount_cents, status, due_at, created_at, updated_at, issued_at, paid_at
		from invoices
		where id = $1
	`, strings.TrimSpace(invoiceID))

	invoice, err := scanInvoice(row)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return domain.Invoice{}, ErrInvoiceNotFound
		}
		return domain.Invoice{}, err
	}

	payments, err := listInvoicePaymentsUsing(ctx, db, invoice.ID)
	if err != nil {
		return domain.Invoice{}, err
	}
	invoice.Payments = payments

	return invoice, nil
}

func listInvoicePaymentsUsing(ctx context.Context, db sqlQuerier, invoiceID string) ([]domain.Payment, error) {
	rows, err := db.QueryContext(ctx, `
		select id, invoice_id, payer_user_id, amount_cents, note, paid_at, created_at
		from invoice_payments
		where invoice_id = $1
		order by paid_at desc, created_at desc
	`, strings.TrimSpace(invoiceID))
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	payments := make([]domain.Payment, 0)
	for rows.Next() {
		var payment domain.Payment
		if err := rows.Scan(&payment.ID, &payment.InvoiceID, &payment.PayerUserID, &payment.AmountCents, &payment.Note, &payment.PaidAt, &payment.CreatedAt); err != nil {
			return nil, err
		}
		payments = append(payments, payment)
	}
	return payments, rows.Err()
}

func (s *PostgresStore) listMessagesForProjectUsing(ctx context.Context, db sqlQuerier, projectID string, includeInternal bool) ([]domain.ProjectMessage, error) {
	query := `
		select id, project_id, author_user_id, author_role, visibility, body, created_at
		from project_messages
		where project_id = $1
	`
	args := []any{strings.TrimSpace(projectID)}
	if !includeInternal {
		query += ` and visibility = $2`
		args = append(args, string(domain.MessageVisibilityShared))
	}
	query += ` order by created_at asc, id asc`

	rows, err := db.QueryContext(ctx, query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	messages := make([]domain.ProjectMessage, 0)
	for rows.Next() {
		message, err := scanProjectMessage(rows)
		if err != nil {
			return nil, err
		}
		messages = append(messages, message)
	}
	return messages, rows.Err()
}

func scanEstimate(scanner interface{ Scan(...any) error }) (domain.Estimate, error) {
	var estimate domain.Estimate
	var status string
	var sentAt sql.NullTime
	var decidedAt sql.NullTime
	if err := scanner.Scan(
		&estimate.ID,
		&estimate.ProjectID,
		&estimate.ContractorOrgID,
		&estimate.Summary,
		&estimate.Notes,
		&estimate.DepositAmountCents,
		&estimate.TotalAmountCents,
		&status,
		&estimate.CreatedAt,
		&estimate.UpdatedAt,
		&sentAt,
		&decidedAt,
	); err != nil {
		return domain.Estimate{}, err
	}

	estimate.Status = domain.EstimateStatus(status)
	if sentAt.Valid {
		estimate.SentAt = &sentAt.Time
	}
	if decidedAt.Valid {
		estimate.DecidedAt = &decidedAt.Time
	}

	return estimate, nil
}

func scanAppointment(scanner interface{ Scan(...any) error }) (domain.Appointment, error) {
	var appointment domain.Appointment
	var status string
	if err := scanner.Scan(
		&appointment.ID,
		&appointment.ProjectID,
		&appointment.ContractorOrgID,
		&appointment.Title,
		&appointment.Notes,
		&appointment.StartsAt,
		&appointment.EndsAt,
		&status,
		&appointment.CreatedAt,
	); err != nil {
		return domain.Appointment{}, err
	}

	appointment.Status = domain.AppointmentStatus(status)
	return appointment, nil
}

func scanInvoice(scanner interface{ Scan(...any) error }) (domain.Invoice, error) {
	var invoice domain.Invoice
	var status string
	var paidAt sql.NullTime
	if err := scanner.Scan(
		&invoice.ID,
		&invoice.ProjectID,
		&invoice.ContractorOrgID,
		&invoice.Summary,
		&invoice.Notes,
		&invoice.AmountCents,
		&invoice.AmountPaidCents,
		&invoice.OutstandingAmountCents,
		&status,
		&invoice.DueAt,
		&invoice.CreatedAt,
		&invoice.UpdatedAt,
		&invoice.IssuedAt,
		&paidAt,
	); err != nil {
		return domain.Invoice{}, err
	}

	invoice.Status = domain.InvoiceStatus(status)
	if paidAt.Valid {
		invoice.PaidAt = &paidAt.Time
	}
	return invoice, nil
}

func scanProjectMessage(scanner interface{ Scan(...any) error }) (domain.ProjectMessage, error) {
	var message domain.ProjectMessage
	var role string
	var visibility string
	if err := scanner.Scan(
		&message.ID,
		&message.ProjectID,
		&message.AuthorUserID,
		&role,
		&visibility,
		&message.Body,
		&message.CreatedAt,
	); err != nil {
		return domain.ProjectMessage{}, err
	}

	message.AuthorRole = domain.Role(role)
	message.Visibility = domain.MessageVisibility(visibility)
	return message, nil
}

func rollback(tx *sql.Tx) {
	_ = tx.Rollback()
}
