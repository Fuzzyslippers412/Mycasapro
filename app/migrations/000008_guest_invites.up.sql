create table work_request_invites (
    id text primary key,
    work_request_id text not null references work_requests(id) on delete cascade,
    homeowner_user_id text not null references users(id) on delete cascade,
    token_hash char(64) not null unique,
    expires_at timestamptz not null,
    revoked_at timestamptz,
    created_at timestamptz not null,
    check (expires_at > created_at)
);

create index work_request_invites_request_idx
    on work_request_invites(work_request_id, created_at desc);

create table guest_estimates (
    id text primary key,
    invite_id text not null references work_request_invites(id) on delete restrict,
    work_request_id text not null references work_requests(id) on delete cascade,
    contractor_name text not null,
    business_name text not null default '',
    email text not null,
    summary text not null,
    notes text not null default '',
    available_timing text not null default '',
    total_amount_cents bigint not null check (total_amount_cents >= 0),
    created_at timestamptz not null,
    unique (invite_id, email)
);

create index guest_estimates_request_idx
    on guest_estimates(work_request_id, created_at desc);

create table guest_estimate_line_items (
    id text primary key,
    guest_estimate_id text not null references guest_estimates(id) on delete cascade,
    label text not null,
    amount_cents bigint not null check (amount_cents >= 0),
    position integer not null check (position >= 0),
    unique (guest_estimate_id, position)
);
