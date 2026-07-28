create table if not exists users (
    id text primary key,
    email text not null unique,
    display_name text not null,
    role text not null,
    created_at timestamptz not null default now()
);

create table if not exists organizations (
    id text primary key,
    name text not null,
    kind text not null,
    created_at timestamptz not null default now()
);

create table if not exists organization_members (
    organization_id text not null references organizations(id) on delete cascade,
    user_id text not null references users(id) on delete cascade,
    role text not null,
    created_at timestamptz not null default now(),
    primary key (organization_id, user_id)
);

create table if not exists properties (
    id text primary key,
    homeowner_user_id text not null references users(id) on delete cascade,
    label text not null,
    address_line_1 text not null,
    address_line_2 text,
    city text not null,
    region text not null,
    postal_code text not null,
    country_code text not null default 'US',
    created_at timestamptz not null default now()
);

create table if not exists property_assignments (
    property_id text not null references properties(id) on delete cascade,
    organization_id text not null references organizations(id) on delete cascade,
    relationship_type text not null,
    created_at timestamptz not null default now(),
    primary key (property_id, organization_id)
);

create table if not exists work_requests (
    id text primary key,
    property_id text not null references properties(id) on delete cascade,
    requested_by_user_id text not null references users(id) on delete cascade,
    title text not null,
    category text not null,
    area text not null,
    urgency text not null,
    description text not null,
    preferred_timing text,
    status text not null,
    created_at timestamptz not null default now()
);

create table if not exists projects (
    id text primary key,
    property_id text not null references properties(id) on delete cascade,
    work_request_id text references work_requests(id) on delete set null,
    contractor_org_id text references organizations(id) on delete set null,
    title text not null,
    status text not null,
    created_at timestamptz not null default now()
);

create table if not exists activity_events (
    id text primary key,
    project_id text references projects(id) on delete cascade,
    actor_user_id text references users(id) on delete set null,
    event_type text not null,
    visibility text not null,
    body jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_properties_homeowner_user_id on properties(homeowner_user_id);
create index if not exists idx_work_requests_property_id on work_requests(property_id);
create index if not exists idx_work_requests_status on work_requests(status);
create index if not exists idx_projects_property_id on projects(property_id);
create index if not exists idx_projects_contractor_org_id on projects(contractor_org_id);
create index if not exists idx_activity_events_project_id on activity_events(project_id, created_at desc);
