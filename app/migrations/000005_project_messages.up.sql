create table if not exists project_messages (
    id text primary key,
    project_id text not null references projects(id) on delete cascade,
    author_user_id text not null references users(id) on delete cascade,
    author_role text not null,
    visibility text not null,
    body text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_project_messages_project_id on project_messages(project_id, created_at asc);
create index if not exists idx_project_messages_visibility on project_messages(visibility);
