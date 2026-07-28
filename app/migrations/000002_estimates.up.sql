create table if not exists estimates (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    contractor_org_id text not null references organizations(id) on delete cascade,
    summary text not null,
    notes text not null default '',
    deposit_amount_cents bigint not null default 0,
    total_amount_cents bigint not null,
    status text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    sent_at timestamptz,
    decided_at timestamptz
);

create table if not exists estimate_line_items (
    id text primary key,
    estimate_id text not null references estimates(id) on delete cascade,
    label text not null,
    amount_cents bigint not null,
    position integer not null default 0
);

create index if not exists idx_estimates_project_id on estimates(project_id, created_at desc);
create index if not exists idx_estimates_status on estimates(status);
create index if not exists idx_estimate_line_items_estimate_id on estimate_line_items(estimate_id, position asc);
