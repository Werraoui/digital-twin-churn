-- Run in the Supabase SQL editor once.
-- Personas are dual-written from the local SQLite warehouse.

create table if not exists personas (
  customer_id text primary key,
  payload jsonb not null,
  churn_risk_score double precision,
  contact_channel text,
  ops_status text default 'none',
  message_status text default 'none',
  recommended_action text,
  retention_message text,
  agent_notes text,
  contacted_at timestamptz,
  updated_at timestamptz default now()
);

create index if not exists personas_risk_idx on personas (churn_risk_score desc nulls last);
create index if not exists personas_ops_idx on personas (ops_status);

create table if not exists pipeline_runs (
  id bigserial primary key,
  customer_id text not null,
  status text,
  action jsonb,
  message text,
  justification text,
  score_before double precision,
  score_after double precision,
  operator text,
  created_at timestamptz default now()
);

create index if not exists pipeline_runs_customer_idx
  on pipeline_runs (customer_id, created_at desc);

-- Optional: enable Realtime for live dashboards (Dashboard → Database → Replication)
-- alter publication supabase_realtime add table personas;
-- alter publication supabase_realtime add table pipeline_runs;
