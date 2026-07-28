create table if not exists attachments (
    id text primary key,
    work_request_id text references work_requests(id) on delete cascade,
    project_id text references projects(id) on delete cascade,
    uploaded_by_user_id text not null references users(id) on delete cascade,
    file_name text not null,
    content_type text not null,
    size_bytes bigint not null check (size_bytes > 0),
    sha256 text not null,
    storage_key text not null unique,
    created_at timestamptz not null default now(),
    constraint attachments_single_parent check (
        (work_request_id is not null and project_id is null) or
        (work_request_id is null and project_id is not null)
    )
);

create index if not exists idx_attachments_work_request on attachments(work_request_id, created_at);
create index if not exists idx_attachments_project on attachments(project_id, created_at);
