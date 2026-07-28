create table if not exists invoices (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    contractor_org_id text not null references organizations(id) on delete cascade,
    summary text not null,
    notes text not null default '',
    amount_cents bigint not null,
    amount_paid_cents bigint not null default 0,
    outstanding_amount_cents bigint not null,
    status text not null,
    due_at timestamptz not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    issued_at timestamptz not null default now(),
    paid_at timestamptz
);

create table if not exists invoice_payments (
    id text primary key,
    invoice_id text not null references invoices(id) on delete cascade,
    payer_user_id text not null references users(id) on delete cascade,
    amount_cents bigint not null,
    note text not null default '',
    paid_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_invoices_project_id on invoices(project_id, created_at desc);
create index if not exists idx_invoices_status on invoices(status);
create index if not exists idx_invoice_payments_invoice_id on invoice_payments(invoice_id, paid_at desc);
