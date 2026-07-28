export type User = {
  id: string;
  email: string;
  display_name: string;
  role: "homeowner" | "contractor" | "contractor_admin" | "crew_member" | "platform_admin";
  created_at: string;
};

export type Property = {
  id: string;
  homeowner_user_id: string;
  label: string;
  address_line_1: string;
  address_line_2?: string;
  city: string;
  region: string;
  postal_code: string;
  country_code: string;
  created_at: string;
};

export type WorkRequest = {
  id: string;
  property_id: string;
  requested_by_user_id: string;
  title: string;
  category: string;
  area: string;
  urgency: string;
  description: string;
  preferred_timing?: string;
  status: string;
  attachments: Attachment[];
  guest_estimate_count: number;
  created_at: string;
};

export type Attachment = {
  id: string;
  work_request_id: string;
  uploaded_by_user_id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
  content_path?: string;
};

export type WorkRequestInvite = {
  id: string;
  work_request_id: string;
  homeowner_user_id: string;
  expires_at: string;
  revoked_at?: string;
  created_at: string;
};

export type GuestEstimateLineItem = {
  id: string;
  guest_estimate_id: string;
  label: string;
  amount_cents: number;
  position: number;
};

export type GuestEstimate = {
  id: string;
  invite_id: string;
  work_request_id: string;
  contractor_name: string;
  business_name?: string;
  email: string;
  summary: string;
  notes?: string;
  available_timing?: string;
  total_amount_cents: number;
  line_items: GuestEstimateLineItem[];
  created_at: string;
};

export type PublicInviteTask = {
  invite: Pick<WorkRequestInvite, "id" | "expires_at" | "created_at">;
  property: Pick<Property, "label" | "city" | "region" | "country_code">;
  work_request: Pick<
    WorkRequest,
    "id" | "title" | "category" | "area" | "urgency" | "description" | "preferred_timing" | "created_at"
  > & { attachments: Attachment[] };
};

export type HomeownerDashboard = {
  homeowner_user_id: string;
  summary: {
    property_count: number;
    open_repair_count: number;
    pending_approval_count: number;
    scheduled_visit_count: number;
    active_project_count: number;
    outstanding_invoice_count: number;
    requests_by_status: Record<string, number>;
  };
  properties: Property[];
  work_requests: WorkRequest[];
  active_projects: ProjectWorkspaceItem[];
};

export type Organization = {
  id: string;
  name: string;
  kind: string;
  created_at: string;
};

export type Project = {
  id: string;
  property_id: string;
  work_request_id: string;
  contractor_org_id: string;
  title: string;
  status: string;
  created_at: string;
};

export type ProjectWorkspaceItem = {
  project: Project;
  property: Property;
  work_request?: WorkRequest;
};

export type EstimateLineItem = {
  id: string;
  label: string;
  amount_cents: number;
  position: number;
};

export type Estimate = {
  id: string;
  project_id: string;
  contractor_org_id: string;
  summary: string;
  notes?: string;
  deposit_amount_cents: number;
  total_amount_cents: number;
  status: string;
  line_items: EstimateLineItem[];
  created_at: string;
  updated_at: string;
  sent_at?: string;
  decided_at?: string;
};

export type Appointment = {
  id: string;
  project_id: string;
  contractor_org_id: string;
  title: string;
  notes?: string;
  starts_at: string;
  ends_at: string;
  status: string;
  created_at: string;
};

export type Payment = {
  id: string;
  invoice_id: string;
  payer_user_id: string;
  amount_cents: number;
  note?: string;
  paid_at: string;
  created_at: string;
};

export type Invoice = {
  id: string;
  project_id: string;
  contractor_org_id: string;
  summary: string;
  notes?: string;
  amount_cents: number;
  amount_paid_cents: number;
  outstanding_amount_cents: number;
  status: string;
  due_at: string;
  payments: Payment[];
  created_at: string;
  updated_at: string;
  issued_at: string;
  paid_at?: string;
};

export type ProjectMessage = {
  id: string;
  project_id: string;
  author_user_id: string;
  author_role: string;
  visibility: string;
  body: string;
  created_at: string;
};

export type ContractorDashboard = {
  contractor_user_id: string;
  summary: {
    organization_count: number;
    available_request_count: number;
    active_project_count: number;
    pending_quote_count: number;
  };
  organizations: Organization[];
  available_requests: Array<{
    work_request: WorkRequest;
    property: Property;
  }>;
  active_projects: ProjectWorkspaceItem[];
};

export type ProjectDetail = {
  viewer_role: string;
  item: ProjectWorkspaceItem;
  estimates: Estimate[];
  appointments: Appointment[];
  invoices: Invoice[];
  messages: ProjectMessage[];
  timeline: Array<{
    id: string;
    event_type: string;
    title: string;
    description: string;
    created_at: string;
  }>;
};
