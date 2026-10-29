-- ============================================================
-- CityWatch AI — Full PostgreSQL Schema for Supabase
-- Run this in the Supabase SQL Editor
-- ============================================================

create extension if not exists pgcrypto;

-- ============================================================
-- 1. DEPARTMENTS
-- ============================================================
create table if not exists public.departments (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  jurisdiction text,
  issue_categories text[] not null default '{}',
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

-- ============================================================
-- 2. PROFILES (linked to auth.users)
-- ============================================================
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  role text not null check (role in ('citizen', 'officer', 'admin')),
  department_id uuid references public.departments(id),
  phone text,
  created_at timestamptz not null default now()
);

-- ============================================================
-- 3. COMPLAINTS
-- ============================================================
create table if not exists public.complaints (
  id uuid primary key default gen_random_uuid(),
  complaint_number text unique,
  citizen_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  category text not null,
  description text not null,
  location_text text,
  latitude double precision,
  longitude double precision,
  ward text,
  department_id uuid references public.departments(id),
  assigned_officer_id uuid references auth.users(id),
  priority text not null default 'medium' check (priority in ('low', 'medium', 'high', 'critical', 'needs_review')),
  status text not null default 'submitted' check (status in (
    'submitted', 'ai_analysis', 'pending_review', 'verified',
    'assigned', 'in_progress', 'resolved', 'closed',
    'rejected', 'reopened', 'needs_information'
  )),
  submitted_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  resolved_at timestamptz,
  closed_at timestamptz
);

create index if not exists complaints_citizen_id_idx on public.complaints (citizen_id);
create index if not exists complaints_status_idx on public.complaints (status);
create index if not exists complaints_category_idx on public.complaints (category);
create index if not exists complaints_priority_idx on public.complaints (priority);
create index if not exists complaints_department_id_idx on public.complaints (department_id);
create index if not exists complaints_assigned_officer_idx on public.complaints (assigned_officer_id);

-- Auto-generate complaint number: CW-YYYYMMDD-XXXX
create or replace function public.generate_complaint_number()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  date_part text;
  seq_num integer;
begin
  date_part := to_char(now(), 'YYYYMMDD');
  select count(*) + 1 into seq_num
  from public.complaints
  where complaint_number like 'CW-' || date_part || '-%';
  new.complaint_number := 'CW-' || date_part || '-' || lpad(seq_num::text, 4, '0');
  return new;
end;
$$;

drop trigger if exists set_complaint_number on public.complaints;
create trigger set_complaint_number
before insert on public.complaints
for each row
when (new.complaint_number is null)
execute function public.generate_complaint_number();

-- ============================================================
-- 4. EVIDENCE FILES
-- ============================================================
create table if not exists public.evidence_files (
  id uuid primary key default gen_random_uuid(),
  complaint_id uuid not null references public.complaints(id) on delete cascade,
  storage_path text not null,
  file_type text not null check (file_type in ('video', 'image', 'document')),
  file_size bigint,
  uploaded_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create index if not exists evidence_files_complaint_id_idx on public.evidence_files (complaint_id);

-- ============================================================
-- 5. AI ANALYSES
-- ============================================================
create table if not exists public.ai_analyses (
  id uuid primary key default gen_random_uuid(),
  complaint_id uuid not null references public.complaints(id) on delete cascade,
  model_name text not null default 'yolov8n',
  model_version text,
  detected_classes jsonb default '[]'::jsonb,
  confidence_data jsonb default '[]'::jsonb,
  frame_timestamps jsonb default '[]'::jsonb,
  suggested_priority text,
  suggested_category text,
  summary text,
  analysis_status text not null default 'pending' check (analysis_status in ('pending', 'processing', 'completed', 'failed', 'review_required')),
  error_message text,
  processing_time_ms integer,
  created_at timestamptz not null default now()
);

create index if not exists ai_analyses_complaint_id_idx on public.ai_analyses (complaint_id);

-- ============================================================
-- 6. ASSIGNMENTS
-- ============================================================
create table if not exists public.assignments (
  id uuid primary key default gen_random_uuid(),
  complaint_id uuid not null references public.complaints(id) on delete cascade,
  department_id uuid references public.departments(id),
  officer_id uuid not null references auth.users(id) on delete cascade,
  assigned_by uuid references auth.users(id),
  notes text,
  assigned_at timestamptz not null default now(),
  unique (complaint_id, officer_id)
);

create index if not exists assignments_complaint_id_idx on public.assignments (complaint_id);
create index if not exists assignments_officer_id_idx on public.assignments (officer_id);

-- ============================================================
-- 7. COMPLAINT HISTORY (audit trail)
-- ============================================================
create table if not exists public.complaint_history (
  id uuid primary key default gen_random_uuid(),
  complaint_id uuid not null references public.complaints(id) on delete cascade,
  actor_id uuid references auth.users(id),
  old_status text,
  new_status text,
  action text not null,
  reason text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists complaint_history_complaint_id_idx on public.complaint_history (complaint_id);

-- ============================================================
-- 8. RESOLUTION RECORDS
-- ============================================================
create table if not exists public.resolution_records (
  id uuid primary key default gen_random_uuid(),
  complaint_id uuid not null references public.complaints(id) on delete cascade,
  officer_id uuid references auth.users(id),
  resolution_notes text not null,
  evidence_file_id uuid references public.evidence_files(id),
  submitted_at timestamptz not null default now(),
  review_status text not null default 'pending' check (review_status in ('pending', 'approved', 'rejected')),
  reviewed_by uuid references auth.users(id),
  reviewed_at timestamptz
);

create index if not exists resolution_records_complaint_id_idx on public.resolution_records (complaint_id);

-- ============================================================
-- 9. NOTIFICATIONS
-- ============================================================
create table if not exists public.notifications (
  id uuid primary key default gen_random_uuid(),
  recipient_id uuid not null references auth.users(id) on delete cascade,
  complaint_id uuid references public.complaints(id) on delete cascade,
  title text not null,
  message text not null,
  type text not null default 'info' check (type in ('info', 'warning', 'success', 'error')),
  read_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists notifications_recipient_id_idx on public.notifications (recipient_id);
create index if not exists notifications_read_at_idx on public.notifications (read_at) where read_at is null;

-- ============================================================
-- TRIGGERS
-- ============================================================

-- Auto-update updated_at on complaints
create or replace function public.update_complaint_updated_at()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists complaints_updated_at on public.complaints;
create trigger complaints_updated_at
before update on public.complaints
for each row
execute function public.update_complaint_updated_at();

-- Auto-log status changes
create or replace function public.log_status_change()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if old.status is distinct from new.status then
    insert into public.complaint_history (complaint_id, old_status, new_status, action)
    values (new.id, old.status, new.status, 'status_change');
  end if;
  return new;
end;
$$;

drop trigger if exists complaints_status_history on public.complaints;
create trigger complaints_status_history
after update on public.complaints
for each row
execute function public.log_status_change();

-- Auto-set resolved_at / closed_at timestamps
create or replace function public.set_resolution_timestamps()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if new.status = 'resolved' and old.status != 'resolved' then
    new.resolved_at = now();
  end if;
  if new.status = 'closed' and old.status != 'closed' then
    new.closed_at = now();
  end if;
  if new.status = 'reopened' then
    new.resolved_at = null;
    new.closed_at = null;
  end if;
  return new;
end;
$$;

drop trigger if exists complaints_resolution_timestamps on public.complaints;
create trigger complaints_resolution_timestamps
before update on public.complaints
for each row
execute function public.set_resolution_timestamps();

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, full_name, role)
  values (
    new.id,
    coalesce(new.raw_user_meta_data->>'full_name', new.email),
    coalesce(new.raw_user_meta_data->>'role', 'citizen')
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

create or replace function public.get_user_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select role from public.profiles where id = auth.uid();
$$;

create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'admin'
  );
$$;

create or replace function public.is_officer()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'officer'
  );
$$;

create or replace function public.is_citizen()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.profiles p
    where p.id = auth.uid() and p.role = 'citizen'
  );
$$;

create or replace function public.complaint_is_assigned_to_user(p_complaint_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from public.assignments a
    where a.complaint_id = p_complaint_id
      and a.officer_id = auth.uid()
  );
$$;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table public.departments enable row level security;
alter table public.profiles enable row level security;
alter table public.complaints enable row level security;
alter table public.evidence_files enable row level security;
alter table public.ai_analyses enable row level security;
alter table public.assignments enable row level security;
alter table public.complaint_history enable row level security;
alter table public.resolution_records enable row level security;
alter table public.notifications enable row level security;

-- Department policies
create policy "Anyone authenticated can read departments"
on public.departments for select
using (auth.role() = 'authenticated');

create policy "Admins can manage departments"
on public.departments for all
using (public.is_admin())
with check (public.is_admin());

-- Profile policies
create policy "Users can read own profile or admins read all"
on public.profiles for select
using (auth.uid() = id or public.is_admin() or public.is_officer());

create policy "Users can create own profile"
on public.profiles for insert
with check (auth.uid() = id);

create policy "Users can update own profile"
on public.profiles for update
using (auth.uid() = id)
with check (auth.uid() = id);

-- Complaint policies
create policy "Citizens see own, admins/officers see relevant"
on public.complaints for select
using (
  citizen_id = auth.uid()
  or public.is_admin()
  or public.complaint_is_assigned_to_user(id)
);

create policy "Citizens can create complaints"
on public.complaints for insert
with check (citizen_id = auth.uid());

create policy "Admins can update any complaint"
on public.complaints for update
using (public.is_admin())
with check (public.is_admin());

create policy "Officers can update assigned complaints"
on public.complaints for update
using (public.complaint_is_assigned_to_user(id))
with check (public.complaint_is_assigned_to_user(id));

create policy "Citizens can update own complaints (limited)"
on public.complaints for update
using (citizen_id = auth.uid())
with check (citizen_id = auth.uid());

-- Evidence file policies
create policy "Read evidence for accessible complaints"
on public.evidence_files for select
using (
  exists (
    select 1 from public.complaints c
    where c.id = complaint_id
      and (c.citizen_id = auth.uid() or public.is_admin() or public.complaint_is_assigned_to_user(c.id))
  )
);

create policy "Upload evidence for own or assigned complaints"
on public.evidence_files for insert
with check (
  exists (
    select 1 from public.complaints c
    where c.id = complaint_id
      and (c.citizen_id = auth.uid() or public.complaint_is_assigned_to_user(c.id))
  )
);

-- AI analysis policies
create policy "Read AI analyses for accessible complaints"
on public.ai_analyses for select
using (
  exists (
    select 1 from public.complaints c
    where c.id = complaint_id
      and (c.citizen_id = auth.uid() or public.is_admin() or public.complaint_is_assigned_to_user(c.id))
  )
);

create policy "Admins and system can manage AI analyses"
on public.ai_analyses for all
using (public.is_admin())
with check (public.is_admin());

-- Assignment policies
create policy "View assignments for accessible complaints"
on public.assignments for select
using (
  officer_id = auth.uid()
  or public.is_admin()
  or exists (
    select 1 from public.complaints c
    where c.id = complaint_id and c.citizen_id = auth.uid()
  )
);

create policy "Admins can manage assignments"
on public.assignments for all
using (public.is_admin())
with check (public.is_admin());

-- Complaint history policies
create policy "Read history for accessible complaints"
on public.complaint_history for select
using (
  exists (
    select 1 from public.complaints c
    where c.id = complaint_id
      and (c.citizen_id = auth.uid() or public.is_admin() or public.complaint_is_assigned_to_user(c.id))
  )
);

create policy "System can insert history"
on public.complaint_history for insert
with check (auth.role() = 'authenticated');

-- Resolution record policies
create policy "Read resolutions for accessible complaints"
on public.resolution_records for select
using (
  exists (
    select 1 from public.complaints c
    where c.id = complaint_id
      and (c.citizen_id = auth.uid() or public.is_admin() or public.complaint_is_assigned_to_user(c.id))
  )
);

create policy "Officers and admins can manage resolutions"
on public.resolution_records for all
using (public.is_admin() or officer_id = auth.uid())
with check (public.is_admin() or officer_id = auth.uid());

-- Notification policies
create policy "Users can read own notifications"
on public.notifications for select
using (recipient_id = auth.uid());

create policy "Users can update own notifications"
on public.notifications for update
using (recipient_id = auth.uid())
with check (recipient_id = auth.uid());

create policy "System can insert notifications"
on public.notifications for insert
with check (auth.role() = 'authenticated');

-- ============================================================
-- STORAGE
-- ============================================================

insert into storage.buckets (id, name, public)
values ('evidence', 'evidence', false)
on conflict (id) do nothing;

create policy "Authenticated users can upload evidence"
on storage.objects for insert
with check (
  bucket_id = 'evidence'
  and auth.role() = 'authenticated'
);

create policy "Users can read evidence for their complaints"
on storage.objects for select
using (
  bucket_id = 'evidence'
  and auth.role() = 'authenticated'
);

-- ============================================================
-- SEED DATA
-- ============================================================

insert into public.departments (name, jurisdiction, issue_categories)
values
  ('Road Maintenance', 'City Municipal Corporation', ARRAY['pothole','road_damage','road_obstruction','speed_breaker']),
  ('Sanitation Department', 'City Municipal Corporation', ARRAY['garbage','waste_dumping','overflowing_bins','sanitation']),
  ('Electrical & Public Lighting', 'City Municipal Corporation', ARRAY['streetlight','electrical_hazard','traffic_signal']),
  ('Drainage Department', 'City Municipal Corporation', ARRAY['drainage','waterlogging','sewage','flooding']),
  ('Traffic & Parking', 'City Traffic Police', ARRAY['illegal_parking','traffic_violation','road_safety']),
  ('General Administration', 'City Municipal Corporation', ARRAY['other','miscellaneous'])
on conflict (name) do nothing;
