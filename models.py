from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import uuid

db = SQLAlchemy()

# Timezone offset for display (IST = UTC+5:30)
IST_OFFSET = timedelta(hours=5, minutes=30)

def to_local_time(utc_time):
    """Convert UTC time to IST"""
    if utc_time:
        return utc_time + IST_OFFSET
    return None

class Generation(db.Model):
    """Track each PPT generation"""
    __tablename__ = 'generations'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # File information
    file_name = db.Column(db.String(255))
    title = db.Column(db.String(500))
    subtitle = db.Column(db.String(500))
    num_slides = db.Column(db.Integer)
    file_size = db.Column(db.Integer)  # in bytes
    
    # College/Academic information (optional)
    college_name = db.Column(db.String(255))
    presentation_title = db.Column(db.String(500))
    student_type = db.Column(db.String(20))  # 'single' or 'group'
    course = db.Column(db.String(100))
    semester = db.Column(db.String(50))
    professor_name = db.Column(db.String(255))
    
    # Technical metadata
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    generation_time = db.Column(db.Float)  # Time taken to generate in seconds
    status = db.Column(db.String(20), default='success')  # success/failed
    error_message = db.Column(db.Text)
    
    # JSON content analysis
    content_summary = db.Column(db.Text)  # Brief summary of topics
    has_tables = db.Column(db.Boolean, default=False)
    has_images = db.Column(db.Boolean, default=False)
    has_charts = db.Column(db.Boolean, default=False)
    
    # Relationships
    students = db.relationship('Student', backref='generation', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Generation {self.id}: {self.title}>'


class Student(db.Model):
    """Track student information for each generation"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    generation_id = db.Column(db.Integer, db.ForeignKey('generations.id'), nullable=False)
    
    name = db.Column(db.String(255), nullable=False)
    usn = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<Student {self.name} ({self.usn})>'


class GeneratedFile(db.Model):
    """Persist generated PowerPoint files so remote clients can download them."""
    __tablename__ = 'generated_files'

    token = db.Column(db.String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    generation_id = db.Column(db.Integer, db.ForeignKey('generations.id'), nullable=False, index=True)
    file_name = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(
        db.String(127),
        nullable=False,
        default='application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )
    file_data = db.Column(db.LargeBinary, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f'<GeneratedFile {self.file_name} for generation {self.generation_id}>'


class Feedback(db.Model):
    """Track user feedback"""
    __tablename__ = 'feedbacks'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Feedback content
    feedback_text = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer)  # Optional 1-5 rating
    user_email = db.Column(db.String(255))  # Optional contact info
    
    # Tech metadata
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    # Categorization
    category = db.Column(db.String(50))  # bug, feature, improvement, praise, other
    status = db.Column(db.String(20), default='new')  # new, reviewed, resolved, archived
    
    def __repr__(self):
        return f'<Feedback {self.id}: {self.category or "uncategorized"}>'


class DailyStats(db.Model):
    """Aggregate daily statistics for quick analytics"""
    __tablename__ = 'daily_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    
    total_generations = db.Column(db.Integer, default=0)
    successful_generations = db.Column(db.Integer, default=0)
    failed_generations = db.Column(db.Integer, default=0)
    total_slides_generated = db.Column(db.Integer, default=0)
    unique_ips = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<DailyStats {self.date}: {self.total_generations} generations>'


def get_analytics_summary():
    """Get comprehensive analytics summary"""
    total_generations = Generation.query.count()
    successful_generations = Generation.query.filter_by(status='success').count()
    failed_generations = Generation.query.filter_by(status='failed').count()
    
    # Total students tracked
    total_students = Student.query.count()
    
    # Average slides per generation
    avg_slides = db.session.query(func.avg(Generation.num_slides)).scalar() or 0
    
    # Most active colleges
    top_colleges = db.session.query(
        Generation.college_name,
        func.count(Generation.id).label('count')
    ).filter(
        Generation.college_name.isnot(None)
    ).group_by(
        Generation.college_name
    ).order_by(
        func.count(Generation.id).desc()
    ).limit(10).all()
    
    # Recent generations
    recent_generations = Generation.query.order_by(
        Generation.timestamp.desc()
    ).limit(10).all()
    
    # Generations by date (last 30 days)
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    daily_counts = db.session.query(
        func.date(Generation.timestamp).label('date'),
        func.count(Generation.id).label('count')
    ).filter(
        Generation.timestamp >= thirty_days_ago
    ).group_by(
        func.date(Generation.timestamp)
    ).order_by('date').all()
    
    return {
        'total_generations': total_generations,
        'successful_generations': successful_generations,
        'failed_generations': failed_generations,
        'success_rate': round((successful_generations / total_generations * 100) if total_generations > 0 else 0, 2),
        'total_students': total_students,
        'avg_slides': round(avg_slides, 2),
        'top_colleges': top_colleges,
        'recent_generations': recent_generations,
        'daily_counts': daily_counts
    }
