drop table if exists email_outbox;

alter table work_request_invites
    drop constraint if exists work_request_invites_delivery_recipient_check,
    drop column if exists delivery_status,
    drop column if exists recipient_email,
    drop column if exists recipient_name;
