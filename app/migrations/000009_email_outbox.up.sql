alter table work_request_invites
    add column recipient_name text not null default '',
    add column recipient_email text not null default '',
    add column delivery_status text not null default 'link_created'
        check (delivery_status in ('link_created', 'queued', 'processing', 'sent', 'failed', 'canceled'));

alter table work_request_invites
    add constraint work_request_invites_delivery_recipient_check
    check (
        (recipient_email = '' and delivery_status = 'link_created')
        or (recipient_email <> '' and delivery_status <> 'link_created')
    );

create table email_outbox (
    id text primary key,
    kind text not null check (kind <> ''),
    aggregate_id text not null check (aggregate_id <> ''),
    recipient_email text not null check (recipient_email <> ''),
    subject text not null check (subject <> ''),
    text_body text not null,
    html_body text not null,
    status text not null default 'queued'
        check (status in ('queued', 'processing', 'sent', 'failed', 'canceled')),
    attempts integer not null default 0 check (attempts between 0 and 8),
    next_attempt_at timestamptz not null,
    locked_until timestamptz,
    last_error text not null default '',
    created_at timestamptz not null,
    sent_at timestamptz,
    check ((status = 'processing') = (locked_until is not null))
);

create index email_outbox_delivery_idx
    on email_outbox(status, next_attempt_at, created_at)
    where status in ('queued', 'processing');

create unique index email_outbox_aggregate_idx
    on email_outbox(kind, aggregate_id);

create index work_request_invites_email_rate_idx
    on work_request_invites(homeowner_user_id, created_at desc)
    where recipient_email <> '';
