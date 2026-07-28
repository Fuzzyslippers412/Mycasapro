create table if not exists appointments (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    contractor_org_id text not null references organizations(id) on delete cascade,
    title text not null,
    notes text not null default '',
    starts_at timestamptz not null,
    ends_at timestamptz not null,
    status text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_appointments_project_id on appointments(project_id, starts_at asc);
create index if not exists idx_appointments_status on appointments(status);
