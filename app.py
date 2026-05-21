import io
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime
from difflib import SequenceMatcher
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory, jsonify
from dotenv import load_dotenv
from models import db, Part, Bin, SearchFeedback, PartEmbedding
import qrcode
import pytesseract
from PIL import Image
from storage import process_image, save_photo_local, delete_photo_local
from backup import create_backup, restore_backup
from search import (
    encode_candidate_ids,
    encode_scorer_metadata,
    normalize_query,
    search_parts,
)

load_dotenv()

app = Flask(__name__)
os.makedirs(app.instance_path, exist_ok=True)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
database_path = os.environ.get('INVENTORY_DATABASE_PATH', 'parts_inventory.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{database_path}"
upload_folder = os.environ.get('INVENTORY_UPLOAD_FOLDER')
if upload_folder:
    app.config['UPLOAD_FOLDER'] = (
        upload_folder if os.path.isabs(upload_folder)
        else os.path.join(app.root_path, upload_folder)
    )
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = int(
    os.environ.get('INVENTORY_MAX_UPLOAD_MB', 16)
) * 1024 * 1024

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

db.init_app(app)


def ensure_sqlite_schema():
    """Keep existing SQLite installs compatible with lightweight model changes."""
    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not database_uri.startswith('sqlite:///'):
        return

    db_path = database_uri.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.instance_path, db_path)
    if not os.path.exists(db_path):
        return

    with sqlite3.connect(db_path) as con:
        columns = [row[1] for row in con.execute("PRAGMA table_info(part)")]
        con.execute("""
            CREATE TABLE IF NOT EXISTS part_bin (
                part_id INTEGER NOT NULL REFERENCES part(id),
                bin_id INTEGER NOT NULL REFERENCES bin(id),
                PRIMARY KEY (part_id, bin_id)
            )
        """)
        if 'location_id' in columns:
            con.execute("""
                INSERT OR IGNORE INTO part_bin (part_id, bin_id)
                SELECT id, location_id FROM part
                WHERE location_id IS NOT NULL
            """)
        if 'usage_count' not in columns:
            con.execute("ALTER TABLE part ADD COLUMN usage_count INTEGER DEFAULT 0")
        stock_log_exists = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='stock_log'"
        ).fetchone()
        if stock_log_exists:
            con.execute("""
                UPDATE part
                SET usage_count = COALESCE((
                    SELECT SUM(ABS(change))
                    FROM stock_log
                    WHERE stock_log.part_id = part.id AND change < 0
                ), usage_count, 0)
            """)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_part_number(name, category):
    cat_code = (category or 'GEN')[:3].upper()
    name_code = re.sub(r'[^A-Z0-9]', '', name.upper())[:4]
    short_id = uuid.uuid4().hex[:4].upper()
    return f"{cat_code}-{name_code}-{short_id}"


# --- Dashboard ---

@app.route('/')
def dashboard():
    low_stock = Part.query.filter(Part.min_threshold > 0, Part.quantity <= Part.min_threshold).all()
    total_parts = Part.query.count()
    return render_template('dashboard.html',
                           low_stock=low_stock,
                           total_parts=total_parts)


# --- Parts ---

@app.route('/parts')
def parts_list():
    query = request.args.get('q', '')
    category = request.args.get('category', '')
    view = request.args.get('view', 'list')

    parts_query = Part.query
    if category:
        parts_query = parts_query.filter(Part.category == category)

    parts = parts_query.order_by(Part.name).all()
    categories = db.session.query(Part.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    search_results = []
    candidate_ids = '[]'
    scorer_metadata = '{}'

    if query:
        feedback_rows = SearchFeedback.query.order_by(
            SearchFeedback.created_at.desc()
        ).limit(200).all()
        embeddings = PartEmbedding.query.all()
        search_results = search_parts(query, parts, feedback_rows, embeddings)
        parts = [result.part for result in search_results]
        candidate_ids = encode_candidate_ids(search_results)
        scorer_metadata = encode_scorer_metadata(search_results)

    return render_template('parts/list.html',
                           parts=parts,
                           search_results=search_results,
                           candidate_ids=candidate_ids,
                           scorer_metadata=scorer_metadata,
                           query=query,
                           category=category,
                           categories=categories,
                           view=view)


@app.route('/search-feedback', methods=['POST'])
def search_feedback():
    query = request.form.get('query', '').strip()
    part_id = int(request.form['part_id'])
    Part.query.get_or_404(part_id)
    candidate_ids = request.form.get('candidate_ids', '[]')
    scorer_metadata = request.form.get('scorer_metadata', '{}')

    try:
        json.loads(candidate_ids)
        json.loads(scorer_metadata)
    except json.JSONDecodeError:
        candidate_ids = '[]'
        scorer_metadata = '{}'

    feedback = SearchFeedback(
        query_text=query,
        normalized_query=normalize_query(query),
        candidate_part_ids=candidate_ids,
        selected_part_id=part_id,
        scorer_metadata=scorer_metadata,
    )
    db.session.add(feedback)
    db.session.commit()
    flash('Search feedback saved.', 'success')
    return redirect(url_for(
        'parts_list',
        q=query,
        category=request.form.get('category', ''),
    ))


@app.route('/parts/new', methods=['GET', 'POST'])
def part_new():
    bins = Bin.query.order_by(Bin.name).all()
    if request.method == 'POST':
        name = request.form['name']
        category = request.form.get('category', '')
        part_number = generate_part_number(name, category)

        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                photo_filename = f"{part_number}.webp"
                photo_bytes = process_image(file.stream)
                save_photo_local(photo_bytes, photo_filename, app.config['UPLOAD_FOLDER'])

        location_ids = [int(i) for i in request.form.getlist('location_ids') if i]
        selected_bins = Bin.query.filter(Bin.id.in_(location_ids)).all() if location_ids else []

        part = Part(
            part_number=part_number,
            name=name,
            description=request.form.get('description', ''),
            category=category,
            photo_filename=photo_filename,
            quantity=int(request.form.get('quantity', 0)),
            min_threshold=int(request.form.get('min_threshold', 0)),
            cost=float(request.form['cost']) if request.form.get('cost') else None,
            locations=selected_bins,
        )
        db.session.add(part)
        db.session.commit()
        flash(f'Part {part_number} added.', 'success')
        return redirect(url_for('part_detail', id=part.id))

    return render_template('parts/form.html', part=None, bins=bins)


@app.route('/parts/<int:id>')
def part_detail(id):
    part = Part.query.get_or_404(id)
    return render_template('parts/detail.html', part=part)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/parts/<int:id>/edit', methods=['GET', 'POST'])
def part_edit(id):
    part = Part.query.get_or_404(id)
    bins = Bin.query.order_by(Bin.name).all()

    if request.method == 'POST':
        part.name = request.form['name']
        part.description = request.form.get('description', '')
        part.category = request.form.get('category', '')
        part.quantity = int(request.form.get('quantity', 0))
        part.min_threshold = int(request.form.get('min_threshold', 0))
        part.cost = float(request.form['cost']) if request.form.get('cost') else None

        location_ids = [int(i) for i in request.form.getlist('location_ids') if i]
        part.locations = Bin.query.filter(Bin.id.in_(location_ids)).all() if location_ids else []

        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                photo_filename = f"{part.part_number}.webp"
                photo_bytes = process_image(file.stream)
                save_photo_local(photo_bytes, photo_filename, app.config['UPLOAD_FOLDER'])
                part.photo_filename = photo_filename

        db.session.commit()
        flash('Part updated.', 'success')
        return redirect(url_for('part_detail', id=part.id))

    return render_template('parts/form.html', part=part, bins=bins)


@app.route('/parts/<int:id>/delete', methods=['POST'])
def part_delete(id):
    part = Part.query.get_or_404(id)
    if part.photo_filename:
        delete_photo_local(part.photo_filename, app.config['UPLOAD_FOLDER'])
    db.session.delete(part)
    db.session.commit()
    flash('Part deleted.', 'success')
    return redirect(url_for('parts_list'))


@app.route('/parts/<int:id>/adjust', methods=['POST'])
def part_adjust_stock(id):
    part = Part.query.get_or_404(id)
    if request.form.get('new_quantity') is not None:
        new_quantity = max(0, int(request.form['new_quantity']))
        change = new_quantity - part.quantity
    else:
        change = int(request.form['change'])

    part.quantity += change
    if change < 0:
        part.usage_count = (part.usage_count or 0) + abs(change)
    db.session.commit()

    flash(f'Stock adjusted by {change:+d}.', 'success')
    return redirect(url_for('part_detail', id=part.id))


# --- Bins ---

@app.route('/bins')
def bins_list():
    bins = Bin.query.order_by(Bin.shelf, Bin.row, Bin.position).all()
    return render_template('bins/list.html', bins=bins)


@app.route('/bins/new', methods=['GET', 'POST'])
def bin_new():
    if request.method == 'POST':
        bin = Bin(
            name=request.form['name'],
            shelf=request.form.get('shelf', ''),
            row=request.form.get('row', ''),
            position=request.form.get('position', ''),
            accessibility=int(request.form.get('accessibility', 5)),
        )
        db.session.add(bin)
        db.session.commit()
        flash(f'Bin "{bin.name}" created.', 'success')
        return redirect(url_for('bins_list'))

    return render_template('bins/form.html', bin=None)


@app.route('/bins/<int:id>/edit', methods=['GET', 'POST'])
def bin_edit(id):
    bin = Bin.query.get_or_404(id)
    if request.method == 'POST':
        bin.name = request.form['name']
        bin.shelf = request.form.get('shelf', '')
        bin.row = request.form.get('row', '')
        bin.position = request.form.get('position', '')
        bin.accessibility = int(request.form.get('accessibility', 5))
        db.session.commit()
        flash('Bin updated.', 'success')
        return redirect(url_for('bins_list'))

    return render_template('bins/form.html', bin=bin)


# --- QR Codes ---

@app.route('/parts/<int:id>/qr')
def part_qr(id):
    part = Part.query.get_or_404(id)
    url = request.host_url.rstrip('/') + url_for('part_detail', id=part.id)
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', download_name=f'qr_{part.part_number}.png')


@app.route('/bins/<int:id>')
def bin_detail(id):
    bin = Bin.query.get_or_404(id)
    view = request.args.get('view', 'list')
    return render_template('bins/detail.html', bin=bin, view=view)


@app.route('/bins/<int:id>/qr')
def bin_qr(id):
    bin = Bin.query.get_or_404(id)
    url = request.host_url.rstrip('/') + url_for('bin_detail', id=bin.id)
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', download_name=f'qr_bin_{bin.name}.png')


# --- Dymo Labels ---

@app.route('/parts/<int:id>/label')
def part_label(id):
    part = Part.query.get_or_404(id)
    primary_bin = part.locations[0] if part.locations else None
    return render_template('label.html', part=part, bin=primary_bin)


@app.route('/bins/<int:id>/label')
def bin_label(id):
    bin = Bin.query.get_or_404(id)
    return render_template('label.html', part=None, bin=bin)


# --- Reorder ---

@app.route('/reorder')
def reorder():
    low_stock = Part.query.filter(Part.min_threshold > 0, Part.quantity <= Part.min_threshold).order_by(Part.category).all()
    by_category = {}
    for part in low_stock:
        cat = part.category or 'Uncategorized'
        by_category.setdefault(cat, []).append(part)
    return render_template('reorder.html', by_category=by_category, total=len(low_stock))


# --- Duplicate Detection ---

def find_similar_parts(name, threshold=0.6):
    all_parts = Part.query.all()
    matches = []
    for part in all_parts:
        ratio = SequenceMatcher(None, name.lower(), part.name.lower()).ratio()
        if ratio >= threshold:
            matches.append({'part': part, 'similarity': round(ratio * 100)})
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    return matches[:5]


@app.route('/api/check-duplicates')
def check_duplicates():
    name = request.args.get('name', '')
    if len(name) < 3:
        return jsonify([])
    matches = find_similar_parts(name)
    return jsonify([
        {'id': m['part'].id, 'name': m['part'].name,
         'part_number': m['part'].part_number, 'similarity': m['similarity']}
        for m in matches
    ])


# --- Purchase Order Intake ---

def match_line_to_part(line):
    """Try to match an OCR line to an existing part."""
    line_clean = line.strip()
    if len(line_clean) < 3:
        return None
    best_match = None
    best_ratio = 0
    for part in Part.query.all():
        ratio = SequenceMatcher(None, line_clean.lower(), part.name.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = part
        pn_ratio = SequenceMatcher(None, line_clean.upper(), part.part_number).ratio()
        if pn_ratio > best_ratio:
            best_ratio = pn_ratio
            best_match = part
    if best_ratio >= 0.5:
        return {'part': best_match, 'confidence': round(best_ratio * 100)}
    return None


def extract_quantity(line):
    """Try to pull a quantity number from the beginning or end of a line."""
    match = re.search(r'\b(\d{1,4})\b', line)
    if match:
        return int(match.group(1))
    return 1


@app.route('/intake', methods=['GET', 'POST'])
def intake():
    results = None
    raw_text = ''

    if request.method == 'POST':
        if 'po_image' in request.files and request.files['po_image'].filename:
            file = request.files['po_image']
            img = Image.open(file.stream)
            raw_text = pytesseract.image_to_string(img)
        elif request.form.get('po_text'):
            raw_text = request.form['po_text']

        if raw_text:
            lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
            results = []
            for line in lines:
                match = match_line_to_part(line)
                qty = extract_quantity(line)
                results.append({
                    'line': line,
                    'match': match,
                    'qty': qty,
                })

    return render_template('intake.html', results=results, raw_text=raw_text)


@app.route('/intake/receive', methods=['POST'])
def intake_receive():
    part_ids = request.form.getlist('part_id')
    quantities = request.form.getlist('quantity')
    received = 0

    for part_id, qty in zip(part_ids, quantities):
        if not part_id or not qty:
            continue
        part = Part.query.get(int(part_id))
        if part:
            change = int(qty)
            part.quantity += change
            received += 1

    db.session.commit()
    flash(f'Received {received} items into stock.', 'success')
    return redirect(url_for('intake'))


# --- Layout Optimization ---

@app.route('/optimize')
def optimize():
    parts = Part.query.filter(Part.locations.any()).all()

    suggestions = []
    for part in parts:
        usage = part.usage_count or 0
        for bin in part.locations:
            score = usage - bin.accessibility
            if usage >= 3 and bin.accessibility <= 5:
                better_bins = Bin.query.filter(
                    Bin.accessibility > bin.accessibility
                ).order_by(Bin.accessibility.desc()).limit(3).all()
                if better_bins:
                    suggestions.append({
                        'part': part,
                        'current_bin': bin,
                        'usage': usage,
                        'suggested_bins': better_bins,
                        'priority': score,
                    })
            elif usage <= 1 and bin.accessibility >= 8:
                lower_bins = Bin.query.filter(
                    Bin.accessibility < bin.accessibility
                ).order_by(Bin.accessibility.asc()).limit(3).all()
                if lower_bins:
                    suggestions.append({
                        'part': part,
                        'current_bin': bin,
                        'usage': usage,
                        'suggested_bins': lower_bins,
                        'priority': -score,
                    })

    suggestions.sort(key=lambda s: s['priority'], reverse=True)
    return render_template('optimize.html', suggestions=suggestions)


@app.route('/optimize/move', methods=['POST'])
def optimize_move():
    part_id = int(request.form['part_id'])
    old_bin_id = int(request.form['old_bin_id'])
    new_bin_id = int(request.form['new_bin_id'])
    part = Part.query.get_or_404(part_id)
    old_bin = Bin.query.get(old_bin_id)
    new_bin = Bin.query.get_or_404(new_bin_id)
    if old_bin and old_bin in part.locations:
        part.locations.remove(old_bin)
    if new_bin not in part.locations:
        part.locations.append(new_bin)
    db.session.commit()
    flash(f'Moved "{part.name}" from {old_bin.name if old_bin else "nowhere"} to {new_bin.name}.', 'success')
    return redirect(url_for('optimize'))


# --- Backup ---

@app.route('/backup', methods=['POST'])
def backup():
    try:
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        sql_bytes = create_backup(db_url)
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
        filename = f"parts_inventory_backup_{timestamp}.sql"
        return send_file(
            io.BytesIO(sql_bytes),
            mimetype='application/sql',
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        flash(f'Backup failed: {e}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/restore', methods=['POST'])
def restore():
    file = request.files.get('backup_file')
    if not file or not file.filename:
        flash('Choose a backup file to restore.', 'error')
        return redirect(url_for('dashboard'))

    try:
        sql_bytes = file.read()
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        db.session.remove()
        db.engine.dispose()
        restore_backup(db_url, sql_bytes)
        db.create_all()
        ensure_sqlite_schema()
        flash('Backup restored.', 'success')
    except Exception as e:
        flash(f'Restore failed: {e}', 'error')
    return redirect(url_for('dashboard'))


# --- Init DB ---

with app.app_context():
    db.create_all()
    ensure_sqlite_schema()


if __name__ == '__main__':
    app.run(
        debug=os.environ.get('FLASK_DEBUG', '0') == '1',
        host=os.environ.get('FLASK_RUN_HOST', 'localhost'),
        port=int(os.environ.get('FLASK_RUN_PORT', 5001)),
    )
