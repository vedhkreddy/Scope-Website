import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SCOPE_SECRET_KEY', 'dev-secret')

# Config for uploads
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
PDF_FOLDER = os.path.join(app.root_path, 'static', 'pdfs')
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}
ADMIN_PASSWORD = os.environ.get('SCOPE_ADMIN_PASSWORD', 'changeme')
CONTENT_PATH = os.path.join(app.root_path, 'content.json')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PDF_FOLDER'] = PDF_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

def allowed_file(filename, allowed):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed

def load_content():
    with open(CONTENT_PATH, 'r') as f:
        return json.load(f)

def save_content(data):
    with open(CONTENT_PATH, 'w') as f:
        json.dump(data, f, indent=2)

@app.route('/')
def home():
    content = load_content()
    return render_template('home.html', content=content)


from datetime import datetime

def sort_publications(publications):
    return sorted(publications, key=lambda p: p.get('date', ''), reverse=True)

@app.route('/publications')
def publications():
    content = load_content()
    pubs = sort_publications(content.get('publications', []))
    return render_template('publications.html', publications=pubs, content=content)

@app.route('/news')
def news():
    content = load_content()
    return render_template('news.html', content=content)


import markdown2

@app.route('/submission-guide')
def submission_guide():
    content = load_content()
    guide_md = content.get('submission_guide', '')
    guide_html = markdown2.markdown(guide_md) if guide_md else ''
    return render_template('submission_guide.html', content=content, guide_html=guide_html)

# --- Admin Submission Guide Edit ---
@app.route('/admin/submission-guide', methods=['GET', 'POST'])
def admin_submission_guide():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    guide_md = content.get('submission_guide', '')
    if request.method == 'POST':
        new_md = request.form.get('guide_md', '').strip()
        content['submission_guide'] = new_md
        save_content(content)
        flash('Submission guide updated!', 'success')
        return redirect(url_for('admin_submission_guide'))
    return render_template('admin_submission_guide.html', guide_md=guide_md)


def sort_about(about):
    return sorted(about, key=lambda m: m.get('order', 0))

@app.route('/about')
def about():
    content = load_content()
    team = sort_about(content.get('about', []))
    return render_template('about.html', content=content, team=team)

# --- Admin About Us Team Management ---
@app.route('/admin/about')
def admin_about():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    team = sort_about(content.get('about', []))
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
            filename = f"about_{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"/static/uploads/{filename}"
        content = load_content()
        order = len(content.get('about', []))
        member = {
            'id': uuid.uuid4().hex,
            'name': name,
            'role': role,
            'image_url': image_url,
            'order': order
        }
        content['about'].append(member)
        save_content(content)
        flash('Team member added!', 'success')
        return redirect(url_for('admin_about'))
    return render_template('admin_about_form.html', action='Add', member=None)


@app.route('/admin/about/edit/<member_id>', methods=['GET', 'POST'])
def admin_about_edit(member_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    team = content.get('about', [])
    member = next((m for m in team if m['id'] == member_id), None)
    if not member:
        flash('Team member not found.', 'danger')
        return redirect(url_for('admin_about'))
    if request.method == 'POST':
        member['name'] = request.form.get('name', '').strip()
        member['role'] = request.form.get('role', '').strip()
        image = request.files.get('image')
        if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = f"about_{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            member['image_url'] = f"/static/uploads/{filename}"
        save_content(content)
        flash('Team member updated!', 'success')
        return redirect(url_for('admin_about'))
    return render_template('admin_about_form.html', action='Edit', member=member)

@app.route('/admin/about/delete/<member_id>', methods=['POST'])
def admin_about_delete(member_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    team = content.get('about', [])
    idx = next((i for i, m in enumerate(team) if m['id'] == member_id), None)
    if idx is not None:
        team.pop(idx)
        # Reorder remaining members
        for i, m in enumerate(team):
            m['order'] = i
        save_content(content)
        flash('Team member deleted.', 'success')
    else:
        flash('Team member not found.', 'danger')
    return redirect(url_for('admin_about'))

@app.route('/admin/about/move/<member_id>/<direction>', methods=['POST'])
def admin_about_move(member_id, direction):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    team = content.get('about', [])
    idx = next((i for i, m in enumerate(team) if m['id'] == member_id), None)
    if idx is not None:
        if direction == 'up' and idx > 0:
            team[idx]['order'], team[idx-1]['order'] = team[idx-1]['order'], team[idx]['order']
        elif direction == 'down' and idx < len(team)-1:
            team[idx]['order'], team[idx+1]['order'] = team[idx+1]['order'], team[idx]['order']
        team.sort(key=lambda m: m['order'])
        for i, m in enumerate(team):
            m['order'] = i
        save_content(content)
        flash('Team member moved!', 'success')
    else:
        flash('Team member not found.', 'danger')
    return redirect(url_for('admin_about'))


# --- Admin Portal ---
from datetime import datetime
import uuid

def require_admin():
    if 'admin' not in session:
        return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        if request.method == 'POST':
            password = request.form.get('password')
            if password == ADMIN_PASSWORD:
                session['admin'] = True
                return redirect(url_for('admin'))
            else:
                flash('Incorrect password.', 'danger')
        return render_template('admin_login.html')
    content = load_content()
    return render_template('admin_dashboard.html', content=content)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin'))

###########################################################
# --- Science in the News CRUD ---
###########################################################

# --- Publications CRUD ---
@app.route('/admin/publications')
def admin_publications():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    pubs = sort_publications(content.get('publications', []))
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
        errors = []
        pdf_url = ''
        cover_url = ''
        # Validate PDF
        if not pdf or not allowed_file(pdf.filename, ALLOWED_PDF_EXTENSIONS):
            errors.append('A valid PDF file is required.')
        else:
            pdf_filename = f"pub_{uuid.uuid4().hex}_{secure_filename(pdf.filename)}"
            pdf.save(os.path.join(app.config['PDF_FOLDER'], pdf_filename))
            pdf_url = f"/static/pdfs/{pdf_filename}"
        # Handle cover image (optional)
        if cover and allowed_file(cover.filename, ALLOWED_IMAGE_EXTENSIONS):
            cover_filename = f"pubcover_{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
            cover.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_filename))
            cover_url = f"/static/uploads/{cover_filename}"
        if errors:
            flash(' '.join(errors), 'danger')
            return render_template('admin_publications_form.html', action='Add', pub=None)
        pub_item = {
            'id': uuid.uuid4().hex,
            'title': title,
            'date': date,
            'description': description,
            'pdf_url': pdf_url,
            'cover_url': cover_url
        }
        content = load_content()
        content['publications'].insert(0, pub_item)
        save_content(content)
        flash('Publication added!', 'success')
        return redirect(url_for('admin_publications'))
    return render_template('admin_publications_form.html', action='Add', pub=None)

@app.route('/admin/publications/edit/<pub_id>', methods=['GET', 'POST'])
def admin_publications_edit(pub_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    pubs = content.get('publications', [])
    pub = next((p for p in pubs if p['id'] == pub_id), None)
    if not pub:
        flash('Publication not found.', 'danger')
        return redirect(url_for('admin_publications'))
    if request.method == 'POST':
        pub['title'] = request.form.get('title', '').strip()
        pub['date'] = request.form.get('date', pub.get('date', datetime.now().strftime('%Y-%m-%d')))
        pub['description'] = request.form.get('description', '').strip()
        pdf = request.files.get('pdf')
        cover = request.files.get('cover')
        # Validate PDF if uploaded
        if pdf and allowed_file(pdf.filename, ALLOWED_PDF_EXTENSIONS):
            pdf_filename = f"pub_{uuid.uuid4().hex}_{secure_filename(pdf.filename)}"
            pdf.save(os.path.join(app.config['PDF_FOLDER'], pdf_filename))
            pub['pdf_url'] = f"/static/pdfs/{pdf_filename}"
        elif pdf and not allowed_file(pdf.filename, ALLOWED_PDF_EXTENSIONS):
            flash('Invalid PDF file.', 'danger')
            return render_template('admin_publications_form.html', action='Edit', pub=pub)
        # Handle cover image (optional)
        if cover and allowed_file(cover.filename, ALLOWED_IMAGE_EXTENSIONS):
            cover_filename = f"pubcover_{uuid.uuid4().hex}_{secure_filename(cover.filename)}"
            cover.save(os.path.join(app.config['UPLOAD_FOLDER'], cover_filename))
            pub['cover_url'] = f"/static/uploads/{cover_filename}"
        save_content(content)
        flash('Publication updated!', 'success')
        return redirect(url_for('admin_publications'))
    return render_template('admin_publications_form.html', action='Edit', pub=pub)

@app.route('/admin/publications/delete/<pub_id>', methods=['POST'])
def admin_publications_delete(pub_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    pubs = content.get('publications', [])
    idx = next((i for i, p in enumerate(pubs) if p['id'] == pub_id), None)
    if idx is not None:
        pubs.pop(idx)
        save_content(content)
        flash('Publication deleted.', 'success')
    else:
        flash('Publication not found.', 'danger')
    return redirect(url_for('admin_publications'))
@app.route('/admin/news')
def admin_news():
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    return render_template('admin_news_list.html', news=content.get('news', []))

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
            filename = f"news_{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"/static/uploads/{filename}"
        news_item = {
            'id': uuid.uuid4().hex,
            'title': title,
            'author': author,
            'preview': preview,
            'full_text': full_text,
            'date': date,
            'image_url': image_url
        }
        content = load_content()
        content['news'].insert(0, news_item)
        save_content(content)
        flash('Article added!', 'success')
        return redirect(url_for('admin_news'))
    return render_template('admin_news_form.html', action='Add', news_item=None)

@app.route('/admin/news/edit/<news_id>', methods=['GET', 'POST'])
def admin_news_edit(news_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    news_list = content.get('news', [])
    news_item = next((n for n in news_list if n['id'] == news_id), None)
    if not news_item:
        flash('Article not found.', 'danger')
        return redirect(url_for('admin_news'))
    if request.method == 'POST':
        news_item['title'] = request.form.get('title', '').strip()
        news_item['author'] = request.form.get('author', '').strip()
        news_item['preview'] = request.form.get('preview', '').strip()
        news_item['full_text'] = request.form.get('full_text', '').strip()
        news_item['date'] = request.form.get('date', news_item.get('date', datetime.now().strftime('%Y-%m-%d')))
        image = request.files.get('image')
        if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTENSIONS):
            filename = f"news_{uuid.uuid4().hex}_{secure_filename(image.filename)}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            news_item['image_url'] = f"/static/uploads/{filename}"
        save_content(content)
        flash('Article updated!', 'success')
        return redirect(url_for('admin_news'))
    return render_template('admin_news_form.html', action='Edit', news_item=news_item)

@app.route('/admin/news/delete/<news_id>', methods=['POST'])
def admin_news_delete(news_id):
    if 'admin' not in session:
        return redirect(url_for('admin'))
    content = load_content()
    news_list = content.get('news', [])
    idx = next((i for i, n in enumerate(news_list) if n['id'] == news_id), None)
    if idx is not None:
        news_list.pop(idx)
        save_content(content)
        flash('Article deleted.', 'success')
    else:
        flash('Article not found.', 'danger')
    return redirect(url_for('admin_news'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)
