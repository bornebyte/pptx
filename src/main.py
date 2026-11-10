import csv
import io
import json
import os
import time
import uuid
from datetime import datetime, date
from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for, Response, abort
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, PP_PARAGRAPH_ALIGNMENT
from pptx.enum.dml import MSO_THEME_COLOR
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from .models import db, Generation, Student, GeneratedFile, Feedback, get_analytics_summary

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, instance_path=os.path.join(PROJECT_ROOT, 'instance'))

# Configuration
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB default
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///pptgen.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CORS configuration (explicit allowlist)
ALLOWED_ORIGINS = {
    "https://notes.shubham-shah.com.np",
}

# Browser-based MCP clients send Origin headers. Non-browser MCP clients often
# omit them; when one is present, require an exact allowlist match.
MCP_ALLOWED_ORIGINS = ALLOWED_ORIGINS | {
    origin.strip()
    for origin in os.getenv(
        'MCP_ALLOWED_ORIGINS',
        'https://chatgpt.com,https://chat.openai.com,https://claude.ai,https://claude.com,http://localhost:3000,http://127.0.0.1:3000'
    ).split(',')
    if origin.strip()
}

MCP_LEGACY_PROTOCOL_VERSIONS = {'2025-03-26', '2025-06-18', '2025-11-25'}
MCP_MODERN_PROTOCOL_VERSIONS = {'2026-07-28'}
MCP_SUPPORTED_PROTOCOL_VERSIONS = MCP_LEGACY_PROTOCOL_VERSIONS | MCP_MODERN_PROTOCOL_VERSIONS
MCP_LATEST_LEGACY_PROTOCOL_VERSION = '2025-11-25'
PPTX_MIME_TYPE = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'

def is_allowed_origin(origin):
    if not origin:
        return False
    if origin in ALLOWED_ORIGINS:
        return True
    # Allow localhost for local development
    if origin.startswith("http://localhost:") or origin.startswith("https://localhost:"):
        return True
    if origin.startswith("http://127.0.0.1:") or origin.startswith("https://127.0.0.1:"):
        return True
    return False


def is_allowed_mcp_origin(origin):
    return origin in MCP_ALLOWED_ORIGINS

@app.before_request
def handle_preflight():
    if request.method != "OPTIONS":
        return None
    origin = request.headers.get("Origin")
    if not (is_allowed_origin(origin) or (request.path == '/mcp' and is_allowed_mcp_origin(origin))):
        return Response(status=403)
    resp = Response(status=204)
    resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = request.headers.get(
        "Access-Control-Request-Headers",
        "Content-Type, Authorization",
    )
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if is_allowed_origin(origin) or (request.path == '/mcp' and is_allowed_mcp_origin(origin)):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, MCP-Protocol-Version, Mcp-Method, Mcp-Name, Mcp-Session-Id"
        )
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        if request.path == '/mcp':
            response.headers["Access-Control-Expose-Headers"] = "MCP-Protocol-Version, Mcp-Session-Id"
    return response

# Admin credentials (change these!)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'changeme123')
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')

FONT = "Calibri"

# Initialize database
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Add Jinja2 filter for timezone conversion
@app.template_filter('to_local')
def to_local_filter(utc_time):
    """Convert UTC time to IST for display"""
    from .models import to_local_time
    return to_local_time(utc_time)

# Helper function to parse color
def parse_color(color_spec):
    """Parse color from various formats: 'red', '#FF0000', or [255, 0, 0]"""
    if isinstance(color_spec, list) and len(color_spec) == 3:
        return RGBColor(*color_spec)
    elif isinstance(color_spec, str):
        if color_spec.startswith('#'):
            # Hex color
            color_spec = color_spec.lstrip('#')
            return RGBColor(*[int(color_spec[i:i+2], 16) for i in (0, 2, 4)])
        else:
            # Named colors
            color_map = {
                'red': RGBColor(255, 0, 0),
                'blue': RGBColor(0, 0, 255),
                'green': RGBColor(0, 128, 0),
                'yellow': RGBColor(255, 255, 0),
                'orange': RGBColor(255, 165, 0),
                'purple': RGBColor(128, 0, 128),
                'pink': RGBColor(255, 192, 203),
                'brown': RGBColor(165, 42, 42),
                'gray': RGBColor(128, 128, 128),
                'black': RGBColor(0, 0, 0),
                'white': RGBColor(255, 255, 255),
            }
            return color_map.get(color_spec.lower(), RGBColor(0, 0, 0))
    return RGBColor(0, 0, 0)  # Default black

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'service': 'ppt-generator',
        'version': '1.0.0'
    })


# Admin Routes
@app.route('/admin')
def admin_redirect():
    """Redirect to admin login"""
    return redirect(url_for('admin_login'))


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            from flask import session
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin analytics dashboard"""
    from flask import session
    from .models import to_local_time
    
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get analytics data
    stats = get_analytics_summary()
    
    # Convert timestamps to local time and prepare student data for JSON serialization
    for gen in stats.get('recent_generations', []):
        if hasattr(gen, 'timestamp') and gen.timestamp:
            gen.local_timestamp = to_local_time(gen.timestamp)
        # Convert students to dictionaries for JSON serialization
        if hasattr(gen, 'students'):
            gen.students_json = [{'name': s.name, 'usn': s.usn} for s in gen.students]
    
    # Prepare chart data
    chart_dates = [str(d[0]) for d in stats['daily_counts']]
    chart_counts = [d[1] for d in stats['daily_counts']]
    
    return render_template('admin_dashboard.html', 
                         stats=stats,
                         chart_dates=chart_dates,
                         chart_counts=chart_counts)


@app.route('/admin/logout')
def admin_logout():
    """Logout admin"""
    from flask import session
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


def _require_api_key():
    """Optionally enforce API key if ADMIN_API_KEY is set."""
    if not ADMIN_API_KEY:
        return None
    header_key = request.headers.get('X-API-Key')
    bearer = request.headers.get('Authorization', '')
    bearer_key = bearer.replace('Bearer ', '', 1).strip() if bearer.startswith('Bearer ') else None
    if header_key == ADMIN_API_KEY or bearer_key == ADMIN_API_KEY:
        return None
    return jsonify({'error': 'Unauthorized'}), 401


def _serialize_generation(gen, include_students=True):
    return {
        'id': gen.id,
        'timestamp': gen.timestamp.isoformat() if gen.timestamp else None,
        'file_name': gen.file_name,
        'title': gen.title,
        'subtitle': gen.subtitle,
        'num_slides': gen.num_slides,
        'file_size': gen.file_size,
        'college_name': gen.college_name,
        'presentation_title': gen.presentation_title,
        'student_type': gen.student_type,
        'course': gen.course,
        'semester': gen.semester,
        'professor_name': gen.professor_name,
        'ip_address': gen.ip_address,
        'user_agent': gen.user_agent,
        'generation_time': gen.generation_time,
        'status': gen.status,
        'error_message': gen.error_message,
        'content_summary': gen.content_summary,
        'has_tables': gen.has_tables,
        'has_images': gen.has_images,
        'has_charts': gen.has_charts,
        'students': (
            [{'id': s.id, 'name': s.name, 'usn': s.usn} for s in gen.students]
            if include_students else []
        )
    }


def _parse_bool(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    v = str(value).strip().lower()
    if v in ('1', 'true', 'yes', 'y', 'on'):
        return True
    if v in ('0', 'false', 'no', 'n', 'off'):
        return False
    return None


def _build_generation_query(args):
    include_students = _parse_bool(args.get('include_students'))
    if include_students is None:
        include_students = True

    query = Generation.query

    # Text filters (case-insensitive partial match)
    def ilike(col, key):
        val = args.get(key)
        if val:
            return col.ilike(f"%{val}%")
        return None

    filters = [
        ilike(Generation.file_name, 'file_name'),
        ilike(Generation.title, 'title'),
        ilike(Generation.subtitle, 'subtitle'),
        ilike(Generation.college_name, 'college_name'),
        ilike(Generation.presentation_title, 'presentation_title'),
        ilike(Generation.course, 'course'),
        ilike(Generation.semester, 'semester'),
        ilike(Generation.professor_name, 'professor_name'),
        ilike(Generation.ip_address, 'ip'),
        ilike(Generation.user_agent, 'user_agent'),
        ilike(Generation.error_message, 'error_message'),
        ilike(Generation.content_summary, 'content_summary'),
    ]

    # Exact match filters
    status = args.get('status')
    if status:
        filters.append(Generation.status == status)
    student_type = args.get('student_type')
    if student_type:
        filters.append(Generation.student_type == student_type)

    # Boolean filters
    for key, col in [
        ('has_tables', Generation.has_tables),
        ('has_images', Generation.has_images),
        ('has_charts', Generation.has_charts),
    ]:
        b = _parse_bool(args.get(key))
        if b is not None:
            filters.append(col == b)

    # Range filters
    def add_range(col, min_key, max_key, cast=float):
        min_v = args.get(min_key)
        max_v = args.get(max_key)
        if min_v is not None:
            try:
                filters.append(col >= cast(min_v))
            except ValueError:
                pass
        if max_v is not None:
            try:
                filters.append(col <= cast(max_v))
            except ValueError:
                pass

    add_range(Generation.num_slides, 'min_slides', 'max_slides', int)
    add_range(Generation.file_size, 'min_file_size', 'max_file_size', int)
    add_range(Generation.generation_time, 'min_time', 'max_time', float)

    # Date range (ISO date or datetime)
    start = args.get('start')
    end = args.get('end')
    if start:
        try:
            filters.append(Generation.timestamp >= datetime.fromisoformat(start))
        except ValueError:
            pass
    if end:
        try:
            filters.append(Generation.timestamp <= datetime.fromisoformat(end))
        except ValueError:
            pass

    # Global search across key fields
    q = args.get('q')
    if q:
        like = f"%{q}%"
        filters.append(or_(
            Generation.file_name.ilike(like),
            Generation.title.ilike(like),
            Generation.subtitle.ilike(like),
            Generation.college_name.ilike(like),
            Generation.presentation_title.ilike(like),
            Generation.professor_name.ilike(like),
            Generation.content_summary.ilike(like),
        ))

    # Student filters (join only if needed)
    student_name = args.get('student_name')
    student_usn = args.get('student_usn')
    if student_name or student_usn:
        query = query.join(Student)
        if student_name:
            filters.append(Student.name.ilike(f"%{student_name}%"))
        if student_usn:
            filters.append(Student.usn.ilike(f"%{student_usn}%"))

    # Apply filters
    for f in filters:
        if f is not None:
            query = query.filter(f)

    # Sorting
    sort_by = args.get('sort_by', 'timestamp')
    sort_dir = args.get('sort_dir', 'desc').lower()
    sort_map = {
        'timestamp': Generation.timestamp,
        'file_name': Generation.file_name,
        'title': Generation.title,
        'num_slides': Generation.num_slides,
        'file_size': Generation.file_size,
        'generation_time': Generation.generation_time,
        'status': Generation.status,
        'college_name': Generation.college_name,
    }
    sort_col = sort_map.get(sort_by, Generation.timestamp)
    query = query.order_by(sort_col.desc() if sort_dir == 'desc' else sort_col.asc())

    return query, include_students


@app.route('/api/generations', methods=['GET'])
def api_generations():
    auth = _require_api_key()
    if auth:
        return auth
    limit = min(int(request.args.get('limit', 50)), 200)
    offset = max(int(request.args.get('offset', 0)), 0)
    query, include_students = _build_generation_query(request.args)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return jsonify({
        'total': total,
        'limit': limit,
        'offset': offset,
        'items': [_serialize_generation(g, include_students=include_students) for g in items]
    })


@app.route('/api/generations/<int:gen_id>', methods=['GET'])
def api_generation_detail(gen_id):
    auth = _require_api_key()
    if auth:
        return auth
    gen = Generation.query.get_or_404(gen_id)
    return jsonify(_serialize_generation(gen))


@app.route('/api/generations/export', methods=['GET'])
def api_generations_export():
    auth = _require_api_key()
    if auth:
        return auth

    export_format = request.args.get('format', 'csv').lower()
    limit = min(int(request.args.get('limit', 5000)), 10000)
    offset = max(int(request.args.get('offset', 0)), 0)

    query, include_students = _build_generation_query(request.args)
    items = query.offset(offset).limit(limit).all()

    if export_format == 'json':
        return jsonify({
            'count': len(items),
            'limit': limit,
            'offset': offset,
            'items': [_serialize_generation(g, include_students=include_students) for g in items]
        })

    if export_format != 'csv':
        return jsonify({'error': 'Invalid format. Use csv or json.'}), 400

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        'id', 'timestamp', 'file_name', 'title', 'subtitle', 'num_slides', 'file_size',
        'college_name', 'presentation_title', 'student_type', 'course', 'semester',
        'professor_name', 'ip_address', 'user_agent', 'generation_time', 'status',
        'error_message', 'content_summary', 'has_tables', 'has_images', 'has_charts'
    ]
    if include_students:
        headers += ['student_names', 'student_usns']
    writer.writerow(headers)

    for g in items:
        row = [
            g.id,
            g.timestamp.isoformat() if g.timestamp else '',
            g.file_name or '',
            g.title or '',
            g.subtitle or '',
            g.num_slides or '',
            g.file_size or '',
            g.college_name or '',
            g.presentation_title or '',
            g.student_type or '',
            g.course or '',
            g.semester or '',
            g.professor_name or '',
            g.ip_address or '',
            g.user_agent or '',
            g.generation_time or '',
            g.status or '',
            g.error_message or '',
            g.content_summary or '',
            g.has_tables,
            g.has_images,
            g.has_charts,
        ]
        if include_students:
            names = '; '.join([s.name for s in g.students]) if g.students else ''
            usns = '; '.join([s.usn or '' for s in g.students]) if g.students else ''
            row += [names, usns]
        writer.writerow(row)

    csv_data = output.getvalue()
    output.close()

    filename = f"generations_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


def style(run, size=18, bold=False, italic=False, color=None, underline=False):
    """Enhanced style function with more formatting options"""
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.underline = underline
    if color:
        run.font.color.rgb = parse_color(color)
    else:
        run.font.color.rgb = RGBColor(0, 0, 0)

def add_text(tf, text, level=0, size=18, bold=False, italic=False, color=None, align=None):
    """Enhanced text function with alignment and formatting"""
    p = tf.add_paragraph() if tf.text else tf.paragraphs[0]
    p.text = text
    p.level = level
    if align:
        alignment_map = {
            'left': PP_ALIGN.LEFT,
            'center': PP_ALIGN.CENTER,
            'right': PP_ALIGN.RIGHT,
            'justify': PP_ALIGN.JUSTIFY
        }
        p.alignment = alignment_map.get(align.lower(), PP_ALIGN.LEFT)
    for r in p.runs:
        style(r, size, bold, italic, color)

def render_heading(tf, block):
    """Render heading block"""
    text = block.get("text", "")
    level = block.get("level", 1)  # 1=large, 2=medium, 3=small
    color = block.get("color")
    align = block.get("align", "left")
    
    size_map = {1: 28, 2: 24, 3: 20}
    size = size_map.get(level, 24)
    
    add_text(tf, text, level=0, size=size, bold=True, color=color, align=align)

def render_paragraph(tf, block):
    """Render styled paragraph"""
    text = block.get("text", "")
    size = block.get("size", 18)
    color = block.get("color")
    bold = block.get("bold", False)
    italic = block.get("italic", False)
    align = block.get("align", "left")
    
    add_text(tf, text, size=size, bold=bold, italic=italic, color=color, align=align)

def render_bullets(tf, block):
    """Enhanced bullet rendering with styles"""
    items = block.get("items", [])
    bullet_color = block.get("color")
    
    for item in items:
        if isinstance(item, str):
            add_text(tf, item, color=bullet_color)
        else:
            # Styled bullet
            text = item.get("text", "")
            bold = item.get("bold", True)
            color = item.get("color", bullet_color)
            add_text(tf, text, bold=bold, color=color)
            
            # Sub-points
            for sub in item.get("subpoints", []):
                if isinstance(sub, str):
                    add_text(tf, sub, level=1, color=bullet_color)
                else:
                    sub_text = sub.get("text", "")
                    sub_color = sub.get("color", bullet_color)
                    add_text(tf, sub_text, level=1, color=sub_color)

def render_table(slide, block, top=2.5):
    """Render a table on the slide"""
    rows = block.get("rows", [])
    if not rows:
        return
    
    num_rows = len(rows)
    num_cols = len(rows[0]) if rows else 0
    
    # Position and size
    left = Inches(block.get("left", 1))
    top = Inches(block.get("top", top))
    width = Inches(block.get("width", 8))
    height = Inches(block.get("height", 0.4 * num_rows))
    
    # Create table
    table = slide.shapes.add_table(num_rows, num_cols, left, top, width, height).table
    
    # Set column widths
    col_widths = block.get("col_widths", [width.inches / num_cols] * num_cols)
    for i, col_width in enumerate(col_widths[:num_cols]):
        table.columns[i].width = Inches(col_width)
    
    # Fill table
    header = block.get("header", True)
    header_color = parse_color(block.get("header_color", [68, 114, 196]))  # Blue
    header_text_color = parse_color(block.get("header_text_color", "white"))
    
    for row_idx, row_data in enumerate(rows):
        for col_idx, cell_data in enumerate(row_data):
            cell = table.cell(row_idx, col_idx)
            
            # Cell text
            if isinstance(cell_data, dict):
                cell.text = str(cell_data.get("text", ""))
                cell_color = cell_data.get("color")
                bg_color = cell_data.get("bg_color")
            else:
                cell.text = str(cell_data)
                cell_color = None
                bg_color = None
            
            # Format cell
            cell.text_frame.paragraphs[0].font.size = Pt(block.get("font_size", 11))
            cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
            
            # Header row styling
            if header and row_idx == 0:
                cell.text_frame.paragraphs[0].font.bold = True
                cell.text_frame.paragraphs[0].font.color.rgb = header_text_color
                cell.fill.solid()
                cell.fill.fore_color.rgb = header_color
            elif bg_color:
                cell.fill.solid()
                cell.fill.fore_color.rgb = parse_color(bg_color)
            
            if cell_color:
                cell.text_frame.paragraphs[0].font.color.rgb = parse_color(cell_color)

def render_text_box(slide, block):
    """Render a text box with custom positioning and styling"""
    text = block.get("text", "")
    left = Inches(block.get("left", 1))
    top = Inches(block.get("top", 3))
    width = Inches(block.get("width", 6))
    height = Inches(block.get("height", 1))
    
    # Create text box
    text_box = slide.shapes.add_textbox(left, top, width, height)
    tf = text_box.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = text
    
    # Styling
    font_size = block.get("font_size", 18)
    bold = block.get("bold", False)
    italic = block.get("italic", False)
    color = block.get("color")
    bg_color = block.get("bg_color")
    align = block.get("align", "left")
    
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.italic = italic
    if color:
        p.font.color.rgb = parse_color(color)
    
    # Alignment
    alignment_map = {
        'left': PP_ALIGN.LEFT,
        'center': PP_ALIGN.CENTER,
        'right': PP_ALIGN.RIGHT,
        'justify': PP_ALIGN.JUSTIFY
    }
    p.alignment = alignment_map.get(align.lower(), PP_ALIGN.LEFT)
    
    # Background color
    if bg_color:
        text_box.fill.solid()
        text_box.fill.fore_color.rgb = parse_color(bg_color)

def render_numbered_list(tf, block):
    """Render numbered list"""
    items = block.get("items", [])
    start = block.get("start", 1)
    color = block.get("color")
    
    for i, item in enumerate(items, start=start):
        if isinstance(item, str):
            add_text(tf, f"{i}. {item}", color=color)
        else:
            text = item.get("text", "")
            item_color = item.get("color", color)
            add_text(tf, f"{i}. {text}", color=item_color)

def render_images(slide, block, top=2.5):
    items = block["items"]
    count = len(items)

    if block["layout"] == "row":
        width = 8 / count
        for i, img in enumerate(items):
            try:
                slide.shapes.add_picture(
                    img["path"],
                    Inches(0.5 + i * width),
                    Inches(top),
                    width=Inches(width - 0.2)
                )
            except FileNotFoundError:
                print(f"Warning: Image file not found at {img['path']}")

    elif block["layout"] == "column":
        height = 4 / count
        for i, img in enumerate(items):
            try:
                slide.shapes.add_picture(
                    img["path"],
                    Inches(2),
                    Inches(top + i * height),
                    height=Inches(height - 0.2)
                )
            except FileNotFoundError:
                print(f"Warning: Image file not found at {img['path']}")

    elif block["layout"] == "grid":
        cols = 2
        rows = (count + 1) // 2
        w, h = 4, 2
        for idx, img in enumerate(items):
            try:
                r, c = divmod(idx, cols)
                slide.shapes.add_picture(
                    img["path"],
                    Inches(0.5 + c * w),
                    Inches(top + r * h),
                    width=Inches(w - 0.3)
                )
            except FileNotFoundError:
                print(f"Warning: Image file not found at {img['path']}")

def render_blocks(slide, blocks):
    """Enhanced block renderer supporting multiple content types"""
    # Check if we have a text placeholder
    has_text_placeholder = len(slide.placeholders) > 1
    
    if has_text_placeholder:
        tf = slide.shapes.placeholders[1].text_frame
        tf.clear()
    else:
        tf = None
    
    current_top = 2.5  # Starting position for non-text elements
    
    for block in blocks:
        kind = block.get("kind", "")
        
        # Text-based blocks (use placeholder text frame)
        if kind == "heading" and tf:
            render_heading(tf, block)
            
        elif kind == "paragraph" and tf:
            render_paragraph(tf, block)
            
        elif kind == "bullets" and tf:
            render_bullets(tf, block)
            
        elif kind == "numbered_list" and tf:
            render_numbered_list(tf, block)
        
        # Positioned blocks (custom positioning)
        elif kind == "table":
            render_table(slide, block, current_top)
            current_top += block.get("height", 2) + 0.3
            
        elif kind == "text_box":
            render_text_box(slide, block)
            
        elif kind == "images":
            render_images(slide, block, current_top)
            # Calculate height used by images
            if block.get("layout") == "column":
                current_top += block.get("height", 4)
            else:
                current_top += 2.5
        
        # Legacy support for old "paragraph" without explicit kind
        elif "text" in block and kind == "" and tf:
            add_text(tf, block["text"])


def create_college_title_slide(prs, college_data):
    """Create custom college/university title slide"""
    # Use blank layout for custom design
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    
    # Add college logo at top center (if exists)
    logo_path = os.path.join(app.root_path, 'static', 'college.png')
    if os.path.exists(logo_path):
        left = Inches(3.5)  # Center position
        top = Inches(0.5)
        height = Inches(1.2)
        slide.shapes.add_picture(logo_path, left, top, height=height)
    
    # Add college/university name
    uni_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(0.5))
    uni_tf = uni_box.text_frame
    uni_tf.text = college_data.get('college_name', 'College/University Name')
    uni_p = uni_tf.paragraphs[0]
    uni_p.alignment = PP_ALIGN.CENTER
    uni_p.font.size = Pt(24)
    uni_p.font.bold = True
    uni_p.font.color.rgb = RGBColor(0, 0, 128)
    
    # Add presentation title
    title_box = slide.shapes.add_textbox(Inches(1), Inches(2.7), Inches(8), Inches(0.8))
    title_tf = title_box.text_frame
    title_tf.text = college_data.get('title', 'Presentation Title')
    title_tf.word_wrap = True
    title_p = title_tf.paragraphs[0]
    title_p.alignment = PP_ALIGN.CENTER
    title_p.font.size = Pt(32)
    title_p.font.bold = True
    title_p.font.color.rgb = RGBColor(0, 0, 0)
    
    # Check if single or group
    if college_data.get('type') == 'single':
        # Single student details
        details_top = 3.8
        details_box = slide.shapes.add_textbox(Inches(2), Inches(details_top), Inches(6), Inches(2.5))
        details_tf = details_box.text_frame
        details_tf.word_wrap = True
        
        # Submitted by
        p = details_tf.paragraphs[0]
        p.text = "Submitted By:"
        p.font.size = Pt(16)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER
        
        # Student details
        student_info = [
            f"Name: {college_data.get('student_name', '')}",
            f"USN: {college_data.get('usn', '')}",
            f"Course: {college_data.get('course', '')}",
            f"Semester: {college_data.get('semester', '')}"
        ]
        
        for info in student_info:
            p = details_tf.add_paragraph()
            p.text = info
            p.font.size = Pt(14)
            p.alignment = PP_ALIGN.CENTER
            p.space_before = Pt(6)
        
        # Submitted to
        p = details_tf.add_paragraph()
        p.text = f"\nSubmitted To: {college_data.get('professor', '')}"
        p.font.size = Pt(14)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER
        p.space_before = Pt(12)
        
    elif college_data.get('type') == 'group':
        # Group - create table for students
        students = college_data.get('students', [])
        
        # Add "Submitted By:" text
        sub_box = slide.shapes.add_textbox(Inches(2), Inches(3.7), Inches(6), Inches(0.4))
        sub_tf = sub_box.text_frame
        sub_p = sub_tf.paragraphs[0]
        sub_p.text = "Submitted By:"
        sub_p.font.size = Pt(16)
        sub_p.font.bold = True
        sub_p.alignment = PP_ALIGN.CENTER
        
        # Create table
        if students:
            rows = len(students) + 1  # +1 for header
            cols = 2
            left = Inches(2.5)
            top = Inches(4.2)
            width = Inches(5)
            height = Inches(0.4 * rows)
            
            table = slide.shapes.add_table(rows, cols, left, top, width, height).table
            
            # Set column widths
            table.columns[0].width = Inches(2.5)
            table.columns[1].width = Inches(2.5)
            
            # Header row
            table.cell(0, 0).text = "Name"
            table.cell(0, 1).text = "USN"
            
            for i, cell in enumerate([table.cell(0, 0), table.cell(0, 1)]):
                cell.text_frame.paragraphs[0].font.bold = True
                cell.text_frame.paragraphs[0].font.size = Pt(12)
                cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                cell.fill.solid()
                cell.fill.fore_color.rgb = RGBColor(200, 200, 200)
            
            # Data rows
            for idx, student in enumerate(students):
                table.cell(idx + 1, 0).text = student.get('name', '')
                table.cell(idx + 1, 1).text = student.get('usn', '')
                
                for col in range(2):
                    cell = table.cell(idx + 1, col)
                    cell.text_frame.paragraphs[0].font.size = Pt(11)
                    cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
        
        # Submitted to
        prof_box = slide.shapes.add_textbox(Inches(2), Inches(6.5), Inches(6), Inches(0.4))
        prof_tf = prof_box.text_frame
        prof_p = prof_tf.paragraphs[0]
        prof_p.text = f"Submitted To: {college_data.get('professor', '')}"
        prof_p.font.size = Pt(14)
        prof_p.font.bold = True
        prof_p.alignment = PP_ALIGN.CENTER


@app.route('/generate_ppt', methods=['POST'])
def generate_ppt():
    try:
        # Get JSON data from request or use default content.json
        if request.is_json:
            data = request.get_json() or {}
            if not isinstance(data, dict):
                return jsonify({'error': 'Request body must be a JSON object'}), 400
            if 'json_data' in data:
                # Parse JSON string from frontend
                content = data['json_data']
                if isinstance(content, str):
                    content = json.loads(content)
                file_name = data.get('file_name', 'presentation')
                jain_data = data.get('jain_data')  # Get college/university data if provided
            else:
                content = data
                file_name = 'presentation'
                jain_data = None
        else:
            # Fallback to content.json file
            with open(os.path.join(app.root_path, 'examples', 'content.json'), 'r', encoding='utf-8') as f:
                content = json.load(f)
            file_name = 'Generated'
            jain_data = None
        
        # Validate required fields
        if not isinstance(content, dict) or 'meta' not in content or 'slides' not in content:
            return jsonify({'error': 'Invalid JSON structure. Required: meta and slides'}), 400
        output = _generate_presentation(content, file_name, jain_data)
        return send_file(
            io.BytesIO(output['file_data']),
            as_attachment=True,
            download_name=output['file_name'],
            mimetype=PPTX_MIME_TYPE
        )
    except json.JSONDecodeError as e:
        return jsonify({'error': f'Invalid JSON: {str(e)}'}), 400
    except PresentationValidationError as e:
        return jsonify({'error': str(e)}), 400
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        print(f"Error generating PPT: {str(e)}")
        return jsonify({'error': str(e)}), 500


def _generate_presentation(content, file_name, jain_data=None, persist_download=False):
    """Generate a PPTX and write the existing analytics records in one transaction."""
    start_time = time.time()
    generation = None

    try:
        if not isinstance(content, dict) or not isinstance(content.get('meta'), dict) or not isinstance(content.get('slides'), list):
            raise ValueError('Invalid presentation. Provide an object with meta and slides.')
        _normalize_presentation_slides(content)
        if jain_data is not None and not isinstance(jain_data, dict):
            raise ValueError('jain_data must be an object.')

        safe_name = secure_filename(str(file_name or 'presentation')) or 'presentation'
        output_filename = f'{safe_name}.pptx'

        # Analyze content for the same tracking fields used by the web endpoint.
        num_slides = len([s for s in content['slides'] if s.get('type') != 'title'])
        has_tables = any('table' in str(s.get('blocks', [])).lower() for s in content['slides'])
        has_images = any('image' in str(s.get('blocks', [])).lower() for s in content['slides'])
        has_charts = any('chart' in str(s.get('blocks', [])).lower() for s in content['slides'])

        generation = Generation(
            file_name=file_name,
            title=content.get('meta', {}).get('title', 'Untitled'),
            subtitle=content.get('meta', {}).get('subtitle'),
            num_slides=num_slides,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=request.headers.get('User-Agent', '')[:500],
            has_tables=has_tables,
            has_images=has_images,
            has_charts=has_charts,
            status='processing'
        )

        if jain_data and jain_data.get('enabled'):
            generation.college_name = jain_data.get('college_name')
            generation.presentation_title = jain_data.get('title')
            generation.student_type = jain_data.get('type')
            generation.course = jain_data.get('course')
            generation.semester = jain_data.get('semester')
            generation.professor_name = jain_data.get('professor')

        db.session.add(generation)
        db.session.flush()

        if jain_data and jain_data.get('enabled'):
            if jain_data.get('type') == 'single':
                db.session.add(Student(
                    generation_id=generation.id,
                    name=jain_data.get('student_name', ''),
                    usn=jain_data.get('usn', '')
                ))
            elif jain_data.get('type') == 'group':
                for student_data in jain_data.get('students', []):
                    db.session.add(Student(
                        generation_id=generation.id,
                        name=student_data.get('name', ''),
                        usn=student_data.get('usn', '')
                    ))

        prs = Presentation()
        if jain_data and jain_data.get('enabled'):
            create_college_title_slide(prs, jain_data)
        else:
            slide = prs.slides.add_slide(prs.slide_layouts[0])
            slide.shapes.title.text = content['meta'].get('title', 'Presentation')
            if len(slide.placeholders) > 1:
                slide.placeholders[1].text = content['meta'].get('subtitle', '')

        for slide_data in content['slides']:
            if slide_data.get('type') == 'title':
                continue
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = slide_data.get('title', 'Slide')
            if 'subtitle' in slide_data:
                paragraph = slide.shapes.title.text_frame.add_paragraph()
                paragraph.text = slide_data['subtitle']
                paragraph.level = 1
            render_blocks(slide, slide_data.get('blocks', []))
            if 'notes' in slide_data:
                slide.notes_slide.notes_text_frame.text = slide_data['notes']

        output = io.BytesIO()
        prs.save(output)
        file_data = output.getvalue()

        generation.status = 'success'
        generation.file_size = len(file_data)
        generation.generation_time = time.time() - start_time
        download_token = None
        if persist_download:
            download_token = uuid.uuid4().hex
            db.session.add(GeneratedFile(
                token=download_token,
                generation_id=generation.id,
                file_name=output_filename,
                mime_type=PPTX_MIME_TYPE,
                file_data=file_data
            ))
        db.session.commit()

        return {
            'file_data': file_data,
            'file_name': output_filename,
            'generation_id': generation.id,
            'download_token': download_token
        }
    except Exception as error:
        if generation is not None:
            try:
                generation.status = 'failed'
                generation.error_message = str(error)
                generation.generation_time = time.time() - start_time
                db.session.commit()
            except Exception:
                db.session.rollback()
        else:
            db.session.rollback()
        raise


@app.route('/downloads/<string:token>', methods=['GET'])
def download_generated_file(token):
    generated_file = db.session.get(GeneratedFile, token)
    if generated_file is None:
        abort(404)

    response = send_file(
        io.BytesIO(generated_file.file_data),
        as_attachment=True,
        download_name=generated_file.file_name,
        mimetype=generated_file.mime_type
    )
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def _mcp_tool_definition():
    block_schema = {
        'type': 'object',
        'required': ['kind'],
        'properties': {
            'kind': {
                'type': 'string',
                'enum': ['heading', 'paragraph', 'bullets', 'numbered_list', 'table', 'text_box', 'images']
            },
            'text': {'type': 'string'},
            'items': {'type': 'array', 'minItems': 1},
            'rows': {'type': 'array', 'minItems': 1},
            'layout': {'type': 'string', 'enum': ['row', 'column', 'grid']}
        },
        'additionalProperties': True
    }
    return {
        'name': 'generate_ppt',
        'title': 'Generate a PowerPoint presentation',
        'description': (
            'Create a complete PowerPoint from the user request. Every content slide must contain at least one '
            'substantive paragraph, bullet list, table, or other supported content block; never send title-only '
            'slides. If the request includes a university, college, student, course, semester, USN, or professor, '
            'pass those details in academic_details and enable the academic title slide. Use single-student mode '
            'for one presenter; use group mode only when multiple presenters or a group project are explicitly requested. '
            'If the user asks for N total slides and an academic cover is enabled, create N-1 content slides so the final deck has N slides. '
            'Returns a direct download link and stores the usual generation analytics.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'file_name': {
                    'type': 'string',
                    'description': 'Download filename without the .pptx extension.',
                    'default': 'presentation'
                },
                'presentation': {
                    'type': 'object',
                    'description': 'Presentation document. Give every content slide substantive body content in blocks; a title alone is not a complete slide.',
                    'required': ['meta', 'slides'],
                    'properties': {
                        'meta': {'type': 'object', 'additionalProperties': True},
                        'slides': {
                            'type': 'array',
                            'minItems': 1,
                            'items': {
                                'type': 'object',
                                'required': ['title', 'blocks'],
                                'properties': {
                                    'type': {'type': 'string', 'enum': ['content']},
                                    'title': {'type': 'string', 'minLength': 1},
                                    'subtitle': {'type': 'string'},
                                    'blocks': {'type': 'array', 'minItems': 1, 'items': block_schema},
                                    'notes': {'type': 'string'}
                                },
                                'additionalProperties': True
                            }
                        }
                    },
                    'additionalProperties': True
                },
                'academic_details': {
                    'type': 'object',
                    'description': (
                        'Use when the user mentions academic details. Set enabled=true and include the college, '
                        'student name, USN, course, semester, and professor that were provided. Set type=single '
                        'for one presenter (the default); set type=group only for multiple presenters or an explicitly requested group project.'
                    ),
                    'properties': {
                        'enabled': {'type': 'boolean', 'description': 'True when an academic title slide was requested or academic details were provided.'},
                        'type': {'type': 'string', 'enum': ['single', 'group'], 'description': 'Use single unless a group project or multiple presenters were explicitly requested.'},
                        'college_name': {'type': 'string'},
                        'title': {'type': 'string', 'description': 'Presentation title shown on the academic title slide.'},
                        'student_name': {'type': 'string'},
                        'usn': {'type': 'string'},
                        'course': {'type': 'string'},
                        'semester': {'type': 'string'},
                        'professor': {'type': 'string'},
                        'students': {
                            'type': 'array',
                            'items': {
                                'type': 'object',
                                'properties': {'name': {'type': 'string'}, 'usn': {'type': 'string'}},
                                'additionalProperties': False
                            }
                        }
                    },
                    'additionalProperties': True
                },
                'jain_data': {
                    'type': 'object',
                    'description': 'Backward-compatible alias for academic_details.',
                    'additionalProperties': True
                }
            },
            'required': ['presentation'],
            'additionalProperties': False
        }
    }


def _mcp_jsonrpc_error(request_id, code, message, http_status=200, data=None):
    error = {'code': code, 'message': message}
    if data is not None:
        error['data'] = data
    return jsonify({'jsonrpc': '2.0', 'id': request_id, 'error': error}), http_status


def _mcp_jsonrpc_result(request_id, result, modern=False):
    if modern:
        result['_meta'] = {'io.modelcontextprotocol/serverInfo': {'name': 'ppt-generator', 'version': '1.0.0'}}
    return jsonify({'jsonrpc': '2.0', 'id': request_id, 'result': result})


def _decode_mcp_header_value(value):
    if value and value.startswith('=?base64?') and value.endswith('?='):
        import base64
        return base64.b64decode(value[9:-2], validate=True).decode('utf-8')
    return value


def _normalize_academic_details(arguments, presentation):
    details = arguments.get('academic_details')
    if details is None:
        details = arguments.get('jain_data')
    academic_details_were_provided = details is not None

    meta = presentation.get('meta', {})
    if not isinstance(meta, dict):
        meta = {}
    has_academic_metadata = any(meta.get(field) for field in (
        'college_name', 'institution', 'university', 'student_name', 'usn', 'course',
        'semester', 'professor', 'professor_name', 'submitted_to', 'students'
    ))
    if details is None:
        details = {}
    if not isinstance(details, dict):
        raise ValueError('academic_details must be an object.')

    details = dict(details)
    student = details.get('student')
    if isinstance(student, dict):
        details['student_name'] = details.get('student_name') or student.get('name', '')
        details['usn'] = details.get('usn') or student.get('usn', '')
    details['college_name'] = (
        details.get('college_name') or details.get('university') or details.get('institution') or
        meta.get('college_name') or meta.get('institution') or meta.get('university') or ''
    )
    details['student_name'] = (
        details.get('student_name') or details.get('presenter') or details.get('author') or
        meta.get('student_name') or meta.get('presenter') or
        (meta.get('author') if academic_details_were_provided or has_academic_metadata else '') or ''
    )
    details['usn'] = details.get('usn') or meta.get('usn') or ''
    details['course'] = details.get('course') or meta.get('course') or ''
    details['semester'] = details.get('semester') or meta.get('semester') or ''
    details['professor'] = (
        details.get('professor') or details.get('professor_name') or details.get('submitted_to') or
        meta.get('professor') or meta.get('professor_name') or meta.get('submitted_to') or ''
    )
    if not details.get('students') and isinstance(meta.get('students'), list):
        details['students'] = meta['students']
    details['title'] = details.get('title') or meta.get('title', '')

    enabled = details.get('enabled')
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() in {'true', '1', 'yes', 'on'}
    elif enabled is None:
        enabled = any(details.get(field) for field in (
            'college_name', 'student_name', 'usn', 'course', 'semester', 'professor', 'students'
        ))
    details['enabled'] = bool(enabled)
    if not details['enabled']:
        return details

    students = details.get('students') or []
    if not isinstance(students, list):
        raise ValueError('academic_details.students must be an array.')
    requested_type = details.get('type') or details.get('student_type')
    if requested_type is None:
        requested_type = 'group' if len(students) > 1 else 'single'
    requested_type = str(requested_type).lower()
    if requested_type not in {'single', 'group'}:
        raise ValueError('academic_details.type must be single or group.')
    details['type'] = requested_type
    return details


class PresentationValidationError(ValueError):
    """Raised when presentation input would create incomplete or empty slides."""


def _normalize_presentation_slides(presentation):
    """Accept common slide-body aliases, then reject slides that would render blank."""
    supported_kinds = {
        'heading', 'paragraph', 'bullets', 'numbered_list', 'table', 'text_box', 'images'
    }
    aliases = {
        'text': 'paragraph',
        'bullet_list': 'bullets',
        'bullet_points': 'bullets',
        'list': 'bullets'
    }

    def has_text(value):
        if isinstance(value, dict):
            return bool(str(value.get('text', '')).strip())
        return bool(str(value or '').strip())

    def block_has_content(block):
        kind = block.get('kind')
        if kind in {'paragraph', 'text_box'}:
            return has_text(block.get('text'))
        if kind in {'bullets', 'numbered_list'}:
            return isinstance(block.get('items'), list) and any(has_text(item) for item in block['items'])
        if kind == 'table':
            return isinstance(block.get('rows'), list) and any(
                has_text(cell) for row in block['rows'] if isinstance(row, list) for cell in row
            )
        if kind == 'images':
            return isinstance(block.get('items'), list) and bool(block['items'])
        return False

    content_slide_count = 0
    for slide_number, slide in enumerate(presentation.get('slides', []), 1):
        if not isinstance(slide, dict):
            raise PresentationValidationError(f'Slide {slide_number} must be an object.')
        if slide.get('type') == 'title':
            continue
        content_slide_count += 1
        if not str(slide.get('title') or '').strip():
            raise PresentationValidationError(f'Slide {slide_number} is missing a title.')

        blocks = slide.get('blocks')
        if not blocks:
            body = slide.get('content') or slide.get('body') or slide.get('text')
            if isinstance(body, str) and body.strip():
                blocks = [{'kind': 'paragraph', 'text': body}]
            elif isinstance(body, list) and body:
                if all(isinstance(item, str) for item in body):
                    blocks = [{'kind': 'bullets', 'items': body}]
                else:
                    blocks = body
            else:
                points = slide.get('bullet_points') or slide.get('key_points') or slide.get('bullets') or slide.get('points')
                if isinstance(points, list) and points:
                    blocks = [{'kind': 'bullets', 'items': points}]

        if not isinstance(blocks, list):
            raise PresentationValidationError(f'Slide {slide_number} blocks must be an array.')

        normalized_blocks = []
        for block in blocks:
            if isinstance(block, str):
                block = {'kind': 'paragraph', 'text': block}
            if not isinstance(block, dict):
                raise PresentationValidationError(f'Slide {slide_number} contains a content block that is not an object.')
            block = dict(block)
            kind = block.get('kind') or block.get('type')
            if not kind and has_text(block.get('text')):
                kind = 'paragraph'
            kind = aliases.get(str(kind).lower(), str(kind).lower()) if kind else ''
            if kind not in supported_kinds:
                raise PresentationValidationError(f'Slide {slide_number} has unsupported content block kind: {kind or "(missing)"}.')
            block['kind'] = kind
            normalized_blocks.append(block)

        if not any(block_has_content(block) for block in normalized_blocks):
            title = slide.get('title') or f'Slide {slide_number}'
            raise PresentationValidationError(
                f'"{title}" has no visible body content. Add at least one paragraph, bullet list, table, or other supported block; do not submit title-only slides.'
            )
        slide['blocks'] = normalized_blocks

    if not content_slide_count:
        raise PresentationValidationError('Add at least one content slide with a title and body blocks.')


def _validate_mcp_image_paths(content):
    """Only allow MCP-generated decks to embed images from this app's static folder."""
    static_root = os.path.realpath(os.path.join(app.root_path, 'static'))
    for slide_data in content.get('slides', []):
        for block in slide_data.get('blocks', []):
            if block.get('kind') != 'images':
                continue
            for image in block.get('items', []):
                path = image.get('path', '')
                resolved_path = os.path.realpath(os.path.join(app.root_path, path))
                if not path or os.path.commonpath([static_root, resolved_path]) != static_root or not os.path.isfile(resolved_path):
                    raise ValueError('MCP presentations may only use image files that already exist under static/.')


def _build_download_url(token):
    path = url_for('download_generated_file', token=token)
    public_base_url = os.getenv('PUBLIC_BASE_URL', '').strip().rstrip('/')
    if public_base_url:
        from urllib.parse import urlsplit
        parsed = urlsplit(public_base_url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ValueError('PUBLIC_BASE_URL must be an absolute http(s) URL.')
        return f'{public_base_url}{path}'
    request_base_url = request.url_root.rstrip('/')
    return f'{request_base_url}{path}'


@app.route('/mcp', methods=['POST', 'GET', 'DELETE'])
def mcp_endpoint():
    """Stateless Streamable HTTP MCP endpoint for current and 2025 clients."""
    origin = request.headers.get('Origin')
    if origin and not (is_allowed_mcp_origin(origin) or is_allowed_origin(origin)):
        return jsonify({'error': 'Origin not allowed'}), 403
    if request.method != 'POST':
        # The server does not initiate messages, so it has no standalone SSE stream or session to close.
        response = jsonify({'error': 'This stateless MCP endpoint supports POST requests only.'})
        response.status_code = 405
        response.headers['Allow'] = 'POST'
        return response
    message = request.get_json(silent=True)
    if message is None:
        # Some remote MCP clients send valid JSON-RPC with a nonstandard or missing
        # Content-Type. Parse the body so those clients receive a protocol response
        # instead of Flask's unsupported-media-type rejection.
        try:
            message = json.loads(request.get_data(cache=True))
        except (json.JSONDecodeError, UnicodeDecodeError):
            message = None
    if not isinstance(message, dict):
        return _mcp_jsonrpc_error(None, -32600, 'Invalid JSON-RPC request.', 400)

    request_id = message.get('id')
    method = message.get('method')
    params = message.get('params') or {}
    if message.get('jsonrpc') != '2.0' or not isinstance(method, str) or not isinstance(params, dict):
        return _mcp_jsonrpc_error(request_id, -32600, 'Invalid JSON-RPC request.', 400)

    protocol_header = request.headers.get('MCP-Protocol-Version')
    metadata_version = (params.get('_meta') or {}).get('io.modelcontextprotocol/protocolVersion')
    if protocol_header and metadata_version and protocol_header != metadata_version:
        return _mcp_jsonrpc_error(request_id, -32020, 'MCP-Protocol-Version header does not match request metadata.', 400)
    protocol_version = protocol_header or metadata_version or '2025-03-26'
    if protocol_version not in MCP_SUPPORTED_PROTOCOL_VERSIONS:
        return _mcp_jsonrpc_error(
            request_id,
            -32022,
            'Unsupported protocol version.',
            400,
            {'supported': sorted(MCP_MODERN_PROTOCOL_VERSIONS), 'requested': protocol_version}
        )

    modern = protocol_version in MCP_MODERN_PROTOCOL_VERSIONS
    if modern:
        meta = params.get('_meta') or {}
        if not protocol_header or protocol_header != meta.get('io.modelcontextprotocol/protocolVersion'):
            return _mcp_jsonrpc_error(request_id, -32020, 'MCP-Protocol-Version header does not match request metadata.', 400)
        header_method = request.headers.get('Mcp-Method')
        if header_method != method:
            return _mcp_jsonrpc_error(request_id, -32020, 'Mcp-Method header does not match request method.', 400)
        if method == 'tools/call':
            header_name = request.headers.get('Mcp-Name')
            try:
                header_name = _decode_mcp_header_value(header_name)
            except (ValueError, UnicodeDecodeError):
                return _mcp_jsonrpc_error(request_id, -32020, 'Invalid Mcp-Name header value.', 400)
            if header_name != params.get('name'):
                return _mcp_jsonrpc_error(request_id, -32020, 'Mcp-Name header does not match tool name.', 400)
    # Notifications do not have an id and receive an empty 202 response.
    if 'id' not in message:
        if method.startswith('notifications/'):
            return Response(status=202)
        return Response(status=202)

    if method == 'server/discover' and modern:
        return _mcp_jsonrpc_result(request_id, {
            'resultType': 'complete',
            'supportedVersions': sorted(MCP_MODERN_PROTOCOL_VERSIONS),
            'capabilities': {'tools': {}},
            'instructions': (
                'For every requested content slide, supply at least one substantive paragraph, bullet list, table, '
                'or other supported block; do not create title-only slides. If the user provides college or student '
                'details, pass them as academic_details with enabled=true and type=single unless a group is explicitly requested.'
            )
        }, modern=True)
    if method == 'initialize' and not modern:
        requested_version = params.get('protocolVersion')
        negotiated_version = requested_version if requested_version in MCP_LEGACY_PROTOCOL_VERSIONS else MCP_LATEST_LEGACY_PROTOCOL_VERSION
        return jsonify({
            'jsonrpc': '2.0',
            'id': request_id,
            'result': {
                'protocolVersion': negotiated_version,
                'capabilities': {'tools': {'listChanged': False}},
                'serverInfo': {'name': 'ppt-generator', 'version': '1.0.0'},
                'instructions': (
                    'For every requested content slide, supply at least one substantive paragraph, bullet list, table, '
                    'or other supported block; do not create title-only slides. If the user provides college or student '
                    'details, pass them as academic_details with enabled=true and type=single unless a group is explicitly requested.'
                )
            }
        })
    if method == 'ping':
        return _mcp_jsonrpc_result(request_id, {}, modern=modern)
    if method == 'tools/list':
        return _mcp_jsonrpc_result(request_id, {'tools': [_mcp_tool_definition()]}, modern=modern)
    if method == 'tools/call':
        if params.get('name') != 'generate_ppt':
            return _mcp_jsonrpc_error(request_id, -32602, 'Unknown tool name.')
        arguments = params.get('arguments') or {}
        if not isinstance(arguments, dict):
            return _mcp_jsonrpc_error(request_id, -32602, 'Tool arguments must be an object.')
        presentation = arguments.get('presentation')
        if presentation is None and isinstance(arguments.get('json_data'), str):
            try:
                presentation = json.loads(arguments['json_data'])
            except json.JSONDecodeError as error:
                return jsonify({
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': {'isError': True, 'content': [{'type': 'text', 'text': f'Invalid presentation JSON: {error}'}]}
                })
        if not isinstance(presentation, dict) or not isinstance(presentation.get('meta'), dict) or not isinstance(presentation.get('slides'), list):
            return jsonify({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {'isError': True, 'content': [{'type': 'text', 'text': 'presentation must be an object with a meta object and slides array.'}]}
            })
        try:
            academic_details = _normalize_academic_details(arguments, presentation)
            _validate_mcp_image_paths(presentation)
            # Validate the public URL configuration before committing a generated file.
            _build_download_url('download-url-validation')
            generated = _generate_presentation(
                presentation,
                arguments.get('file_name', 'presentation'),
                academic_details,
                persist_download=True
            )
            download_url = _build_download_url(generated['download_token'])
            result = {
                'generation_id': generated['generation_id'],
                'file_name': generated['file_name'],
                'download_url': download_url,
                'download_markdown': f"[Download {generated['file_name']}]({download_url})",
                'academic_title_slide': bool(academic_details and academic_details.get('enabled')),
                'student_type': academic_details.get('type') if academic_details and academic_details.get('enabled') else None
            }
            return _mcp_jsonrpc_result(request_id, {
                'content': [
                    {'type': 'text', 'text': f"PowerPoint generated and saved.\n\n{result['download_markdown']}"},
                    {
                        'type': 'resource_link',
                        'uri': download_url,
                        'name': generated['file_name'],
                        'mimeType': PPTX_MIME_TYPE,
                        'description': 'Download the generated PowerPoint presentation.'
                    }
                ],
                'structuredContent': result,
                'isError': False
            }, modern=modern)
        except Exception as error:
            db.session.rollback()
            return jsonify({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {'isError': True, 'content': [{'type': 'text', 'text': f'Could not generate the PowerPoint: {error}'}]}
            })

    return _mcp_jsonrpc_error(request_id, -32601, f'Method not found: {method}', 404)


# Feedback endpoints
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback (public endpoint, no auth required)"""
    try:
        data = request.get_json()
        
        if not data or not data.get('feedback_text'):
            return jsonify({'error': 'feedback_text is required'}), 400
        
        # Validate rating if provided
        rating = data.get('rating')
        if rating is not None:
            try:
                rating = int(rating)
                if not (1 <= rating <= 5):
                    return jsonify({'error': 'rating must be between 1 and 5'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'rating must be a number'}), 400
        
        # Create feedback record
        feedback = Feedback(
            feedback_text=data.get('feedback_text'),
            rating=rating,
            user_email=data.get('user_email'),
            category=data.get('category'),  # bug, feature, improvement, praise, other
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=request.headers.get('User-Agent', '')[:500]
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!',
            'feedback_id': feedback.id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        print(f"Error saving feedback: {str(e)}")
        return jsonify({'error': 'Failed to save feedback'}), 500


def _serialize_feedback(fb):
    """Serialize feedback object to dict"""
    return {
        'id': fb.id,
        'timestamp': fb.timestamp.isoformat() if fb.timestamp else None,
        'feedback_text': fb.feedback_text,
        'rating': fb.rating,
        'user_email': fb.user_email,
        'category': fb.category,
        'status': fb.status,
        'ip_address': fb.ip_address,
        'user_agent': fb.user_agent
    }


def _build_feedback_query(args):
    """Build filtered query for feedback with similar pattern to generations"""
    query = Feedback.query
    
    # Text filters
    def ilike(col, key):
        val = args.get(key)
        if val:
            return col.ilike(f"%{val}%")
        return None
    
    filters = [
        ilike(Feedback.feedback_text, 'feedback_text'),
        ilike(Feedback.user_email, 'user_email'),
        ilike(Feedback.ip_address, 'ip'),
        ilike(Feedback.user_agent, 'user_agent'),
    ]
    
    # Exact match filters
    category = args.get('category')
    if category:
        filters.append(Feedback.category == category)
    
    status = args.get('status')
    if status:
        filters.append(Feedback.status == status)
    
    # Rating range filter
    min_rating = args.get('min_rating')
    max_rating = args.get('max_rating')
    if min_rating is not None:
        try:
            filters.append(Feedback.rating >= int(min_rating))
        except ValueError:
            pass
    if max_rating is not None:
        try:
            filters.append(Feedback.rating <= int(max_rating))
        except ValueError:
            pass
    
    # Date range filter
    start = args.get('start')
    end = args.get('end')
    if start:
        try:
            filters.append(Feedback.timestamp >= datetime.fromisoformat(start))
        except ValueError:
            pass
    if end:
        try:
            filters.append(Feedback.timestamp <= datetime.fromisoformat(end))
        except ValueError:
            pass
    
    # Global search
    q = args.get('q')
    if q:
        like = f"%{q}%"
        filters.append(or_(
            Feedback.feedback_text.ilike(like),
            Feedback.user_email.ilike(like),
            Feedback.category.ilike(like)
        ))
    
    # Apply filters
    for f in filters:
        if f is not None:
            query = query.filter(f)
    
    # Sorting
    sort_by = args.get('sort_by', 'timestamp')
    sort_dir = args.get('sort_dir', 'desc').lower()
    sort_map = {
        'timestamp': Feedback.timestamp,
        'rating': Feedback.rating,
        'category': Feedback.category,
        'status': Feedback.status
    }
    sort_col = sort_map.get(sort_by, Feedback.timestamp)
    query = query.order_by(sort_col.desc() if sort_dir == 'desc' else sort_col.asc())
    
    return query


@app.route('/api/feedbacks', methods=['GET'])
def api_feedbacks():
    """Get all feedback with filtering options (requires API key)"""
    auth = _require_api_key()
    if auth:
        return auth
    
    limit = min(int(request.args.get('limit', 50)), 200)
    offset = max(int(request.args.get('offset', 0)), 0)
    
    query = _build_feedback_query(request.args)
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    
    return jsonify({
        'total': total,
        'limit': limit,
        'offset': offset,
        'items': [_serialize_feedback(fb) for fb in items]
    })


@app.route('/api/feedbacks/<int:feedback_id>', methods=['GET'])
def api_feedback_detail(feedback_id):
    """Get specific feedback by ID (requires API key)"""
    auth = _require_api_key()
    if auth:
        return auth
    
    feedback = Feedback.query.get_or_404(feedback_id)
    return jsonify(_serialize_feedback(feedback))


@app.route('/api/feedbacks/<int:feedback_id>', methods=['PATCH'])
def api_feedback_update(feedback_id):
    """Update feedback status/category (requires API key)"""
    auth = _require_api_key()
    if auth:
        return auth
    
    feedback = Feedback.query.get_or_404(feedback_id)
    data = request.get_json()
    
    # Only allow updating status and category
    if 'status' in data:
        allowed_statuses = ['new', 'reviewed', 'resolved', 'archived']
        if data['status'] in allowed_statuses:
            feedback.status = data['status']
    
    if 'category' in data:
        feedback.category = data['category']
    
    db.session.commit()
    return jsonify(_serialize_feedback(feedback))


@app.route('/api/feedbacks/export', methods=['GET'])
def api_feedbacks_export():
    """Export feedback data as CSV or JSON (requires API key)"""
    auth = _require_api_key()
    if auth:
        return auth
    
    export_format = request.args.get('format', 'csv').lower()
    limit = min(int(request.args.get('limit', 5000)), 10000)
    offset = max(int(request.args.get('offset', 0)), 0)
    
    query = _build_feedback_query(request.args)
    items = query.offset(offset).limit(limit).all()
    
    if export_format == 'json':
        return jsonify({
            'count': len(items),
            'limit': limit,
            'offset': offset,
            'items': [_serialize_feedback(fb) for fb in items]
        })
    
    if export_format != 'csv':
        return jsonify({'error': 'Invalid format. Use csv or json.'}), 400
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    headers = ['id', 'timestamp', 'feedback_text', 'rating', 'user_email', 
               'category', 'status', 'ip_address', 'user_agent']
    writer.writerow(headers)
    
    for fb in items:
        row = [
            fb.id,
            fb.timestamp.isoformat() if fb.timestamp else '',
            fb.feedback_text or '',
            fb.rating or '',
            fb.user_email or '',
            fb.category or '',
            fb.status or '',
            fb.ip_address or '',
            fb.user_agent or ''
        ]
        writer.writerow(row)
    
    csv_data = output.getvalue()
    output.close()
    
    filename = f"feedback_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


if __name__ == '__main__':
    # Development server only
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)
