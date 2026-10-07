-- Run once in your own Supabase project's SQL editor. No private library data.
create table if not exists public.genre_review_workspaces (
 owner_id text primary key,
 library_path text, library_name text, library_sha text,
 decisions jsonb not null default '{"version":1,"groups":{},"files":{}}',
 revision bigint not null default 0,
 updated_at timestamptz not null default now()
);
alter table public.genre_review_workspaces enable row level security;
revoke all on public.genre_review_workspaces from anon, authenticated;
grant all on public.genre_review_workspaces to service_role;
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values ('mixweave-private-review','mixweave-private-review',false,60000000,array['application/gzip'])
on conflict(id) do nothing;

create or replace function public.save_genre_review(
 p_owner text, p_expected bigint, p_decisions jsonb,
 p_library_path text, p_library_name text, p_library_sha text
) returns setof public.genre_review_workspaces
language plpgsql security invoker set search_path = public as $$
begin
 insert into public.genre_review_workspaces(owner_id) values(p_owner)
 on conflict(owner_id) do nothing;
 return query update public.genre_review_workspaces set
 decisions=coalesce(p_decisions,decisions),
 library_path=coalesce(p_library_path,library_path),
 library_name=coalesce(p_library_name,library_name),
 library_sha=coalesce(p_library_sha,library_sha),
 revision=revision+1,updated_at=now()
 where owner_id=p_owner and revision=p_expected returning *;
 if not found then raise exception 'Newer revision exists' using errcode='40001'; end if;
end $$;
revoke all on function public.save_genre_review(text,bigint,jsonb,text,text,text) from public,anon,authenticated;
grant execute on function public.save_genre_review(text,bigint,jsonb,text,text,text) to service_role;
