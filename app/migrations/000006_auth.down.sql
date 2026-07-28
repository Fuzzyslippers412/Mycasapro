drop table if exists sessions;
drop index if exists idx_users_email_lower;
alter table users drop column if exists password_hash;
