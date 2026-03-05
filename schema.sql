-- Run this SQL in the Supabase SQL Editor to create the required tables.
-- Also create two PUBLIC storage buckets in the Supabase dashboard:
--   1. "uploads" (for images)
--   2. "pdfs" (for PDF files)

-- Site settings (single row)
create table site_settings (
  id int primary key default 1 check (id = 1),
  title text not null default 'The Scope',
  mascot_url text default '',
  mission text default '',
  current_edition text default '',
  current_edition_title text default '',
  current_edition_pdf_url text default '',
  submission_guide text default ''
);

-- Seed the single row
insert into site_settings (id) values (1);

-- Publications
create table publications (
  id text primary key,
  title text not null,
  date date,
  description text default '',
  pdf_url text default '',
  cover_url text default ''
);

-- News articles
create table news (
  id text primary key,
  title text not null,
  author text default '',
  preview text default '',
  full_text text default '',
  date date,
  image_url text default ''
);

-- Team members
create table team_members (
  id text primary key,
  name text not null,
  role text default '',
  image_url text default '',
  sort_order int default 0
);
