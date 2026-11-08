create table if not exists public.documents (
  id uuid primary key,
  department text not null,
  file_name text not null,
  storage_path text not null,
  doc_hash text not null,
  status text not null default 'pending' check (status in ('pending', 'processing', 'indexed', 'failed')),
  chunk_count integer not null default 0,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (department, file_name)
);

create index if not exists documents_status_idx on public.documents (status);

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace trigger documents_touch_updated_at
before update on public.documents
for each row execute function public.touch_updated_at();

alter table public.documents enable row level security;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('documents', 'documents', false, 52428800, array['application/pdf'])
on conflict (id) do nothing;
