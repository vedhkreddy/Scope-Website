#!/usr/bin/env python3
"""Migrate data from content.json and local files to Supabase.

Prerequisites:
  1. Run schema.sql in Supabase SQL Editor
  2. Create public storage buckets 'uploads' and 'pdfs' in Supabase dashboard
  3. Set SUPABASE_URL and SUPABASE_KEY in .env

Usage:
  python migrate.py
"""

import os
import json

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.environ['SUPABASE_URL']
SUPABASE_KEY = os.environ['SUPABASE_KEY']
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_PATH = os.path.join(BASE_DIR, 'content.json')

CONTENT_TYPES = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'svg': 'image/svg+xml', 'pdf': 'application/pdf',
}


def upload_local_file(local_path, bucket):
    """Upload a local file to Supabase Storage and return the public URL."""
    if not local_path or not os.path.exists(local_path):
        print(f"  [skip] File not found: {local_path}")
        return ''

    filename = os.path.basename(local_path)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')

    with open(local_path, 'rb') as f:
        data = f.read()

    print(f"  Uploading {filename} -> {bucket}...")
    supabase.storage.from_(bucket).upload(filename, data, {'content-type': content_type})
    url = supabase.storage.from_(bucket).get_public_url(filename)
    print(f"    {url}")
    return url


def migrate_url(url_path, bucket):
    """Convert a local /static/... URL to a Supabase Storage public URL."""
    if not url_path:
        return ''
    local_path = os.path.join(BASE_DIR, url_path.lstrip('/'))
    return upload_local_file(local_path, bucket)


def main():
    with open(CONTENT_PATH, 'r') as f:
        content = json.load(f)

    # ── Site Settings ──
    print('=== Site Settings ===')
    site = content.get('site', {})
    mascot_url = migrate_url(site.get('mascot_svg_url', ''), 'uploads')
    edition_pdf_url = migrate_url(content.get('current_edition_pdf_url', ''), 'pdfs')

    supabase.table('site_settings').upsert({
        'id': 1,
        'title': site.get('title', 'The Scope'),
        'mascot_url': mascot_url,
        'mission': site.get('mission', ''),
        'current_edition': content.get('current_edition', ''),
        'current_edition_title': content.get('current_edition_title', ''),
        'current_edition_pdf_url': edition_pdf_url,
        'submission_guide': content.get('submission_guide', ''),
    }).execute()
    print('  Done.\n')

    # ── Publications ──
    print('=== Publications ===')
    for pub in content.get('publications', []):
        pdf_url = migrate_url(pub.get('pdf_url', ''), 'pdfs')
        cover_url = migrate_url(pub.get('cover_url', ''), 'uploads')
        supabase.table('publications').upsert({
            'id': pub['id'],
            'title': pub.get('title', ''),
            'date': pub.get('date', None),
            'description': pub.get('description', ''),
            'pdf_url': pdf_url,
            'cover_url': cover_url,
        }).execute()
        print(f"  '{pub.get('title')}' done.")
    print()

    # ── News ──
    print('=== News ===')
    for article in content.get('news', []):
        image_url = migrate_url(article.get('image_url', ''), 'uploads')
        supabase.table('news').upsert({
            'id': article['id'],
            'title': article.get('title', ''),
            'author': article.get('author', ''),
            'preview': article.get('preview', ''),
            'full_text': article.get('full_text', ''),
            'date': article.get('date', None),
            'image_url': image_url,
        }).execute()
        print(f"  '{article.get('title')}' done.")
    print()

    # ── Team Members ──
    print('=== Team Members ===')
    for member in content.get('about', []):
        image_url = migrate_url(member.get('image_url', ''), 'uploads')
        supabase.table('team_members').upsert({
            'id': member['id'],
            'name': member.get('name', ''),
            'role': member.get('role', ''),
            'image_url': image_url,
            'sort_order': member.get('order', 0),
        }).execute()
        print(f"  '{member.get('name')}' done.")

    print('\n=== Migration complete! ===')


if __name__ == '__main__':
    main()
