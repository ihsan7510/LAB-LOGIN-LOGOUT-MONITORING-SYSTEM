from app import app, db
from database import Admin

def create_admin():
    with app.app_context():
        # Ensure tables exist
        db.create_all()
        
        # Check if admin exists
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            print("Creating default admin user...")
            new_admin = Admin(username='admin')
            new_admin.set_password('admin123')
            db.session.add(new_admin)
            db.session.commit()
            print("Admin user created (admin/admin123).")
        else:
            print("Admin user already exists.")

if __name__ == '__main__':
    create_admin()
