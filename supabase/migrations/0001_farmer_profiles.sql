create table public.farmer_profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,
  full_name text not null,
  phone text,
  preferred_language text not null default 'en',
  state text,
  district text,
  taluk text,
  village text,
  crops text[] default '{}',
  farm_size text,
  onboarding_completed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.farmer_profiles enable row level security;

create policy "Users can select their own farmer profile"
  on public.farmer_profiles for select
  using (user_id = auth.uid());

create policy "Users can insert their own farmer profile"
  on public.farmer_profiles for insert
  with check (user_id = auth.uid());

create policy "Users can update their own farmer profile"
  on public.farmer_profiles for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());
