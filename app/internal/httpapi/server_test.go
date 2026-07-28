package httpapi

import (
	"bytes"
	"context"
	"encoding/json"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/Fuzzyslippers412/Mycasapro/app/internal/config"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/domain"
	"github.com/Fuzzyslippers412/Mycasapro/app/internal/store"
)

func newTestServer() *http.Server {
	server := newRawTestServer()
	securedHandler := server.Handler
	server.Handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		scope, actorID, scoped := scopedActorPath(r.URL.Path)
		if scoped {
			role := domain.RoleHomeowner
			if scope == "contractors" {
				role = domain.RoleContractor
			}
			r = r.WithContext(context.WithValue(r.Context(), principalContextKey{}, domain.User{ID: actorID, Role: role}))
		}
		securedHandler.ServeHTTP(w, r)
	})
	return server
}

func newRawTestServer() *http.Server {
	return NewServerWithStore(config.Config{
		Addr:           ":0",
		Env:            "test",
		AppName:        "MyCasaPro",
		WebURL:         "http://localhost:3000",
		AllowedOrigins: []string{"http://localhost:3000"},
	}, store.NewMemoryStore())
}

func TestRegisterCurrentUserAndLogout(t *testing.T) {
	server := newRawTestServer()
	registerBody := `{
		"display_name":"Amina Diallo",
		"email":"amina@example.com",
		"password":"correct-horse-battery",
		"role":"homeowner"
	}`
	registerReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/register", bytes.NewBufferString(registerBody))
	registerReq.Header.Set("Content-Type", "application/json")
	registerResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(registerResp, registerReq)
	if registerResp.Code != http.StatusCreated {
		t.Fatalf("register status mismatch: got=%d body=%s", registerResp.Code, registerResp.Body.String())
	}

	result := registerResp.Result()
	cookies := result.Cookies()
	if len(cookies) != 1 || cookies[0].Name != sessionCookieName || !cookies[0].HttpOnly {
		t.Fatalf("expected secure session cookie, got=%v", cookies)
	}

	meReq := httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	meReq.AddCookie(cookies[0])
	meResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(meResp, meReq)
	if meResp.Code != http.StatusOK {
		t.Fatalf("me status mismatch: got=%d body=%s", meResp.Code, meResp.Body.String())
	}

	logoutReq := httptest.NewRequest(http.MethodPost, "/api/v1/auth/logout", nil)
	logoutReq.AddCookie(cookies[0])
	logoutResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(logoutResp, logoutReq)
	if logoutResp.Code != http.StatusNoContent {
		t.Fatalf("logout status mismatch: got=%d", logoutResp.Code)
	}

	meAfterLogoutReq := httptest.NewRequest(http.MethodGet, "/api/v1/auth/me", nil)
	meAfterLogoutReq.AddCookie(cookies[0])
	meAfterLogoutResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(meAfterLogoutResp, meAfterLogoutReq)
	if meAfterLogoutResp.Code != http.StatusUnauthorized {
		t.Fatalf("expected logged out session, got=%d", meAfterLogoutResp.Code)
	}
}

func TestScopedRoutesRequireMatchingAuthenticatedUser(t *testing.T) {
	server := newRawTestServer()
	req := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/usr-private/dashboard", nil)
	resp := httptest.NewRecorder()
	server.Handler.ServeHTTP(resp, req)
	if resp.Code != http.StatusUnauthorized {
		t.Fatalf("expected unauthorized route, got=%d body=%s", resp.Code, resp.Body.String())
	}
}

func TestHealthRoute(t *testing.T) {
	server := newTestServer()

	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	resp := httptest.NewRecorder()
	server.Handler.ServeHTTP(resp, req)

	if resp.Code != http.StatusOK {
		t.Fatalf("status mismatch: got=%d want=%d", resp.Code, http.StatusOK)
	}

	var payload map[string]any
	if err := json.Unmarshal(resp.Body.Bytes(), &payload); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if payload["service"] != "mycasapro-app" {
		t.Fatalf("service mismatch: got=%v", payload["service"])
	}
}

func TestMetaRoute(t *testing.T) {
	server := newTestServer()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/meta", nil)
	resp := httptest.NewRecorder()
	server.Handler.ServeHTTP(resp, req)

	if resp.Code != http.StatusOK {
		t.Fatalf("status mismatch: got=%d want=%d", resp.Code, http.StatusOK)
	}

	var payload struct {
		Product string   `json:"product"`
		Modules []string `json:"modules"`
	}
	if err := json.Unmarshal(resp.Body.Bytes(), &payload); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if payload.Product != "home-maintenance" {
		t.Fatalf("product mismatch: got=%q", payload.Product)
	}
	if len(payload.Modules) == 0 {
		t.Fatal("expected modules")
	}
}

func TestCreatePropertyAndDashboardFlow(t *testing.T) {
	server := newTestServer()
	homeownerID := "homeowner-1"

	propertyBody := `{
		"label":"Main House",
		"address_line_1":"123 Cedar St",
		"city":"Oakland",
		"region":"CA",
		"postal_code":"94607",
		"country_code":"US"
	}`
	propertyReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/properties", bytes.NewBufferString(propertyBody))
	propertyReq.Header.Set("Content-Type", "application/json")
	propertyResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(propertyResp, propertyReq)

	if propertyResp.Code != http.StatusCreated {
		t.Fatalf("create property status mismatch: got=%d body=%s", propertyResp.Code, propertyResp.Body.String())
	}

	var property domain.Property
	if err := json.Unmarshal(propertyResp.Body.Bytes(), &property); err != nil {
		t.Fatalf("unmarshal property: %v", err)
	}
	if property.ID == "" {
		t.Fatal("expected property id")
	}

	workRequestBody, _ := json.Marshal(map[string]string{
		"property_id":      property.ID,
		"title":            "Kitchen sink leak",
		"category":         "plumbing",
		"area":             "kitchen",
		"urgency":          "high",
		"description":      "Water is pooling under the sink every night.",
		"preferred_timing": "weekday mornings",
	})
	workReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests", bytes.NewBuffer(workRequestBody))
	workReq.Header.Set("Content-Type", "application/json")
	workResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(workResp, workReq)

	if workResp.Code != http.StatusCreated {
		t.Fatalf("create work request status mismatch: got=%d body=%s", workResp.Code, workResp.Body.String())
	}

	dashboardReq := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/"+homeownerID+"/dashboard", nil)
	dashboardResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(dashboardResp, dashboardReq)

	if dashboardResp.Code != http.StatusOK {
		t.Fatalf("dashboard status mismatch: got=%d body=%s", dashboardResp.Code, dashboardResp.Body.String())
	}

	var dashboard domain.HomeownerDashboard
	if err := json.Unmarshal(dashboardResp.Body.Bytes(), &dashboard); err != nil {
		t.Fatalf("unmarshal dashboard: %v", err)
	}
	if dashboard.Summary.PropertyCount != 1 {
		t.Fatalf("property count mismatch: got=%d", dashboard.Summary.PropertyCount)
	}
	if dashboard.Summary.OpenRepairCount != 1 {
		t.Fatalf("open repair count mismatch: got=%d", dashboard.Summary.OpenRepairCount)
	}
	if len(dashboard.Properties) != 1 {
		t.Fatalf("properties length mismatch: got=%d", len(dashboard.Properties))
	}
	if len(dashboard.WorkRequests) != 1 {
		t.Fatalf("work requests length mismatch: got=%d", len(dashboard.WorkRequests))
	}
}

func TestCreateWorkRequestRequiresOwnedProperty(t *testing.T) {
	server := newTestServer()

	body := `{
		"property_id":"prop-missing",
		"title":"Broken window latch",
		"category":"windows",
		"area":"bedroom",
		"urgency":"medium",
		"description":"Latch no longer closes."
	}`
	req := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/homeowner-2/work-requests", bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	resp := httptest.NewRecorder()
	server.Handler.ServeHTTP(resp, req)

	if resp.Code != http.StatusNotFound {
		t.Fatalf("status mismatch: got=%d body=%s", resp.Code, resp.Body.String())
	}
}

func TestListPropertiesEmptyState(t *testing.T) {
	server := newTestServer()

	req := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/homeowner-empty/properties", nil)
	resp := httptest.NewRecorder()
	server.Handler.ServeHTTP(resp, req)

	if resp.Code != http.StatusOK {
		t.Fatalf("status mismatch: got=%d body=%s", resp.Code, resp.Body.String())
	}

	var payload struct {
		Properties []domain.Property `json:"properties"`
	}
	if err := json.Unmarshal(resp.Body.Bytes(), &payload); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if len(payload.Properties) != 0 {
		t.Fatalf("expected empty properties, got=%d", len(payload.Properties))
	}
}

func TestContractorDashboardCanConvertRequestToProject(t *testing.T) {
	server := newTestServer()
	homeownerID := "homeowner-3"
	contractorID := "contractor-1"

	propertyBody := `{
		"label":"Rental House",
		"address_line_1":"8 Pine Ave",
		"city":"Portland",
		"region":"OR",
		"postal_code":"97205",
		"country_code":"US"
	}`
	propertyReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/properties", bytes.NewBufferString(propertyBody))
	propertyReq.Header.Set("Content-Type", "application/json")
	propertyResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(propertyResp, propertyReq)

	var property domain.Property
	if err := json.Unmarshal(propertyResp.Body.Bytes(), &property); err != nil {
		t.Fatalf("unmarshal property: %v", err)
	}

	workRequestBody, _ := json.Marshal(map[string]string{
		"property_id": property.ID,
		"title":       "Bathroom fan replacement",
		"category":    "electrical",
		"area":        "bathroom",
		"urgency":     "medium",
		"description": "The fan no longer turns on.",
	})
	workReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests", bytes.NewBuffer(workRequestBody))
	workReq.Header.Set("Content-Type", "application/json")
	workResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(workResp, workReq)

	var createdRequest domain.WorkRequest
	if err := json.Unmarshal(workResp.Body.Bytes(), &createdRequest); err != nil {
		t.Fatalf("unmarshal work request: %v", err)
	}

	orgReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations", bytes.NewBufferString(`{"name":"Northside Repairs"}`))
	orgReq.Header.Set("Content-Type", "application/json")
	orgResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(orgResp, orgReq)

	if orgResp.Code != http.StatusCreated {
		t.Fatalf("create org status mismatch: got=%d body=%s", orgResp.Code, orgResp.Body.String())
	}

	var organization domain.Organization
	if err := json.Unmarshal(orgResp.Body.Bytes(), &organization); err != nil {
		t.Fatalf("unmarshal org: %v", err)
	}

	dashboardReq := httptest.NewRequest(http.MethodGet, "/api/v1/contractors/"+contractorID+"/dashboard", nil)
	dashboardResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(dashboardResp, dashboardReq)
	if dashboardResp.Code != http.StatusOK {
		t.Fatalf("dashboard status mismatch: got=%d body=%s", dashboardResp.Code, dashboardResp.Body.String())
	}

	var dashboard domain.ContractorDashboard
	if err := json.Unmarshal(dashboardResp.Body.Bytes(), &dashboard); err != nil {
		t.Fatalf("unmarshal contractor dashboard: %v", err)
	}
	if dashboard.Summary.AvailableRequestCount != 1 {
		t.Fatalf("available request count mismatch: got=%d", dashboard.Summary.AvailableRequestCount)
	}

	projectBody, _ := json.Marshal(map[string]string{
		"work_request_id": createdRequest.ID,
	})
	projectReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations/"+organization.ID+"/projects", bytes.NewBuffer(projectBody))
	projectReq.Header.Set("Content-Type", "application/json")
	projectResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(projectResp, projectReq)
	if projectResp.Code != http.StatusCreated {
		t.Fatalf("project status mismatch: got=%d body=%s", projectResp.Code, projectResp.Body.String())
	}

	dashboardResp = httptest.NewRecorder()
	server.Handler.ServeHTTP(dashboardResp, dashboardReq)
	if dashboardResp.Code != http.StatusOK {
		t.Fatalf("dashboard status mismatch after convert: got=%d body=%s", dashboardResp.Code, dashboardResp.Body.String())
	}
	if err := json.Unmarshal(dashboardResp.Body.Bytes(), &dashboard); err != nil {
		t.Fatalf("unmarshal contractor dashboard: %v", err)
	}
	if dashboard.Summary.AvailableRequestCount != 0 {
		t.Fatalf("expected no available requests after convert, got=%d", dashboard.Summary.AvailableRequestCount)
	}
	if dashboard.Summary.ActiveProjectCount != 1 {
		t.Fatalf("expected one active project, got=%d", dashboard.Summary.ActiveProjectCount)
	}
}

func TestHomeownerProjectDetailAfterConversion(t *testing.T) {
	server := newTestServer()
	homeownerID := "homeowner-4"
	contractorID := "contractor-4"

	propertyReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/properties", bytes.NewBufferString(`{
		"label":"Townhouse",
		"address_line_1":"22 Harbor Way",
		"city":"San Diego",
		"region":"CA",
		"postal_code":"92101",
		"country_code":"US"
	}`))
	propertyReq.Header.Set("Content-Type", "application/json")
	propertyResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(propertyResp, propertyReq)

	var property domain.Property
	if err := json.Unmarshal(propertyResp.Body.Bytes(), &property); err != nil {
		t.Fatalf("unmarshal property: %v", err)
	}

	workRequestReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests", bytes.NewBufferString(`{
		"property_id":"`+property.ID+`",
		"title":"Water heater issue",
		"category":"plumbing",
		"area":"garage",
		"urgency":"high",
		"description":"Pilot light will not stay on."
	}`))
	workRequestReq.Header.Set("Content-Type", "application/json")
	workRequestResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(workRequestResp, workRequestReq)

	var workRequest domain.WorkRequest
	if err := json.Unmarshal(workRequestResp.Body.Bytes(), &workRequest); err != nil {
		t.Fatalf("unmarshal work request: %v", err)
	}

	orgReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations", bytes.NewBufferString(`{"name":"Harbor Mechanical"}`))
	orgReq.Header.Set("Content-Type", "application/json")
	orgResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(orgResp, orgReq)

	var organization domain.Organization
	if err := json.Unmarshal(orgResp.Body.Bytes(), &organization); err != nil {
		t.Fatalf("unmarshal organization: %v", err)
	}

	projectReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations/"+organization.ID+"/projects", bytes.NewBufferString(`{"work_request_id":"`+workRequest.ID+`"}`))
	projectReq.Header.Set("Content-Type", "application/json")
	projectResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(projectResp, projectReq)

	var project domain.Project
	if err := json.Unmarshal(projectResp.Body.Bytes(), &project); err != nil {
		t.Fatalf("unmarshal project: %v", err)
	}

	detailReq := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/"+homeownerID+"/projects/"+project.ID, nil)
	detailResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(detailResp, detailReq)
	if detailResp.Code != http.StatusOK {
		t.Fatalf("detail status mismatch: got=%d body=%s", detailResp.Code, detailResp.Body.String())
	}

	var detail domain.ProjectDetail
	if err := json.Unmarshal(detailResp.Body.Bytes(), &detail); err != nil {
		t.Fatalf("unmarshal detail: %v", err)
	}
	if detail.ViewerRole != "homeowner" {
		t.Fatalf("viewer role mismatch: got=%s", detail.ViewerRole)
	}
	if detail.Item.Project.ID != project.ID {
		t.Fatalf("project mismatch: got=%s want=%s", detail.Item.Project.ID, project.ID)
	}
	if detail.Item.WorkRequest == nil || detail.Item.WorkRequest.ID != workRequest.ID {
		t.Fatalf("expected linked work request in detail")
	}
	if len(detail.Timeline) == 0 {
		t.Fatal("expected project timeline")
	}
}

func TestEstimateWorkflowRoutes(t *testing.T) {
	server := newTestServer()
	homeownerID := "homeowner-5"
	contractorID := "contractor-5"

	propertyReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/properties", bytes.NewBufferString(`{
		"label":"Duplex",
		"address_line_1":"40 Linden Ave",
		"city":"Sacramento",
		"region":"CA",
		"postal_code":"95814",
		"country_code":"US"
	}`))
	propertyReq.Header.Set("Content-Type", "application/json")
	propertyResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(propertyResp, propertyReq)

	var property domain.Property
	if err := json.Unmarshal(propertyResp.Body.Bytes(), &property); err != nil {
		t.Fatalf("unmarshal property: %v", err)
	}

	workRequestReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests", bytes.NewBufferString(`{
		"property_id":"`+property.ID+`",
		"title":"Front door repair",
		"category":"carpentry",
		"area":"entry",
		"urgency":"medium",
		"description":"Door sticks and the deadbolt is misaligned."
	}`))
	workRequestReq.Header.Set("Content-Type", "application/json")
	workRequestResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(workRequestResp, workRequestReq)

	var workRequest domain.WorkRequest
	if err := json.Unmarshal(workRequestResp.Body.Bytes(), &workRequest); err != nil {
		t.Fatalf("unmarshal work request: %v", err)
	}

	orgReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations", bytes.NewBufferString(`{"name":"Door Doctor"}`))
	orgReq.Header.Set("Content-Type", "application/json")
	orgResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(orgResp, orgReq)

	var organization domain.Organization
	if err := json.Unmarshal(orgResp.Body.Bytes(), &organization); err != nil {
		t.Fatalf("unmarshal organization: %v", err)
	}

	projectReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations/"+organization.ID+"/projects", bytes.NewBufferString(`{"work_request_id":"`+workRequest.ID+`"}`))
	projectReq.Header.Set("Content-Type", "application/json")
	projectResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(projectResp, projectReq)

	var project domain.Project
	if err := json.Unmarshal(projectResp.Body.Bytes(), &project); err != nil {
		t.Fatalf("unmarshal project: %v", err)
	}

	estimateReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/projects/"+project.ID+"/estimates", bytes.NewBufferString(`{
		"summary":"Replace strike plate and plane front door",
		"deposit_amount_cents":6000,
		"line_items":[
			{"label":"Labor","amount_cents":14000},
			{"label":"Materials","amount_cents":4000}
		]
	}`))
	estimateReq.Header.Set("Content-Type", "application/json")
	estimateResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(estimateResp, estimateReq)
	if estimateResp.Code != http.StatusCreated {
		t.Fatalf("create estimate status mismatch: got=%d body=%s", estimateResp.Code, estimateResp.Body.String())
	}

	var estimate domain.Estimate
	if err := json.Unmarshal(estimateResp.Body.Bytes(), &estimate); err != nil {
		t.Fatalf("unmarshal estimate: %v", err)
	}
	if estimate.Status != domain.EstimateStatusSent {
		t.Fatalf("estimate status mismatch: got=%s", estimate.Status)
	}

	approveReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/projects/"+project.ID+"/estimates/"+estimate.ID+"/approve", bytes.NewBuffer(nil))
	approveResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(approveResp, approveReq)
	if approveResp.Code != http.StatusOK {
		t.Fatalf("approve estimate status mismatch: got=%d body=%s", approveResp.Code, approveResp.Body.String())
	}

	appointmentReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/projects/"+project.ID+"/appointments", bytes.NewBufferString(`{
		"title":"On-site visit",
		"notes":"Confirm measurements and hardware finish.",
		"starts_at":"2026-08-01T17:00:00Z",
		"ends_at":"2026-08-01T18:00:00Z"
	}`))
	appointmentReq.Header.Set("Content-Type", "application/json")
	appointmentResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(appointmentResp, appointmentReq)
	if appointmentResp.Code != http.StatusCreated {
		t.Fatalf("create appointment status mismatch: got=%d body=%s", appointmentResp.Code, appointmentResp.Body.String())
	}

	invoiceReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/projects/"+project.ID+"/invoices", bytes.NewBufferString(`{
		"summary":"Deposit request for materials",
		"notes":"Covers lockset and trim replacement parts.",
		"amount_cents":6000,
		"due_at":"2026-08-03T17:00:00Z"
	}`))
	invoiceReq.Header.Set("Content-Type", "application/json")
	invoiceResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(invoiceResp, invoiceReq)
	if invoiceResp.Code != http.StatusCreated {
		t.Fatalf("create invoice status mismatch: got=%d body=%s", invoiceResp.Code, invoiceResp.Body.String())
	}

	var invoice domain.Invoice
	if err := json.Unmarshal(invoiceResp.Body.Bytes(), &invoice); err != nil {
		t.Fatalf("unmarshal invoice: %v", err)
	}

	paymentReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/projects/"+project.ID+"/invoices/"+invoice.ID+"/payments", bytes.NewBufferString(`{
		"amount_cents":6000,
		"note":"Paid from the homeowner dashboard."
	}`))
	paymentReq.Header.Set("Content-Type", "application/json")
	paymentResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(paymentResp, paymentReq)
	if paymentResp.Code != http.StatusOK {
		t.Fatalf("record payment status mismatch: got=%d body=%s", paymentResp.Code, paymentResp.Body.String())
	}

	detailReq := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/"+homeownerID+"/projects/"+project.ID, nil)
	detailResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(detailResp, detailReq)
	if detailResp.Code != http.StatusOK {
		t.Fatalf("detail status mismatch: got=%d body=%s", detailResp.Code, detailResp.Body.String())
	}

	var detail domain.ProjectDetail
	if err := json.Unmarshal(detailResp.Body.Bytes(), &detail); err != nil {
		t.Fatalf("unmarshal detail: %v", err)
	}
	if len(detail.Estimates) != 1 {
		t.Fatalf("estimate count mismatch: got=%d", len(detail.Estimates))
	}
	if detail.Estimates[0].Status != domain.EstimateStatusApproved {
		t.Fatalf("approved estimate mismatch: got=%s", detail.Estimates[0].Status)
	}
	if detail.Item.Project.Status != domain.ProjectStatusApproved {
		t.Fatalf("project status mismatch: got=%s", detail.Item.Project.Status)
	}
	if len(detail.Appointments) != 1 {
		t.Fatalf("appointment count mismatch: got=%d", len(detail.Appointments))
	}
	if len(detail.Invoices) != 1 {
		t.Fatalf("invoice count mismatch: got=%d", len(detail.Invoices))
	}
	if detail.Invoices[0].Status != domain.InvoiceStatusPaid {
		t.Fatalf("invoice status mismatch: got=%s", detail.Invoices[0].Status)
	}
	if len(detail.Invoices[0].Payments) != 1 {
		t.Fatalf("invoice payment count mismatch: got=%d", len(detail.Invoices[0].Payments))
	}
}

func TestProjectMessageRoutesRespectVisibility(t *testing.T) {
	server := newTestServer()
	homeownerID := "homeowner-6"
	contractorID := "contractor-6"

	propertyReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/properties", bytes.NewBufferString(`{
		"label":"Cottage",
		"address_line_1":"11 Cedar Point",
		"city":"Tacoma",
		"region":"WA",
		"postal_code":"98402",
		"country_code":"US"
	}`))
	propertyReq.Header.Set("Content-Type", "application/json")
	propertyResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(propertyResp, propertyReq)

	var property domain.Property
	if err := json.Unmarshal(propertyResp.Body.Bytes(), &property); err != nil {
		t.Fatalf("unmarshal property: %v", err)
	}

	workRequestReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests", bytes.NewBufferString(`{
		"property_id":"`+property.ID+`",
		"title":"Exterior light flicker",
		"category":"electrical",
		"area":"porch",
		"urgency":"medium",
		"description":"Front porch light flickers at night."
	}`))
	workRequestReq.Header.Set("Content-Type", "application/json")
	workRequestResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(workRequestResp, workRequestReq)

	var workRequest domain.WorkRequest
	if err := json.Unmarshal(workRequestResp.Body.Bytes(), &workRequest); err != nil {
		t.Fatalf("unmarshal work request: %v", err)
	}

	orgReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations", bytes.NewBufferString(`{"name":"Bright Wire Co"}`))
	orgReq.Header.Set("Content-Type", "application/json")
	orgResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(orgResp, orgReq)

	var organization domain.Organization
	if err := json.Unmarshal(orgResp.Body.Bytes(), &organization); err != nil {
		t.Fatalf("unmarshal organization: %v", err)
	}

	projectReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations/"+organization.ID+"/projects", bytes.NewBufferString(`{"work_request_id":"`+workRequest.ID+`"}`))
	projectReq.Header.Set("Content-Type", "application/json")
	projectResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(projectResp, projectReq)

	var project domain.Project
	if err := json.Unmarshal(projectResp.Body.Bytes(), &project); err != nil {
		t.Fatalf("unmarshal project: %v", err)
	}

	contractorMessageReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/projects/"+project.ID+"/messages", bytes.NewBufferString(`{
		"body":"I can take a look tomorrow after 2 PM.",
		"visibility":"shared"
	}`))
	contractorMessageReq.Header.Set("Content-Type", "application/json")
	contractorMessageResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(contractorMessageResp, contractorMessageReq)
	if contractorMessageResp.Code != http.StatusCreated {
		t.Fatalf("create contractor shared message status mismatch: got=%d body=%s", contractorMessageResp.Code, contractorMessageResp.Body.String())
	}

	internalMessageReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/projects/"+project.ID+"/messages", bytes.NewBufferString(`{
		"body":"Bring dimmer tester and extra bulb.",
		"visibility":"internal"
	}`))
	internalMessageReq.Header.Set("Content-Type", "application/json")
	internalMessageResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(internalMessageResp, internalMessageReq)
	if internalMessageResp.Code != http.StatusCreated {
		t.Fatalf("create contractor internal message status mismatch: got=%d body=%s", internalMessageResp.Code, internalMessageResp.Body.String())
	}

	homeownerMessageReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/projects/"+project.ID+"/messages", bytes.NewBufferString(`{
		"body":"Tomorrow works. Gate code is 1122."
	}`))
	homeownerMessageReq.Header.Set("Content-Type", "application/json")
	homeownerMessageResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(homeownerMessageResp, homeownerMessageReq)
	if homeownerMessageResp.Code != http.StatusCreated {
		t.Fatalf("create homeowner message status mismatch: got=%d body=%s", homeownerMessageResp.Code, homeownerMessageResp.Body.String())
	}

	homeownerDetailReq := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/"+homeownerID+"/projects/"+project.ID, nil)
	homeownerDetailResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(homeownerDetailResp, homeownerDetailReq)
	if homeownerDetailResp.Code != http.StatusOK {
		t.Fatalf("homeowner detail status mismatch: got=%d body=%s", homeownerDetailResp.Code, homeownerDetailResp.Body.String())
	}

	var homeownerDetail domain.ProjectDetail
	if err := json.Unmarshal(homeownerDetailResp.Body.Bytes(), &homeownerDetail); err != nil {
		t.Fatalf("unmarshal homeowner detail: %v", err)
	}
	if len(homeownerDetail.Messages) != 2 {
		t.Fatalf("homeowner message count mismatch: got=%d", len(homeownerDetail.Messages))
	}

	contractorDetailReq := httptest.NewRequest(http.MethodGet, "/api/v1/contractors/"+contractorID+"/projects/"+project.ID, nil)
	contractorDetailResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(contractorDetailResp, contractorDetailReq)
	if contractorDetailResp.Code != http.StatusOK {
		t.Fatalf("contractor detail status mismatch: got=%d body=%s", contractorDetailResp.Code, contractorDetailResp.Body.String())
	}

	var contractorDetail domain.ProjectDetail
	if err := json.Unmarshal(contractorDetailResp.Body.Bytes(), &contractorDetail); err != nil {
		t.Fatalf("unmarshal contractor detail: %v", err)
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
		t.Fatal("expected internal note in contractor detail")
	}
}

func TestWorkRequestAttachmentUploadAndDownload(t *testing.T) {
	server := newTestServer()
	homeownerID := "homeowner-attachments"

	propertyReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/properties", bytes.NewBufferString(`{
		"label":"Home",
		"address_line_1":"14 Market Street",
		"city":"Oakland",
		"region":"CA",
		"postal_code":"94607",
		"country_code":"US"
	}`))
	propertyReq.Header.Set("Content-Type", "application/json")
	propertyResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(propertyResp, propertyReq)
	if propertyResp.Code != http.StatusCreated {
		t.Fatalf("create property status mismatch: got=%d body=%s", propertyResp.Code, propertyResp.Body.String())
	}
	var property domain.Property
	if err := json.Unmarshal(propertyResp.Body.Bytes(), &property); err != nil {
		t.Fatalf("unmarshal property: %v", err)
	}

	workRequestReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests", bytes.NewBufferString(`{
		"property_id":"`+property.ID+`",
		"title":"Water under sink",
		"category":"plumbing",
		"area":"kitchen",
		"urgency":"high",
		"description":"Water appears after the faucet runs."
	}`))
	workRequestReq.Header.Set("Content-Type", "application/json")
	workRequestResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(workRequestResp, workRequestReq)
	if workRequestResp.Code != http.StatusCreated {
		t.Fatalf("create work request status mismatch: got=%d body=%s", workRequestResp.Code, workRequestResp.Body.String())
	}
	var workRequest domain.WorkRequest
	if err := json.Unmarshal(workRequestResp.Body.Bytes(), &workRequest); err != nil {
		t.Fatalf("unmarshal work request: %v", err)
	}

	pngData := []byte{0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 13, 'I', 'H', 'D', 'R'}
	var uploadBody bytes.Buffer
	writer := multipart.NewWriter(&uploadBody)
	part, err := writer.CreateFormFile("file", "leak.png")
	if err != nil {
		t.Fatalf("create multipart file: %v", err)
	}
	if _, err := part.Write(pngData); err != nil {
		t.Fatalf("write multipart file: %v", err)
	}
	if err := writer.Close(); err != nil {
		t.Fatalf("close multipart writer: %v", err)
	}

	uploadPath := "/api/v1/homeowners/" + homeownerID + "/work-requests/" + workRequest.ID + "/attachments"
	uploadReq := httptest.NewRequest(http.MethodPost, uploadPath, &uploadBody)
	uploadReq.Header.Set("Content-Type", writer.FormDataContentType())
	uploadResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(uploadResp, uploadReq)
	if uploadResp.Code != http.StatusCreated {
		t.Fatalf("upload attachment status mismatch: got=%d body=%s", uploadResp.Code, uploadResp.Body.String())
	}
	var attachment struct {
		ID          string `json:"id"`
		ContentType string `json:"content_type"`
		ContentPath string `json:"content_path"`
	}
	if err := json.Unmarshal(uploadResp.Body.Bytes(), &attachment); err != nil {
		t.Fatalf("unmarshal attachment: %v", err)
	}
	if attachment.ID == "" || attachment.ContentType != "image/png" || attachment.ContentPath == "" {
		t.Fatalf("unexpected attachment payload: %+v", attachment)
	}

	downloadReq := httptest.NewRequest(http.MethodGet, attachment.ContentPath, nil)
	downloadResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(downloadResp, downloadReq)
	if downloadResp.Code != http.StatusOK {
		t.Fatalf("download attachment status mismatch: got=%d body=%s", downloadResp.Code, downloadResp.Body.String())
	}
	if !bytes.Equal(downloadResp.Body.Bytes(), pngData) {
		t.Fatal("downloaded attachment bytes do not match upload")
	}
	if got := downloadResp.Header().Get("Content-Type"); got != "image/png" {
		t.Fatalf("download content type mismatch: got=%q", got)
	}
	unauthorizedPath := "/api/v1/homeowners/someone-else/work-requests/" + workRequest.ID + "/attachments/" + attachment.ID
	unauthorizedReq := httptest.NewRequest(http.MethodGet, unauthorizedPath, nil)
	unauthorizedResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(unauthorizedResp, unauthorizedReq)
	if unauthorizedResp.Code != http.StatusNotFound {
		t.Fatalf("other homeowner download status mismatch: got=%d body=%s", unauthorizedResp.Code, unauthorizedResp.Body.String())
	}

	contractorID := "contractor-attachments"
	contractorPath := "/api/v1/contractors/" + contractorID + "/work-requests/" + workRequest.ID + "/attachments/" + attachment.ID
	availableDownloadReq := httptest.NewRequest(http.MethodGet, contractorPath, nil)
	availableDownloadResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(availableDownloadResp, availableDownloadReq)
	if availableDownloadResp.Code != http.StatusOK {
		t.Fatalf("available contractor attachment status mismatch: got=%d body=%s", availableDownloadResp.Code, availableDownloadResp.Body.String())
	}

	contractorDashboardReq := httptest.NewRequest(http.MethodGet, "/api/v1/contractors/"+contractorID+"/dashboard", nil)
	contractorDashboardResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(contractorDashboardResp, contractorDashboardReq)
	if contractorDashboardResp.Code != http.StatusOK {
		t.Fatalf("contractor dashboard status mismatch: got=%d body=%s", contractorDashboardResp.Code, contractorDashboardResp.Body.String())
	}
	var contractorDashboard domain.ContractorDashboard
	if err := json.Unmarshal(contractorDashboardResp.Body.Bytes(), &contractorDashboard); err != nil {
		t.Fatalf("unmarshal contractor dashboard: %v", err)
	}
	if len(contractorDashboard.AvailableRequests) != 1 || len(contractorDashboard.AvailableRequests[0].WorkRequest.Attachments) != 1 {
		t.Fatalf("contractor inbox attachment mismatch: %+v", contractorDashboard.AvailableRequests)
	}

	orgReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations", bytes.NewBufferString(`{"name":"Attachment Repair Co"}`))
	orgReq.Header.Set("Content-Type", "application/json")
	orgResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(orgResp, orgReq)
	if orgResp.Code != http.StatusCreated {
		t.Fatalf("create attachment contractor organization status mismatch: got=%d body=%s", orgResp.Code, orgResp.Body.String())
	}
	var organization domain.Organization
	if err := json.Unmarshal(orgResp.Body.Bytes(), &organization); err != nil {
		t.Fatalf("unmarshal attachment contractor organization: %v", err)
	}
	projectReq := httptest.NewRequest(http.MethodPost, "/api/v1/contractors/"+contractorID+"/organizations/"+organization.ID+"/projects", bytes.NewBufferString(`{"work_request_id":"`+workRequest.ID+`"}`))
	projectReq.Header.Set("Content-Type", "application/json")
	projectResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(projectResp, projectReq)
	if projectResp.Code != http.StatusCreated {
		t.Fatalf("create attachment project status mismatch: got=%d body=%s", projectResp.Code, projectResp.Body.String())
	}
	var project domain.Project
	if err := json.Unmarshal(projectResp.Body.Bytes(), &project); err != nil {
		t.Fatalf("unmarshal attachment project: %v", err)
	}

	assignedDownloadReq := httptest.NewRequest(http.MethodGet, contractorPath, nil)
	assignedDownloadResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(assignedDownloadResp, assignedDownloadReq)
	if assignedDownloadResp.Code != http.StatusOK {
		t.Fatalf("assigned contractor attachment status mismatch: got=%d body=%s", assignedDownloadResp.Code, assignedDownloadResp.Body.String())
	}
	otherContractorPath := "/api/v1/contractors/other-contractor/work-requests/" + workRequest.ID + "/attachments/" + attachment.ID
	otherContractorReq := httptest.NewRequest(http.MethodGet, otherContractorPath, nil)
	otherContractorResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(otherContractorResp, otherContractorReq)
	if otherContractorResp.Code != http.StatusNotFound {
		t.Fatalf("unassigned contractor attachment status mismatch: got=%d body=%s", otherContractorResp.Code, otherContractorResp.Body.String())
	}

	projectDetailReq := httptest.NewRequest(http.MethodGet, "/api/v1/contractors/"+contractorID+"/projects/"+project.ID, nil)
	projectDetailResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(projectDetailResp, projectDetailReq)
	if projectDetailResp.Code != http.StatusOK {
		t.Fatalf("attachment project detail status mismatch: got=%d body=%s", projectDetailResp.Code, projectDetailResp.Body.String())
	}
	var projectDetail domain.ProjectDetail
	if err := json.Unmarshal(projectDetailResp.Body.Bytes(), &projectDetail); err != nil {
		t.Fatalf("unmarshal attachment project detail: %v", err)
	}
	if projectDetail.Item.WorkRequest == nil || len(projectDetail.Item.WorkRequest.Attachments) != 1 {
		t.Fatalf("project detail attachment mismatch: %+v", projectDetail.Item.WorkRequest)
	}

	dashboardReq := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/"+homeownerID+"/dashboard", nil)
	dashboardResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(dashboardResp, dashboardReq)
	if dashboardResp.Code != http.StatusOK {
		t.Fatalf("dashboard status mismatch: got=%d body=%s", dashboardResp.Code, dashboardResp.Body.String())
	}
	var dashboard domain.HomeownerDashboard
	if err := json.Unmarshal(dashboardResp.Body.Bytes(), &dashboard); err != nil {
		t.Fatalf("unmarshal dashboard: %v", err)
	}
	if len(dashboard.WorkRequests) != 1 || len(dashboard.WorkRequests[0].Attachments) != 1 {
		t.Fatalf("dashboard attachment mismatch: %+v", dashboard.WorkRequests)
	}
}

func TestGuestInviteEstimateFlow(t *testing.T) {
	server := newTestServer()
	homeownerID := "homeowner-invite"

	propertyReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/properties", bytes.NewBufferString(`{
		"label":"Harbor House","address_line_1":"48 Private Way","city":"Oakland","region":"CA","postal_code":"94607","country_code":"US"
	}`))
	propertyReq.Header.Set("Content-Type", "application/json")
	propertyResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(propertyResp, propertyReq)
	if propertyResp.Code != http.StatusCreated {
		t.Fatalf("create invite property: got=%d body=%s", propertyResp.Code, propertyResp.Body.String())
	}
	var property domain.Property
	if err := json.Unmarshal(propertyResp.Body.Bytes(), &property); err != nil {
		t.Fatalf("unmarshal invite property: %v", err)
	}

	workReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests", bytes.NewBufferString(`{
		"property_id":"`+property.ID+`","title":"Repair the guest bath tile","category":"general","area":"Guest bathroom",
		"urgency":"medium","description":"Three floor tiles are loose near the shower.","preferred_timing":"Weekday mornings"
	}`))
	workReq.Header.Set("Content-Type", "application/json")
	workResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(workResp, workReq)
	if workResp.Code != http.StatusCreated {
		t.Fatalf("create invite request: got=%d body=%s", workResp.Code, workResp.Body.String())
	}
	var workRequest domain.WorkRequest
	if err := json.Unmarshal(workResp.Body.Bytes(), &workRequest); err != nil {
		t.Fatalf("unmarshal invite request: %v", err)
	}

	attachmentBytes := []byte{0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a, 'e', 'v', 'i', 'd', 'e', 'n', 'c', 'e'}
	var attachmentBody bytes.Buffer
	attachmentWriter := multipart.NewWriter(&attachmentBody)
	attachmentPart, err := attachmentWriter.CreateFormFile("file", "loose-tile.png")
	if err != nil {
		t.Fatalf("create invite attachment: %v", err)
	}
	if _, err := attachmentPart.Write(attachmentBytes); err != nil {
		t.Fatalf("write invite attachment: %v", err)
	}
	if err := attachmentWriter.Close(); err != nil {
		t.Fatalf("close invite attachment: %v", err)
	}
	attachmentReq := httptest.NewRequest(http.MethodPost, "/api/v1/homeowners/"+homeownerID+"/work-requests/"+workRequest.ID+"/attachments", &attachmentBody)
	attachmentReq.Header.Set("Content-Type", attachmentWriter.FormDataContentType())
	attachmentResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(attachmentResp, attachmentReq)
	if attachmentResp.Code != http.StatusCreated {
		t.Fatalf("upload invite attachment: got=%d body=%s", attachmentResp.Code, attachmentResp.Body.String())
	}
	var attachment domain.Attachment
	if err := json.Unmarshal(attachmentResp.Body.Bytes(), &attachment); err != nil {
		t.Fatalf("unmarshal invite attachment: %v", err)
	}

	invitePath := "/api/v1/homeowners/" + homeownerID + "/work-requests/" + workRequest.ID + "/invites"
	inviteReq := httptest.NewRequest(http.MethodPost, invitePath, nil)
	inviteResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(inviteResp, inviteReq)
	if inviteResp.Code != http.StatusCreated {
		t.Fatalf("create invite: got=%d body=%s", inviteResp.Code, inviteResp.Body.String())
	}
	var invitePayload struct {
		Invite   domain.WorkRequestInvite `json:"invite"`
		ShareURL string                   `json:"share_url"`
	}
	if err := json.Unmarshal(inviteResp.Body.Bytes(), &invitePayload); err != nil {
		t.Fatalf("unmarshal invite: %v", err)
	}
	token := strings.TrimPrefix(invitePayload.ShareURL, "http://localhost:3000/invite/")
	if token == "" || token == invitePayload.ShareURL {
		t.Fatalf("unexpected share URL: %q", invitePayload.ShareURL)
	}

	publicReq := httptest.NewRequest(http.MethodGet, "/api/v1/invites/"+token, nil)
	publicResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(publicResp, publicReq)
	if publicResp.Code != http.StatusOK {
		t.Fatalf("get public invite: got=%d body=%s", publicResp.Code, publicResp.Body.String())
	}
	if strings.Contains(publicResp.Body.String(), "48 Private Way") || strings.Contains(publicResp.Body.String(), homeownerID) {
		t.Fatalf("public invite leaked private property data: %s", publicResp.Body.String())
	}
	if !strings.Contains(publicResp.Body.String(), "Oakland") || !strings.Contains(publicResp.Body.String(), "Repair the guest bath tile") {
		t.Fatalf("public invite missing scoped task data: %s", publicResp.Body.String())
	}
	publicAttachmentPath := "/api/v1/invites/" + token + "/attachments/" + attachment.ID
	if !strings.Contains(publicResp.Body.String(), publicAttachmentPath) {
		t.Fatalf("public invite missing token-scoped attachment path: %s", publicResp.Body.String())
	}
	publicAttachmentReq := httptest.NewRequest(http.MethodGet, publicAttachmentPath, nil)
	publicAttachmentResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(publicAttachmentResp, publicAttachmentReq)
	if publicAttachmentResp.Code != http.StatusOK || !bytes.Equal(publicAttachmentResp.Body.Bytes(), attachmentBytes) {
		t.Fatalf("download invite attachment: got=%d body=%x", publicAttachmentResp.Code, publicAttachmentResp.Body.Bytes())
	}
	wrongAttachmentReq := httptest.NewRequest(http.MethodGet, "/api/v1/invites/"+token+"/attachments/att_unknown", nil)
	wrongAttachmentResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(wrongAttachmentResp, wrongAttachmentReq)
	if wrongAttachmentResp.Code != http.StatusNotFound {
		t.Fatalf("cross-attachment invite access: got=%d body=%s", wrongAttachmentResp.Code, wrongAttachmentResp.Body.String())
	}

	estimateBody := `{
		"contractor_name":"Morgan Lee","business_name":"Lee Tile Works","email":"morgan@example.com",
		"summary":"Reset and grout three loose tiles.","available_timing":"Tuesday morning",
		"line_items":[{"label":"Labor","amount_cents":24000},{"label":"Materials","amount_cents":6500}]
	}`
	estimateReq := httptest.NewRequest(http.MethodPost, "/api/v1/invites/"+token+"/estimates", bytes.NewBufferString(estimateBody))
	estimateReq.Header.Set("Content-Type", "application/json")
	estimateResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(estimateResp, estimateReq)
	if estimateResp.Code != http.StatusCreated {
		t.Fatalf("submit guest estimate: got=%d body=%s", estimateResp.Code, estimateResp.Body.String())
	}
	var estimate domain.GuestEstimate
	if err := json.Unmarshal(estimateResp.Body.Bytes(), &estimate); err != nil {
		t.Fatalf("unmarshal guest estimate: %v", err)
	}
	if estimate.TotalAmountCents != 30500 || len(estimate.LineItems) != 2 {
		t.Fatalf("guest estimate total mismatch: %+v", estimate)
	}

	duplicateReq := httptest.NewRequest(http.MethodPost, "/api/v1/invites/"+token+"/estimates", bytes.NewBufferString(estimateBody))
	duplicateReq.Header.Set("Content-Type", "application/json")
	duplicateResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(duplicateResp, duplicateReq)
	if duplicateResp.Code != http.StatusConflict {
		t.Fatalf("duplicate estimate status: got=%d body=%s", duplicateResp.Code, duplicateResp.Body.String())
	}

	listReq := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/"+homeownerID+"/work-requests/"+workRequest.ID+"/guest-estimates", nil)
	listResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(listResp, listReq)
	if listResp.Code != http.StatusOK || !strings.Contains(listResp.Body.String(), "Morgan Lee") {
		t.Fatalf("list guest estimates: got=%d body=%s", listResp.Code, listResp.Body.String())
	}

	dashboardReq := httptest.NewRequest(http.MethodGet, "/api/v1/homeowners/"+homeownerID+"/dashboard", nil)
	dashboardResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(dashboardResp, dashboardReq)
	var dashboard domain.HomeownerDashboard
	if err := json.Unmarshal(dashboardResp.Body.Bytes(), &dashboard); err != nil {
		t.Fatalf("unmarshal invite dashboard: %v", err)
	}
	if len(dashboard.WorkRequests) != 1 || dashboard.WorkRequests[0].GuestEstimateCount != 1 || dashboard.WorkRequests[0].Status != domain.WorkRequestStatusQuoted {
		t.Fatalf("invite dashboard state mismatch: %+v", dashboard.WorkRequests)
	}

	revokeReq := httptest.NewRequest(http.MethodPost, invitePath+"/"+invitePayload.Invite.ID+"/revoke", nil)
	revokeResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(revokeResp, revokeReq)
	if revokeResp.Code != http.StatusOK {
		t.Fatalf("revoke invite: got=%d body=%s", revokeResp.Code, revokeResp.Body.String())
	}
	revokedReq := httptest.NewRequest(http.MethodGet, "/api/v1/invites/"+token, nil)
	revokedResp := httptest.NewRecorder()
	server.Handler.ServeHTTP(revokedResp, revokedReq)
	if revokedResp.Code != http.StatusGone {
		t.Fatalf("revoked invite status: got=%d body=%s", revokedResp.Code, revokedResp.Body.String())
	}
	if got := requestLogPath("/api/v1/invites/" + token + "/estimates"); got != "/api/v1/invites/[redacted]" {
		t.Fatalf("invite log path was not redacted: %q", got)
	}
}
