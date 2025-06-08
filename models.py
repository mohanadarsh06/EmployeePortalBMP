from app import db
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class Employee(UserMixin, db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic Employee Information
    employment_type = db.Column(db.String(50))
    billable_status = db.Column(db.String(50))
    employee_status = db.Column(db.String(50))
    system_id = db.Column(db.String(50))
    bensl_id = db.Column(db.String(50))
    full_name = db.Column(db.String(200))
    role = db.Column(db.String(100))
    skill = db.Column(db.Text)
    team = db.Column(db.String(100))
    manager_name = db.Column(db.String(200))
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    critical = db.Column(db.String(20))
    
    # Date Information
    doj_allianz = db.Column(db.Date)  # Date of Joining Allianz
    dol_allianz = db.Column(db.Date)  # Date of Leaving Allianz
    doj_project = db.Column(db.Date)  # Date of Joining Project
    dol_project = db.Column(db.Date)  # Date of Leaving Project
    
    # Additional Details
    grade = db.Column(db.String(50))
    designation = db.Column(db.String(100))
    gender = db.Column(db.String(20))
    company = db.Column(db.String(100))
    emailid = db.Column(db.String(200))
    location = db.Column(db.String(100))
    billing_rate = db.Column(db.Float)
    rate_card = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    
    # Authentication (keeping minimal for login functionality)
    password_hash = db.Column(db.String(256))
    is_manager = db.Column(db.Boolean, default=False)
    
    # Relationships
    manager = db.relationship('Employee', remote_side=[id], backref='direct_reports')
    feedback_given = db.relationship('Feedback', foreign_keys='Feedback.manager_id', backref='given_by')
    feedback_received = db.relationship('Feedback', foreign_keys='Feedback.employee_id', backref='received_by')
    billing_records = db.relationship('BillingDetail', backref='employee')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_all_subordinates(self):
        """Get all employees under this manager's hierarchy"""
        subordinates = []
        direct_reports = self.direct_reports
        for report in direct_reports:
            subordinates.append(report)
            subordinates.extend(report.get_all_subordinates())
        return subordinates
    
    def can_manage(self, employee):
        """Check if this employee can manage another employee"""
        if not self.is_manager:
            return False
        subordinates = self.get_all_subordinates()
        return employee in subordinates
    
    def to_dict(self):
        return {
            'id': self.id,
            'employment_type': self.employment_type,
            'billable_status': self.billable_status,
            'employee_status': self.employee_status,
            'system_id': self.system_id,
            'bensl_id': self.bensl_id,
            'full_name': self.full_name,
            'role': self.role,
            'skill': self.skill,
            'team': self.team,
            'manager_name': self.manager_name,
            'manager_id': self.manager_id,
            'critical': self.critical,
            'doj_allianz': self.doj_allianz.isoformat() if self.doj_allianz else None,
            'dol_allianz': self.dol_allianz.isoformat() if self.dol_allianz else None,
            'doj_project': self.doj_project.isoformat() if self.doj_project else None,
            'dol_project': self.dol_project.isoformat() if self.dol_project else None,
            'grade': self.grade,
            'designation': self.designation,
            'gender': self.gender,
            'company': self.company,
            'emailid': self.emailid,
            'location': self.location,
            'billing_rate': self.billing_rate,
            'rate_card': self.rate_card,
            'remarks': self.remarks,
            'is_manager': self.is_manager
        }

class Feedback(db.Model):
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Feedback Period
    feedback_type = db.Column(db.String(20), nullable=False)  # Monthly/Quarterly
    period_year = db.Column(db.Integer, nullable=False)
    period_month = db.Column(db.Integer)  # For monthly feedback
    period_quarter = db.Column(db.Integer)  # For quarterly feedback
    
    # Feedback Content
    performance_rating = db.Column(db.Integer)  # 1-5 scale
    goals_achieved = db.Column(db.Text)
    areas_of_improvement = db.Column(db.Text)
    strengths = db.Column(db.Text)
    comments = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_name': self.received_by.name,
            'manager_name': self.given_by.name,
            'feedback_type': self.feedback_type,
            'period_year': self.period_year,
            'period_month': self.period_month,
            'period_quarter': self.period_quarter,
            'performance_rating': self.performance_rating,
            'goals_achieved': self.goals_achieved,
            'areas_of_improvement': self.areas_of_improvement,
            'strengths': self.strengths,
            'comments': self.comments,
            'created_at': self.created_at.isoformat()
        }

class BillingDetail(db.Model):
    __tablename__ = 'billing_details'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    
    # Billing Information
    billing_rate = db.Column(db.Float)
    currency = db.Column(db.String(10), default='USD')
    project_name = db.Column(db.String(200))
    client_name = db.Column(db.String(200))
    
    # Time Period
    billing_month = db.Column(db.Integer, nullable=False)
    billing_year = db.Column(db.Integer, nullable=False)
    
    # Hours and Amount
    billable_hours = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    
    # Status
    billing_status = db.Column(db.String(20), default='Draft')  # Draft/Submitted/Approved/Paid
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'employee_name': self.employee.name,
            'billing_rate': self.billing_rate,
            'currency': self.currency,
            'project_name': self.project_name,
            'client_name': self.client_name,
            'billing_month': self.billing_month,
            'billing_year': self.billing_year,
            'billable_hours': self.billable_hours,
            'total_amount': self.total_amount,
            'billing_status': self.billing_status
        }
