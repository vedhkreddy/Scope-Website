import os
import uuid
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort,
)
from werkzeug.utils import secure_filename
import markdown2
import db

app = Flask(__name__)
app.secret_key = os.environ.get('SCOPE_SECRET_KEY', 'dev-secret')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}
ADMIN_PASSWORD = os.environ.get('SCOPE_ADMIN_PASSWORD', 'changeme')


def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


# Inject site settings into every template (replaces passing content= everywhere)
@app.context_processor
def inject_site():
    try:
        site = db.get_site_settings()
    except Exception:
        site = {'title': 'The Scope', 'mascot_url': '', 'mission': ''}
    return {'site': site}


# ── Error Handlers ─────────────────────────────────────────

@app.errorhandler(404)
def handle_404(e):
    return render_template('404.html'), 404


@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.error(f'Unhandled exception: {e}', exc_info=True)
    return render_template('error.html'), 500


# ── Public Pages ───────────────────────────────────────────

@app.route('/')
def home():
    site = db.get_site_settings()
    return render_template(
        'home.html',
        current_edition=site.get('current_edition', ''),
        current_edition_title=site.get('current_edition_title', ''),
        current_edition_pdf_url=site.get('current_edition_pdf_url', ''),
    )


@app.route('/publications')
def publications():
    pubs = db.get_publications()
    return render_template('publications.html', publications=pubs)


@app.route('/news')
def news():
    news_articles = db.get_news()
    return render_template('news.html', news_articles=news_articles)


@app.route('/news/<news_id>')
def news_detail(news_id):
    article = db.get_news_article(news_id)
    if not article:
        abort(404)
    return render_template('news_detail.html', article=article)


@app.route('/submission-guide')
def submission_guide():
    site = db.get_site_settings()
    guide_md = site.get('submission_guide', '')
    guide_html = markdown2.markdown(guide_md) if guide_md else ''
    return render_template('submission_guide.html', guide_html=guide_html)


@app.route('/about')
def about():
    team = db.get_team()
    return render_template('about.html', team=team)


# ── Admin Auth ─────────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        if request.method == 'POST':
            if request.form.get('password') == ADMIN_PASSWORD:
                session['admin'] = True
                return redirect(url_for('admin'))
            else:
                flash('Incorrect password.', 'danger')
        return render_template('admin_login.html')
    return render_template('admin_dashboard.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))


# ── Admin: Edition ─────────────────────────────────────────

@app.route('/admin/edition', methods=['GET', 'POST'])
def admin_edition():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    site = db.get_site_settings()
    current_edition = site.get('current_edition', '')
    current_edition_title = site.get('current_edition_title', '')
    current_edition_pdf_url = site.get('current_edition_pdf_url', '')

    if request.method == 'POST':
        new_edition = request.form.get('current_edition', '').strip()
        new_title = request.form.get('current_edition_title', '').strip()
        pdf = request.files.get('pdf')

        if not new_edition or not new_title:
            flash('Both fields are required.', 'danger')
            return render_template('admin_edition_form.html',
                current_edition=new_edition, current_edition_title=new_title,
                current_edition_pdf_url=current_edition_pdf_url)

        pdf_url = current_edition_pdf_url
        if pdf and pdf.filename:
            if not allowed_file(pdf.filename, ALLOWED_PDF_EXTENSIONS):
                flash('Please upload a valid PDF file.', 'danger')
                return render_template('admin_edition_form.html',
                    current_edition=new_edition, current_edition_title=new_title,
                    current_edition_pdf_url=current_edition_pdf_url)
            db.delete_file('pdfs', current_edition_pdf_url)
            pdf_url = db.upload_file('pdfs', pdf, secure_filename(pdf.filename))
        elif not current_edition_pdf_url:
            flash('A PDF file is required for the edition.', 'danger')
            return render_template('admin_edition_form.html',
                current_edition=new_edition, current_edition_title=new_title,
                current_edition_pdf_url=current_edition_pdf_url)

        db.update_site_settings({
            'current_edition': new_edition,
            'current_edition_title': new_title,
            'current_edition_pdf_url': pdf_url,
        })
        flash('Edition info updated!', 'success')
        return redirect(url_for('admin'))

    return render_template('admin_edition_form.html',
        current_edition=current_edition, current_edition_title=current_edition_title,
        current_edition_pdf_url=current_edition_pdf_url)


# ── Admin: Site Title & Mascot ─────────────────────────────

@app.route('/admin/site', methods=['GET', 'POST'])
def admin_site():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    site = db.get_site_settings()
    site_title = site.get('title', '')
    mascot_url = site.get('mascot_url', '')

    if request.method == 'POST':
        new_title = request.form.get('site_title', '').strip()
        mascot = request.files.get('mascot')

        if not new_title:
            flash('Site title is required.', 'danger')
            return render_template('admin_site_form.html',
                site_title=new_title, mascot_svg_url=mascot_url)

        new_mascot_url = mascot_url
        if mascot and mascot.filename:
            ext = mascot.filename.rsplit('.', 1)[-1].lower()
            if ext not in ('svg', 'png'):
                flash('Mascot must be SVG or PNG.', 'danger')
                return render_template('admin_site_form.html',
                    site_title=new_title, mascot_svg_url=mascot_url)
            db.delete_file('uploads', mascot_url)
            new_mascot_url = db.upload_file('uploads', mascot, secure_filename(mascot.filename))

        db.update_site_settings({'title': new_title, 'mascot_url': new_mascot_url})
        flash('Site info updated!', 'success')
        return redirect(url_for('admin'))

    return render_template('admin_site_form.html',
        site_title=site_title, mascot_svg_url=mascot_url)


# ── Admin: Submission Guide ────────────────────────────────

@app.route('/admin/submission-guide', methods=['GET', 'POST'])
def admin_submission_guide():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    site = db.get_site_settings()
    guide_md = site.get('submission_guide', '')

    if request.method == 'POST':
        new_md = request.form.get('guide_md', '').strip()
        db.update_site_settings({'submission_guide': new_md})
        flash('Submission guide updated!', 'success')
        return redirect(url_for('admin_submission_guide'))

    return render_template('admin_submission_guide.html', guide_md=guide_md)


# ── Admin: Publications CRUD ──────────────────────────────

@app.route('/admin/publications')
def admin_publications():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    pubs = db.get_publications()
    return render_template('admin_publications_list.html', publications=pubs)


@app.route('/admin/publications/add', methods=['GET', 'POST'])
def admin_publications_add():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        description = request.form.get('description', '').strip()
        pdf = request.files.get('pdf')
        cover = request.files.get('cover')

        pdf_url = ''
        cover_url = ''

        if not pdf or not allowed_file(pdf.filename, ALLOWED_PDF_EXTENSIONS):
            flash('A valid PDF file is required.', 'danger')
            return render_template('admin_publications_form.html', action='Add', pub=None)

        pdf_url = db.upload_file('pdfs', pdf, secure_filename(pdf.filename))

        if cover and allowed_file(cover.filename, ALLOWED_IMAGE_EXTENSIONS):
            cover_url = db.upload_file('uploads', cover, secure_filename(cover.filename))

        db.add_publication({
            'id': uuid.uuid4().hex,
            'title': title,
            'date': date,
            'description': description,
            'pdf_url': pdf_url,
            'cover_url': cover_url,
        })
        flash('Publication added!', 'success')
        return redirect(url_for('admin_publications'))

    return render_template('admin_publications_form.html', action='Add', pub=None)


@app.route('/admin/publications/edit/<pub_id>', methods=['GET', 'POST'])
def admin_publications_edit(pub_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    pub = db.get_publication(pub_id)
    if not pub:
        flash('Publication not found.', 'danger')
        return redirect(url_for('admin_publications'))

    if request.method == 'POST':
        updates = {
            'title': request.form.get('title', '').strip(),
            'date': request.form.get('date', pub.get('date', datetime.now().strftime('%Y-%m-%d'))),
            'description': request.form.get('description', '').strip(),
        }

        pdf = request.files.get('pdf')
        cover = request.files.get('cover')

        if pdf and pdf.filename:
            if not allowed_file(pdf.filename, ALLOWED_PDF_EXTENSIONS):
                flash('Invalid PDF file.', 'danger')
                return render_template('admin_publications_form.html', action='Edit', pub=pub)
            db.delete_file('pdfs', pub.get('pdf_url', ''))
            updates['pdf_url'] = db.upload_file('pdfs', pdf, secure_filename(pdf.filename))

        if cover and allowed_file(cover.filename, ALLOWED_IMAGE_EXTENSIONS):
            db.delete_file('uploads', pub.get('cover_url', ''))
            updates['cover_url'] = db.upload_file('uploads', cover, secure_filename(cover.filename))

        db.update_publication(pub_id, updates)
        flash('Publication updated!', 'success')
        return redirect(url_for('admin_publications'))

    return render_template('admin_publications_form.html', action='Edit', pub=pub)


@app.route('/admin/publications/delete/<pub_id>', methods=['POST'])
def admin_publications_delete(pub_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    pub = db.get_publication(pub_id)
    if pub:
        db.delete_file('pdfs', pub.get('pdf_url', ''))
        db.delete_file('uploads', pub.get('cover_url', ''))
        db.delete_publication(pub_id)
        flash('Publication deleted.', 'success')
    else:
        flash('Publication not found.', 'danger')
    return redirect(url_for('admin_publications'))


# ── Admin: News CRUD ──────────────────────────────────────

@app.route('/admin/news')
def admin_news():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    news_articles = db.get_news()
    return render_template('admin_news_list.html', news=news_articles)


@app.route('/admin/news/add', methods=['GET', 'POST'])
def admin_news_add():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        preview = request.form.get('preview', '').strip()
        full_text = request.form.get('full_text', '').strip()
        date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        image = request.files.get('image')

        image_url = ''
        if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            image_url = db.upload_file('uploads', image, secure_filename(image.filename))

        db.add_news({
            'id': uuid.uuid4().hex,
            'title': title,
            'author': author,
            'preview': preview,
            'full_text': full_text,
            'date': date,
            'image_url': image_url,
        })
        flash('Article added!', 'success')
        return redirect(url_for('admin_news'))

    return render_template('admin_news_form.html', action='Add', news_item=None)


@app.route('/admin/news/edit/<news_id>', methods=['GET', 'POST'])
def admin_news_edit(news_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    news_item = db.get_news_article(news_id)
    if not news_item:
        flash('Article not found.', 'danger')
        return redirect(url_for('admin_news'))

    if request.method == 'POST':
        updates = {
            'title': request.form.get('title', '').strip(),
            'author': request.form.get('author', '').strip(),
            'preview': request.form.get('preview', '').strip(),
            'full_text': request.form.get('full_text', '').strip(),
            'date': request.form.get('date', news_item.get('date', datetime.now().strftime('%Y-%m-%d'))),
        }

        image = request.files.get('image')
        if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            db.delete_file('uploads', news_item.get('image_url', ''))
            updates['image_url'] = db.upload_file('uploads', image, secure_filename(image.filename))

        db.update_news(news_id, updates)
        flash('Article updated!', 'success')
        return redirect(url_for('admin_news'))

    return render_template('admin_news_form.html', action='Edit', news_item=news_item)


@app.route('/admin/news/delete/<news_id>', methods=['POST'])
def admin_news_delete(news_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    article = db.get_news_article(news_id)
    if article:
        db.delete_file('uploads', article.get('image_url', ''))
        db.delete_news(news_id)
        flash('Article deleted.', 'success')
    else:
        flash('Article not found.', 'danger')
    return redirect(url_for('admin_news'))


# ── Admin: About/Team CRUD ────────────────────────────────

@app.route('/admin/about')
def admin_about():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    team = db.get_team()
    return render_template('admin_about_list.html', team=team)


@app.route('/admin/about/add', methods=['GET', 'POST'])
def admin_about_add():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        role = request.form.get('role', '').strip()
        image = request.files.get('image')

        image_url = ''
        if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            image_url = db.upload_file('uploads', image, secure_filename(image.filename))

        team = db.get_team()
        order = len(team)

        db.add_member({
            'id': uuid.uuid4().hex,
            'name': name,
            'role': role,
            'image_url': image_url,
            'sort_order': order,
        })
        flash('Team member added!', 'success')
        return redirect(url_for('admin_about'))

    return render_template('admin_about_form.html', action='Add', member=None)


@app.route('/admin/about/edit/<member_id>', methods=['GET', 'POST'])
def admin_about_edit(member_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    member = db.get_member(member_id)
    if not member:
        flash('Team member not found.', 'danger')
        return redirect(url_for('admin_about'))

    if request.method == 'POST':
        updates = {
            'name': request.form.get('name', '').strip(),
            'role': request.form.get('role', '').strip(),
        }

        image = request.files.get('image')
        if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            db.delete_file('uploads', member.get('image_url', ''))
            updates['image_url'] = db.upload_file('uploads', image, secure_filename(image.filename))

        db.update_member(member_id, updates)
        flash('Team member updated!', 'success')
        return redirect(url_for('admin_about'))

    return render_template('admin_about_form.html', action='Edit', member=member)


@app.route('/admin/about/delete/<member_id>', methods=['POST'])
def admin_about_delete(member_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    member = db.get_member(member_id)
    if member:
        db.delete_file('uploads', member.get('image_url', ''))
        db.delete_member(member_id)
        # Reorder remaining members
        team = db.get_team()
        for i, m in enumerate(team):
            if m['sort_order'] != i:
                db.update_member(m['id'], {'sort_order': i})
        flash('Team member deleted.', 'success')
    else:
        flash('Team member not found.', 'danger')
    return redirect(url_for('admin_about'))


@app.route('/admin/about/move/<member_id>/<direction>', methods=['POST'])
def admin_about_move(member_id, direction):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    team = db.get_team()  # already sorted by sort_order
    idx = next((i for i, m in enumerate(team) if m['id'] == member_id), None)

    if idx is not None:
        if direction == 'up' and idx > 0:
            db.update_member(team[idx]['id'], {'sort_order': team[idx - 1]['sort_order']})
            db.update_member(team[idx - 1]['id'], {'sort_order': team[idx]['sort_order']})
        elif direction == 'down' and idx < len(team) - 1:
            db.update_member(team[idx]['id'], {'sort_order': team[idx + 1]['sort_order']})
            db.update_member(team[idx + 1]['id'], {'sort_order': team[idx]['sort_order']})
        flash('Team member moved!', 'success')
    else:
        flash('Team member not found.', 'danger')
    return redirect(url_for('admin_about'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=True)
