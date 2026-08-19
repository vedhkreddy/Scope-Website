import os
import uuid
from supabase import create_client, Client

url = os.environ.get('SUPABASE_URL', '')
key = os.environ.get('SUPABASE_KEY', '')

supabase: Client = None
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as exc:
        print(f"Warning: failed to initialize Supabase client: {exc}")
        supabase = None
else:
    print("Warning: SUPABASE_URL or SUPABASE_KEY not set; running with database disabled.")


DEFAULT_SITE_SETTINGS = {
    'title': 'The Scope', 'mascot_url': '', 'mission': '',
    'current_edition': '', 'current_edition_title': '',
    'current_edition_pdf_url': '', 'submission_guide': ''
}


# ── Site Settings ──────────────────────────────────────────

def get_site_settings():
    if not supabase:
        return dict(DEFAULT_SITE_SETTINGS)
    try:
        res = supabase.table('site_settings').select('*').eq('id', 1).execute()
        if res.data:
            return res.data[0]
    except Exception as exc:
        print(f"Warning: get_site_settings failed: {exc}")
    return dict(DEFAULT_SITE_SETTINGS)


def update_site_settings(fields: dict):
    if not supabase:
        return
    try:
        supabase.table('site_settings').update(fields).eq('id', 1).execute()
    except Exception as exc:
        print(f"Warning: update_site_settings failed: {exc}")


# ── Publications ───────────────────────────────────────────

def get_publications():
    if not supabase:
        return []
    try:
        res = supabase.table('publications').select('*').order('date', desc=True).execute()
        return res.data or []
    except Exception as exc:
        print(f"Warning: get_publications failed: {exc}")
        return []


def get_publication(pub_id):
    if not supabase:
        return None
    try:
        res = supabase.table('publications').select('*').eq('id', pub_id).execute()
        return res.data[0] if res.data else None
    except Exception as exc:
        print(f"Warning: get_publication failed: {exc}")
        return None


def add_publication(data):
    if not supabase:
        return
    try:
        supabase.table('publications').insert(data).execute()
    except Exception as exc:
        print(f"Warning: add_publication failed: {exc}")


def update_publication(pub_id, data):
    if not supabase:
        return
    try:
        supabase.table('publications').update(data).eq('id', pub_id).execute()
    except Exception as exc:
        print(f"Warning: update_publication failed: {exc}")


def delete_publication(pub_id):
    if not supabase:
        return
    try:
        supabase.table('publications').delete().eq('id', pub_id).execute()
    except Exception as exc:
        print(f"Warning: delete_publication failed: {exc}")


# ── News ───────────────────────────────────────────────────

def get_news():
    if not supabase:
        return []
    try:
        res = supabase.table('news').select('*').order('date', desc=True).execute()
        return res.data or []
    except Exception as exc:
        print(f"Warning: get_news failed: {exc}")
        return []


def get_news_article(news_id):
    if not supabase:
        return None
    try:
        res = supabase.table('news').select('*').eq('id', news_id).execute()
        return res.data[0] if res.data else None
    except Exception as exc:
        print(f"Warning: get_news_article failed: {exc}")
        return None


def add_news(data):
    if not supabase:
        return
    try:
        supabase.table('news').insert(data).execute()
    except Exception as exc:
        print(f"Warning: add_news failed: {exc}")


def update_news(news_id, data):
    if not supabase:
        return
    try:
        supabase.table('news').update(data).eq('id', news_id).execute()
    except Exception as exc:
        print(f"Warning: update_news failed: {exc}")


def delete_news(news_id):
    if not supabase:
        return
    try:
        supabase.table('news').delete().eq('id', news_id).execute()
    except Exception as exc:
        print(f"Warning: delete_news failed: {exc}")


# ── Team Members ───────────────────────────────────────────

def get_team():
    if not supabase:
        return []
    try:
        res = supabase.table('team_members').select('*').order('sort_order').execute()
        return res.data or []
    except Exception as exc:
        print(f"Warning: get_team failed: {exc}")
        return []


def get_member(member_id):
    if not supabase:
        return None
    try:
        res = supabase.table('team_members').select('*').eq('id', member_id).execute()
        return res.data[0] if res.data else None
    except Exception as exc:
        print(f"Warning: get_member failed: {exc}")
        return None


def add_member(data):
    if not supabase:
        return
    try:
        supabase.table('team_members').insert(data).execute()
    except Exception as exc:
        print(f"Warning: add_member failed: {exc}")


def update_member(member_id, data):
    if not supabase:
        return
    try:
        supabase.table('team_members').update(data).eq('id', member_id).execute()
    except Exception as exc:
        print(f"Warning: update_member failed: {exc}")


def delete_member(member_id):
    if not supabase:
        return
    try:
        supabase.table('team_members').delete().eq('id', member_id).execute()
    except Exception as exc:
        print(f"Warning: delete_member failed: {exc}")


# ── File Upload / Delete ──────────────────────────────────

CONTENT_TYPES = {
    'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'gif': 'image/gif', 'svg': 'image/svg+xml', 'pdf': 'application/pdf',
}


def upload_file(bucket, file_obj, filename):
    """Upload a file to Supabase Storage and return the public URL."""
    if not supabase:
        print("Warning: upload_file called but Supabase client is not configured.")
        return None
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')

    try:
        data = file_obj.read()
        supabase.storage.from_(bucket).upload(
            unique_name, data, {'content-type': content_type}
        )
        return supabase.storage.from_(bucket).get_public_url(unique_name)
    except Exception as exc:
        print(f"Warning: upload_file failed: {exc}")
        return None


def delete_file(bucket, file_url):
    """Delete a file from Supabase Storage given its public URL."""
    if not supabase or not file_url:
        return
    try:
        marker = f'/storage/v1/object/public/{bucket}/'
        idx = file_url.index(marker)
        path = file_url[idx + len(marker):]
        supabase.storage.from_(bucket).remove([path])
    except (ValueError, Exception):
        pass
