import os
import uuid
from supabase import create_client, Client

url = os.environ.get('SUPABASE_URL', '')
key = os.environ.get('SUPABASE_KEY', '')

supabase: Client = create_client(url, key) if url and key else None


# ── Site Settings ──────────────────────────────────────────

def get_site_settings():
    res = supabase.table('site_settings').select('*').eq('id', 1).execute()
    if res.data:
        return res.data[0]
    return {
        'title': 'The Scope', 'mascot_url': '', 'mission': '',
        'current_edition': '', 'current_edition_title': '',
        'current_edition_pdf_url': '', 'submission_guide': ''
    }


def update_site_settings(fields: dict):
    supabase.table('site_settings').update(fields).eq('id', 1).execute()


# ── Publications ───────────────────────────────────────────

def get_publications():
    res = supabase.table('publications').select('*').order('date', desc=True).execute()
    return res.data


def get_publication(pub_id):
    res = supabase.table('publications').select('*').eq('id', pub_id).execute()
    return res.data[0] if res.data else None


def add_publication(data):
    supabase.table('publications').insert(data).execute()


def update_publication(pub_id, data):
    supabase.table('publications').update(data).eq('id', pub_id).execute()


def delete_publication(pub_id):
    supabase.table('publications').delete().eq('id', pub_id).execute()


# ── News ───────────────────────────────────────────────────

def get_news():
    res = supabase.table('news').select('*').order('date', desc=True).execute()
    return res.data


def get_news_article(news_id):
    res = supabase.table('news').select('*').eq('id', news_id).execute()
    return res.data[0] if res.data else None


def add_news(data):
    supabase.table('news').insert(data).execute()


def update_news(news_id, data):
    supabase.table('news').update(data).eq('id', news_id).execute()


def delete_news(news_id):
    supabase.table('news').delete().eq('id', news_id).execute()


# ── Team Members ───────────────────────────────────────────

def get_team():
    res = supabase.table('team_members').select('*').order('sort_order').execute()
    return res.data


def get_member(member_id):
    res = supabase.table('team_members').select('*').eq('id', member_id).execute()
    return res.data[0] if res.data else None


def add_member(data):
    supabase.table('team_members').insert(data).execute()


def update_member(member_id, data):
    supabase.table('team_members').update(data).eq('id', member_id).execute()


def delete_member(member_id):
    supabase.table('team_members').delete().eq('id', member_id).execute()


# ── File Upload / Delete ──────────────────────────────────

CONTENT_TYPES = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'svg': 'image/svg+xml', 'pdf': 'application/pdf',
}


def upload_file(bucket, file_obj, filename):
    """Upload a file to Supabase Storage and return the public URL."""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')

    data = file_obj.read()
    supabase.storage.from_(bucket).upload(
        unique_name, data, {'content-type': content_type}
    )
    return supabase.storage.from_(bucket).get_public_url(unique_name)


def delete_file(bucket, file_url):
    """Delete a file from Supabase Storage given its public URL."""
    if not file_url:
        return
    try:
        marker = f'/storage/v1/object/public/{bucket}/'
        idx = file_url.index(marker)
        path = file_url[idx + len(marker):]
        supabase.storage.from_(bucket).remove([path])
    except (ValueError, Exception):
        pass
