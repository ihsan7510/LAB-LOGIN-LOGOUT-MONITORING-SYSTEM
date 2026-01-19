from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    semester = db.Column(db.String(10), nullable=False, default="1") # Added Semantic
    fingerprint_id = db.Column(db.Integer, unique=True, nullable=False)
    
    def __repr__(self):
        return f'<Student {self.name}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), nullable=False) # LOGIN or LOGOUT
    subject = db.Column(db.String(100), nullable=False) # Subject name at time of scan
    
    student = db.relationship('Student', backref=db.backref('attendance_records', lazy=True, cascade="all, delete-orphan"))

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False) # Monday, Tuesday...
    start_time = db.Column(db.String(10), nullable=False) # HH:MM
    end_time = db.Column(db.String(10), nullable=False)   # HH:MM
    subject = db.Column(db.String(100), nullable=False)
    lab_name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(10), nullable=False, default="1")

class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False) # REGISTER, DELETE
    payload = db.Column(db.String(100), nullable=True) # JSON payload or simple ID string
    created_at = db.Column(db.DateTime, default=datetime.now)
