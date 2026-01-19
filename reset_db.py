from app import app, db

print("Resetting database...")
with app.app_context():
    # Force drop all tables (Student, Attendance, Timetable)
    db.drop_all()
    print("Tables dropped.")
    
    # Recreate all tables with new schema
    db.create_all()
    print("Tables created.")
    print("Database reset successfully.")
