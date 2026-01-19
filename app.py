from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from database import db, Student, Attendance, Timetable, Command
from datetime import datetime, date, timedelta
import os
import calendar
import pandas as pd
import time
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///attendance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from database import db, Student, Attendance, Timetable, Command, Admin
from flask import flash

# ... (Previous imports)

db.init_app(app)
app.secret_key = 'supersecretkey' # Required for sessions

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))


# Global State for Registration/Commands
command_queue = []
registration_status = {'status': 'idle', 'message': '', 'fingerprint_id': None}
lcd_message = "Initializing..."
last_heartbeat_time = 0

@app.context_processor
def inject_device_status():
    is_connected = (time.time() - last_heartbeat_time) < 5
    return dict(is_device_connected=is_connected)

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    global last_heartbeat_time
    last_heartbeat_time = time.time()
    return jsonify({'status': 'ok'})

def get_current_class(student_semester):
    """Checks the timetable for a class currently running for a specific semester."""
    now = datetime.now()
    current_day = calendar.day_name[now.weekday()] # e.g., "Monday"
    current_time = now.strftime("%H:%M") # e.g., "09:30"
    
    # DEBUG LOGGING
    print(f"DEBUG: Current Day={current_day}, Time={current_time}, Sem={student_semester}")
    
    # Find a class where start <= current <= end AND semester matches
    ongoing_class = Timetable.query.filter(
        Timetable.day == current_day,
        Timetable.semester == student_semester,
        Timetable.start_time <= current_time,
        Timetable.end_time >= current_time
    ).first()
    
    if ongoing_class:
        print(f"DEBUG: Found Class: {ongoing_class.subject} ({ongoing_class.start_time}-{ongoing_class.end_time})")
    else:
        print(f"DEBUG: No Class Found for Sem {student_semester}")
        
    return ongoing_class

@app.route('/download_excel')
def download_excel():
    # Query all attendance records joined with Student
    results = db.session.query(
        Student.name, 
        Student.roll_no, 
        Student.semester, 
        Attendance.subject, 
        Attendance.timestamp, 
        Attendance.status
    ).join(Attendance, Student.id == Attendance.student_id).all()
    
    # Create a list of dictionaries
    data = []
    for row in results:
        data.append({
            'Student Name': row.name,
            'Register No': row.roll_no,
            'Semester': row.semester,
            'Subject': row.subject,
            'Date': row.timestamp.strftime('%Y-%m-%d'),
            'Time': row.timestamp.strftime('%H:%M:%S'),            'Status': row.status
        })
        
    df = pd.DataFrame(data)
    
    # Create an in-memory output file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')
        
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'attendance_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )
    
from sqlalchemy import func, or_

def get_active_student_count():
    """Calculates how many students are currently logged in."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    # Subquery: Get the latest timestamp for each student (for today)
    subquery = db.session.query(
        Attendance.student_id,
        func.max(Attendance.timestamp).label('max_time')
    ).filter(Attendance.timestamp >= today_start).group_by(Attendance.student_id).subquery()
    
    # query: Find records that match the latest timestamp and have status 'LOGIN'
    count = db.session.query(Attendance).join(
        subquery,
        (Attendance.student_id == subquery.c.student_id) & 
        (Attendance.timestamp == subquery.c.max_time)
    ).filter(Attendance.status == 'LOGIN').count()
    
    return count

    return count

@app.route('/api/latest_log_id')
def latest_log_id():
    last_log = Attendance.query.order_by(Attendance.id.desc()).first()
    return jsonify({'last_id': last_log.id if last_log else 0})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = Admin.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def landing_page():
    return render_template('landing.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/dashboard')
def public_dashboard():
    # ... (Rest of dashboard logic)
    date_filter = request.args.get('date')
    subject_filter = request.args.get('subject')
    search_query = request.args.get('search')
    
    query = Attendance.query.join(Student)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            date_start = datetime.combine(filter_date, datetime.min.time())
            date_end = datetime.combine(filter_date, datetime.max.time())
            query = query.filter(Attendance.timestamp.between(date_start, date_end))
        except ValueError:
            pass # Ignore invalid dates
            
    if subject_filter:
        query = query.filter(Attendance.subject.ilike(f"%{subject_filter}%"))
        
    if search_query:
        query = query.filter(
            or_(
                Student.name.ilike(f"%{search_query}%"),
                Student.roll_no.ilike(f"%{search_query}%")
            )
        )
    
    # Show recent attendance (limit 50 if no filter, else all)
    if not (date_filter or subject_filter or search_query):
        recent_logs = query.order_by(Attendance.timestamp.desc()).limit(50).all()
        # Get latest ID for polling from the unfiltered recent list (or just the very latest global)
        # Actually safer to always get the absolute latest ID for polling to work regardless of filter
        latest_global = Attendance.query.order_by(Attendance.id.desc()).first()
        last_id = latest_global.id if latest_global else 0
    else:
        recent_logs = query.order_by(Attendance.timestamp.desc()).all()
        # For polling, we still use the global latest arg
        latest_global = Attendance.query.order_by(Attendance.id.desc()).first()
        last_id = latest_global.id if latest_global else 0

    active_count = get_active_student_count()
    
    return render_template('dashboard.html', logs=recent_logs, active_count=active_count, last_id=last_id)

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')

@app.route('/api/daily_stats')
@login_required
def daily_stats():
    # Get last 7 days range
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    
    # Initialize dictionary for last 7 days with 0
    daily_counts = {}
    current_date = start_date
    while current_date <= end_date:
        daily_counts[current_date.strftime('%Y-%m-%d')] = 0
        current_date += timedelta(days=1)
    
    # Query logs from last 7 days
    logs = db.session.query(
        func.date(Attendance.timestamp).label('date'), 
        func.count(Attendance.id).label('count')
    ).filter(
        Attendance.timestamp >= datetime.combine(start_date, datetime.min.time())
    ).group_by('date').all()
    
    # Update counts
    for log in logs:
        # log.date might be a string or date object depending on SQLite/SQLAlchemy version
        # Ensure it matches the key format
        log_date = str(log.date)
        if log_date in daily_counts:
            daily_counts[log_date] = log.count
            
    return jsonify({
        'dates': list(daily_counts.keys()),
        'counts': list(daily_counts.values())
    })

@app.route('/api/semester_stats')
@login_required
def semester_stats():
    # Aggregate attendance counts by semester
    # We join Attendance with Student to filter/group by semester
    stats = db.session.query(
        Student.semester,
        func.count(Attendance.id).label('count')
    ).join(Attendance, Student.id == Attendance.student_id)\
    .group_by(Student.semester).all()
    
    data = {}
    # Ensure we label them nicely
    for row in stats:
        label = f"Semester {row.semester}"
        data[label] = row.count
        
    return jsonify({
        'labels': list(data.keys()),
        'data': list(data.values())
    })

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    if request.method == 'POST':
        name = request.form.get('name')
        roll_no = request.form.get('roll_no')
        semester = request.form.get('semester')
        fingerprint_id = request.form.get('fingerprint_id')
        
        if name and roll_no and fingerprint_id and semester:
            new_student = Student(name=name, roll_no=roll_no, semester=semester, fingerprint_id=int(fingerprint_id))
            try:
                db.session.add(new_student)
                db.session.commit()
            except Exception as e:
                return f"Error: {e}"
            return redirect(url_for('students'))
            
    all_students = Student.query.all()
    return render_template('students.html', students=all_students)

@app.route('/delete_student/<int:id>', methods=['POST'])
@login_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    fingerprint_id = student.fingerprint_id # Get ID before deleting
    
    try:
        db.session.delete(student)
        
        # Queue hardware deletion
        print(f"Queueing deletion for Fingerprint ID {fingerprint_id}")
        cmd = Command(type='DELETE', payload=str(fingerprint_id))
        db.session.add(cmd)
        
        db.session.commit()
        
    except Exception as e:
        return f"Error deleting student: {e}"
    return redirect(url_for('students'))

    return redirect(url_for('students'))

@app.route('/edit_student/<int:id>', methods=['POST'])
@login_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    name = request.form.get('name')
    roll_no = request.form.get('roll_no')
    semester = request.form.get('semester')
    fingerprint_id = request.form.get('fingerprint_id')
    
    # Optional: Logic to handle fingerprint change
    # If fingerprint ID changed, we might need to delete old one or warn user.
    # For now, we assume user knows what they are doing (e.g. they registered a new finger manually)
    
    student.name = name
    student.roll_no = roll_no
    student.semester = semester
    student.fingerprint_id = int(fingerprint_id)
    
    try:
        db.session.commit()
    except Exception as e:
        return f"Error updating student: {e}"
    
    return redirect(url_for('students'))

@app.route('/timetable', methods=['GET', 'POST'])
@login_required
def timetable():
    if request.method == 'POST':
        # Simple form to add timetable entry for testing
        day = request.form.get('day')
        start = request.form.get('start_time')
        end = request.form.get('end_time')
        subject = request.form.get('subject')
        lab = request.form.get('lab_name')
        semester = request.form.get('semester')
        
        entry = Timetable(day=day, start_time=start, end_time=end, subject=subject, lab_name=lab, semester=semester)
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('timetable'))

    semester_filter = request.args.get('semester')
    if semester_filter:
        entries = Timetable.query.filter_by(semester=semester_filter).all()
        # Pass the filter back to template to keep state
    else:
        entries = Timetable.query.all()
        
    return render_template('timetable.html', entries=entries, current_semester=semester_filter)

@app.route('/api/start_registration')
def start_registration():
    global registration_status
    cmd = Command(type='REGISTER', payload=None)
    db.session.add(cmd)
    db.session.commit()
    registration_status = {'status': 'waiting', 'message': 'Request sent to sensor...', 'fingerprint_id': None}
    return jsonify({'status': 'started'})

@app.route('/api/get_command')
def get_command():
    cmd = Command.query.order_by(Command.created_at.asc()).first()
    if cmd:
        data = {'type': cmd.type, 'id': int(cmd.payload) if cmd.payload else None}
        db.session.delete(cmd)
        db.session.commit()
        return jsonify(data)
    return jsonify({'type': None})

@app.route('/api/registration_status')
def get_registration_status():
    return jsonify(registration_status)

@app.route('/api/registration_result', methods=['POST'])
def registration_result():
    global registration_status
    data = request.json
    if data.get('status') == 'success':
        registration_status = {
            'status': 'success', 
            'fingerprint_id': data.get('fingerprint_id')
        }
    else:
        registration_status = {
            'status': 'failed', 
            'message': data.get('message', 'Unknown error')
        }
    return jsonify({'ack': True})

@app.route('/api/lcd_status', methods=['GET', 'POST'])
def lcd_status():
    global lcd_message
    if request.method == 'POST':
        data = request.json
        lcd_message = data.get('message', '')
        return jsonify({'status': 'updated'})
    return jsonify({'message': lcd_message})

@app.route('/api/scan', methods=['POST'])
def api_scan():
    data = request.json
    fingerprint_id = data.get('fingerprint_id')
    
    if fingerprint_id is None:
        return jsonify({'status': 'error', 'message': 'No fingerprint ID provided'}), 400
    
    student = Student.query.filter_by(fingerprint_id=fingerprint_id).first()
    
    if not student:
        return jsonify({'status': 'error', 'message': 'Student not found', 'student_name': 'Unknown'}), 200
        
    # 2. Check for Current Class FOR THIS STUDENT'S SEMESTER
    current_class = get_current_class(student.semester)
    if not current_class:
        return jsonify({
            'status': 'error', 
            'message': 'No Class',
            'student_name': student.name
        }), 200

    # 3. Determine Login/Logout
    # Get last log for this student for THIS subject today
    start_of_day = datetime.combine(date.today(), datetime.min.time())
    
    last_log = Attendance.query.filter(
        Attendance.student_id == student.id,
        Attendance.subject == current_class.subject,
        Attendance.timestamp >= start_of_day
    ).order_by(Attendance.timestamp.desc()).first()
    
    new_status = 'LOGIN'
    if last_log and last_log.status == 'LOGIN':
        new_status = 'LOGOUT'
    
    # 4. Log Attendance
    log = Attendance(
        student_id=student.id, 
        status=new_status, 
        subject=current_class.subject
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'status': 'success', 
        'message': f'{new_status} Success', 
        'student_name': student.name,
        'subject': current_class.subject,
        'scan_type': new_status  # LOGIN or LOGOUT
    })

@app.route('/api/reset_system_data', methods=['POST'])
@login_required
def reset_system_data():
    try:
        # 1. Clear Database Tables
        num_students = db.session.query(Student).delete()
        num_attendance = db.session.query(Attendance).delete()
        num_timetable = db.session.query(Timetable).delete()
        
        # 2. Queue Hardware Reset Command
        # We don't need a payload for EMPTY_DB
        cmd = Command(type='EMPTY_DB')
        db.session.add(cmd)
        
        db.session.commit()
        
        print(f"System Reset: Deleted {num_students} students, {num_attendance} logs, {num_timetable} classes.")
        
        return jsonify({
            'status': 'success', 
            'message': f'System Reset Complete. Deleted {num_students} students, {num_attendance} logs.'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    if not os.path.exists('attendance.db'):
        init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
