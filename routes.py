import os
import json
from datetime import datetime, date
from flask import render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import app, db
from models import Employee, Feedback, BillingDetail
from utils import process_excel_file, get_dashboard_analytics, allowed_file

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emailid = request.form['email']
        password = request.form['password']
        
        employee = Employee.query.filter_by(emailid=emailid).first()
        
        if employee and employee.check_password(password):
            login_user(employee)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get analytics data for current user's scope
    if current_user.is_manager:
        subordinates = current_user.get_all_subordinates()
        employees_in_scope = subordinates + [current_user]
    else:
        employees_in_scope = [current_user]
    
    analytics = get_dashboard_analytics(employees_in_scope)
    
    # Get recent feedback
    recent_feedback = []
    if current_user.is_manager:
        recent_feedback = Feedback.query.filter_by(manager_id=current_user.id)\
                                      .order_by(Feedback.created_at.desc())\
                                      .limit(5).all()
    
    return render_template('dashboard.html', 
                         analytics=analytics, 
                         recent_feedback=recent_feedback)

@app.route('/employees')
@login_required
def employees():
    if not current_user.is_manager:
        flash('Access denied. Only managers can view employee lists.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get employees under current manager
    subordinates = current_user.get_all_subordinates()
    
    return render_template('employees.html', employees=subordinates)

@app.route('/employee/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if not current_user.is_manager:
        flash('Access denied. Only managers can add employees.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            employee = Employee(
                employment_type=request.form.get('employment_type'),
                billable_status=request.form.get('billable_status'),
                employee_status=request.form.get('employee_status'),
                system_id=request.form.get('system_id'),
                bensl_id=request.form.get('bensl_id'),
                full_name=request.form.get('full_name'),
                role=request.form.get('role'),
                skill=request.form.get('skill'),
                team=request.form.get('team'),
                manager_name=request.form.get('manager_name'),
                manager_id=current_user.id,
                critical=request.form.get('critical'),
                grade=request.form.get('grade'),
                designation=request.form.get('designation'),
                gender=request.form.get('gender'),
                company=request.form.get('company'),
                emailid=request.form.get('emailid'),
                location=request.form.get('location'),
                billing_rate=float(request.form['billing_rate']) if request.form.get('billing_rate') else None,
                rate_card=request.form.get('rate_card'),
                remarks=request.form.get('remarks'),
                is_manager=request.form.get('is_manager') == 'on'
            )
            
            # Handle date fields
            if request.form.get('doj_allianz'):
                employee.doj_allianz = datetime.strptime(request.form['doj_allianz'], '%Y-%m-%d').date()
            if request.form.get('dol_allianz'):
                employee.dol_allianz = datetime.strptime(request.form['dol_allianz'], '%Y-%m-%d').date()
            if request.form.get('doj_project'):
                employee.doj_project = datetime.strptime(request.form['doj_project'], '%Y-%m-%d').date()
            if request.form.get('dol_project'):
                employee.dol_project = datetime.strptime(request.form['dol_project'], '%Y-%m-%d').date()
            
            # Set default password (employee should change it)
            employee.set_password('password123')
            
            db.session.add(employee)
            db.session.commit()
            
            flash('Employee added successfully!', 'success')
            return redirect(url_for('employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding employee: {str(e)}', 'error')
    
    return render_template('employee_form.html', employee=None, action='Add')

@app.route('/employee/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    
    if not current_user.can_manage(employee) and current_user.id != employee.id:
        flash('Access denied. You can only edit employees under your management.', 'error')
        return redirect(url_for('employees'))
    
    if request.method == 'POST':
        try:
            employee.employment_type = request.form.get('employment_type')
            employee.billable_status = request.form.get('billable_status')
            employee.employee_status = request.form.get('employee_status')
            employee.system_id = request.form.get('system_id')
            employee.bensl_id = request.form.get('bensl_id')
            employee.full_name = request.form.get('full_name')
            employee.role = request.form.get('role')
            employee.skill = request.form.get('skill')
            employee.team = request.form.get('team')
            employee.manager_name = request.form.get('manager_name')
            employee.critical = request.form.get('critical')
            employee.grade = request.form.get('grade')
            employee.designation = request.form.get('designation')
            employee.gender = request.form.get('gender')
            employee.company = request.form.get('company')
            employee.emailid = request.form.get('emailid')
            employee.location = request.form.get('location')
            employee.billing_rate = float(request.form['billing_rate']) if request.form.get('billing_rate') else None
            employee.rate_card = request.form.get('rate_card')
            employee.remarks = request.form.get('remarks')
            
            # Handle date fields
            if request.form.get('doj_allianz'):
                employee.doj_allianz = datetime.strptime(request.form['doj_allianz'], '%Y-%m-%d').date()
            if request.form.get('dol_allianz'):
                employee.dol_allianz = datetime.strptime(request.form['dol_allianz'], '%Y-%m-%d').date()
            if request.form.get('doj_project'):
                employee.doj_project = datetime.strptime(request.form['doj_project'], '%Y-%m-%d').date()
            if request.form.get('dol_project'):
                employee.dol_project = datetime.strptime(request.form['dol_project'], '%Y-%m-%d').date()
            
            if current_user.is_manager:
                employee.is_manager = request.form.get('is_manager') == 'on'
            
            db.session.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('employees'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating employee: {str(e)}', 'error')
    
    return render_template('employee_form.html', employee=employee, action='Edit')

@app.route('/employee/<int:id>')
@login_required
def employee_details(id):
    employee = Employee.query.get_or_404(id)
    
    # Check if user can view this employee
    if not current_user.is_manager and current_user.id != employee.id:
        if not current_user.can_manage(employee):
            flash('Access denied. You can only view employees under your management.', 'error')
            return redirect(url_for('employees'))
    
    return render_template('employee_details.html', employee=employee)

@app.route('/employee/delete/<int:id>', methods=['POST'])
@login_required
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    
    if not (current_user.can_manage(employee) or employee.manager_id == current_user.id):
        flash('Access denied. You can only delete employees under your management.', 'error')
        return redirect(url_for('employees'))
    
    try:
        db.session.delete(employee)
        db.session.commit()
        flash('Employee deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting employee: {str(e)}', 'error')
    
    return redirect(url_for('employees'))

@app.route('/feedback')
@login_required
def feedback():
    if not current_user.is_manager:
        flash('Access denied. Only managers can manage feedback.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get feedback given by current manager
    feedback_list = Feedback.query.filter_by(manager_id=current_user.id)\
                                 .order_by(Feedback.created_at.desc()).all()
    
    return render_template('feedback.html', feedback_list=feedback_list)

@app.route('/feedback/add', methods=['GET', 'POST'])
@login_required
def add_feedback():
    if not current_user.is_manager:
        flash('Access denied. Only managers can give feedback.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            feedback = Feedback(
                employee_id=int(request.form['employee_id']),
                manager_id=current_user.id,
                feedback_type=request.form['feedback_type'],
                period_year=int(request.form['period_year']),
                performance_rating=int(request.form['performance_rating']) if request.form['performance_rating'] else None,
                goals_achieved=request.form['goals_achieved'],
                areas_of_improvement=request.form['areas_of_improvement'],
                strengths=request.form['strengths'],
                comments=request.form['comments']
            )
            
            if request.form['feedback_type'] == 'Monthly':
                feedback.period_month = int(request.form['period_month'])
            else:
                feedback.period_quarter = int(request.form['period_quarter'])
            
            # Verify employee is under current manager
            employee = Employee.query.get(feedback.employee_id)
            if not current_user.can_manage(employee):
                flash('Access denied. You can only give feedback to your direct reports.', 'error')
                return redirect(url_for('feedback'))
            
            db.session.add(feedback)
            db.session.commit()
            
            flash('Feedback added successfully!', 'success')
            return redirect(url_for('feedback'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding feedback: {str(e)}', 'error')
    
    # Get direct reports for dropdown
    direct_reports = current_user.direct_reports
    return render_template('feedback_form.html', feedback=None, employees=direct_reports, action='Add')

@app.route('/feedback/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_feedback(id):
    feedback = Feedback.query.get_or_404(id)
    
    if feedback.manager_id != current_user.id:
        flash('Access denied. You can only edit your own feedback.', 'error')
        return redirect(url_for('feedback'))
    
    if request.method == 'POST':
        try:
            feedback.feedback_type = request.form['feedback_type']
            feedback.period_year = int(request.form['period_year'])
            feedback.performance_rating = int(request.form['performance_rating']) if request.form['performance_rating'] else None
            feedback.goals_achieved = request.form['goals_achieved']
            feedback.areas_of_improvement = request.form['areas_of_improvement']
            feedback.strengths = request.form['strengths']
            feedback.comments = request.form['comments']
            
            if request.form['feedback_type'] == 'Monthly':
                feedback.period_month = int(request.form['period_month'])
                feedback.period_quarter = None
            else:
                feedback.period_quarter = int(request.form['period_quarter'])
                feedback.period_month = None
            
            db.session.commit()
            flash('Feedback updated successfully!', 'success')
            return redirect(url_for('feedback'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating feedback: {str(e)}', 'error')
    
    direct_reports = current_user.direct_reports
    return render_template('feedback_form.html', feedback=feedback, employees=direct_reports, action='Edit')

@app.route('/billing')
@login_required
def billing():
    if not current_user.is_manager:
        flash('Access denied. Only managers can view billing details.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get billing details for employees under current manager
    subordinate_ids = [emp.id for emp in current_user.get_all_subordinates()]
    subordinate_ids.append(current_user.id)
    
    billing_records = BillingDetail.query.filter(BillingDetail.employee_id.in_(subordinate_ids))\
                                        .order_by(BillingDetail.billing_year.desc(), 
                                                BillingDetail.billing_month.desc()).all()
    
    return render_template('billing.html', billing_records=billing_records)

@app.route('/hierarchy')
@login_required
def hierarchy():
    # Get all employees and build hierarchy tree
    all_employees = Employee.query.all()
    
    # Build a mapping of managers to their direct reports
    manager_reports = {}
    employee_dict = {emp.id: emp for emp in all_employees}
    
    # Initialize direct_reports list for each employee
    for emp in all_employees:
        emp.direct_reports = []
    
    # Build the hierarchy relationships
    top_managers = []
    for emp in all_employees:
        if emp.manager_id is None:
            # This is a top-level employee/manager
            top_managers.append(emp)
        else:
            # This employee has a manager
            manager = employee_dict.get(emp.manager_id)
            if manager:
                manager.direct_reports.append(emp)
    
    # Sort direct reports by name for each manager
    for emp in all_employees:
        emp.direct_reports.sort(key=lambda x: x.full_name or '')
    
    # Sort top managers by name
    top_managers.sort(key=lambda x: x.full_name or '')
    
    # If user is not a top manager and not viewing all, show only their hierarchy
    if current_user.manager_id is not None and not current_user.is_manager:
        # Find the root manager for current user
        root_manager = current_user
        while root_manager.manager_id is not None:
            parent = employee_dict.get(root_manager.manager_id)
            if parent:
                root_manager = parent
            else:
                break
        top_managers = [root_manager] if root_manager else [current_user]
    
    return render_template('hierarchy.html', top_managers=top_managers)

@app.route('/import_excel', methods=['GET', 'POST'])
@login_required
def import_excel():
    if not current_user.is_manager:
        flash('Access denied. Only managers can import employee data.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                result = process_excel_file(file, current_user.id)
                
                if result['success']:
                    success_msg = f'Successfully imported {result["count"]} employees'
                    if result['skipped'] > 0:
                        success_msg += f' (skipped {result["skipped"]} duplicates)'
                    
                    flash(success_msg, 'success')
                    
                    # Show errors if any
                    if result['errors']:
                        error_summary = f"Import completed with {len(result['errors'])} warnings/errors. "
                        error_summary += "Check the details below."
                        flash(error_summary, 'warning')
                        
                        # Store detailed errors in session for display
                        session = request.environ.get('werkzeug.session') 
                        if session:
                            session['import_errors'] = result['errors'][:20]  # Limit to 20 errors
                    
                    return redirect(url_for('employees'))
                else:
                    error_msg = f'Import failed: {result["error"]}'
                    if result['errors']:
                        error_msg += f' Additional errors: {len(result["errors"])} rows had issues.'
                    flash(error_msg, 'error')
                    
            except Exception as e:
                flash(f'Error processing file: {str(e)}', 'error')
        else:
            flash('Invalid file type. Please upload an Excel file (.xlsx or .xls)', 'error')
    
    return render_template('import_excel.html')

# API endpoints for charts
@app.route('/api/dashboard_data')
@login_required
def dashboard_data():
    if current_user.is_manager:
        subordinates = current_user.get_all_subordinates()
        employees_in_scope = subordinates + [current_user]
    else:
        employees_in_scope = [current_user]
    
    analytics = get_dashboard_analytics(employees_in_scope)
    return jsonify(analytics)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
# API endpoint to get import results
@app.route('/api/import_results')
@login_required 
def import_results():
    session = request.environ.get('werkzeug.session')
    if session and 'import_errors' in session:
        errors = session.pop('import_errors', [])
        return jsonify({'errors': errors})
    return jsonify({'errors': []})

@app.route('/api/employee/<int:id>')
@login_required
def api_employee_details(id):
    employee = Employee.query.get_or_404(id)
    
    # Check if user can view this employee
    if not current_user.is_manager and current_user.id != employee.id:
        if not current_user.can_manage(employee):
            return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(employee.to_dict())
@app.route('/download_template')
@login_required
def download_template():
    if not current_user.is_manager:
        flash('Access denied. Only managers can download templates.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Create sample data matching database schema
        sample_data = [
            {
                'Employment_Type': 'Permanent',
                'Billable_Status': 'Billable',
                'Employee_Status': 'Active',
                'System_ID': 'SYS001',
                'Bensl_ID': 'BENSL001',
                'Full_Name': 'John Doe',
                'Role': 'Software Engineer',
                'Skill': 'Python, JavaScript, SQL',
                'Team': 'UFS',
                'Manager_Name': 'Jane Smith',
                'Manager_ID': '',
                'Critical': 'No',
                'DOJ_Allianz': '2024-01-15',
                'DOL_Allianz': '',
                'Grade': 'L3',
                'Designation': 'Software Engineer',
                'DOJ_Project': '2024-01-20',
                'DOL_Project': '',
                'Gender': 'Male',
                'Company': 'Allianz',
                'Emailid': 'john.doe@company.com',
                'Location': 'Bangalore',
                'Billing_Rate': '50.00',
                'Rate_Card': 'Standard',
                'Remarks': 'Good performer'
            },
            {
                'Employment_Type': 'Permanent',
                'Billable_Status': 'Billable',
                'Employee_Status': 'Active',
                'System_ID': 'SYS002',
                'Bensl_ID': 'BENSL002',
                'Full_Name': 'Jane Smith',
                'Role': 'Senior Developer',
                'Skill': 'Java, React, MongoDB',
                'Team': 'RG',
                'Manager_Name': 'Manager Name',
                'Manager_ID': '',
                'Critical': 'No',
                'DOJ_Allianz': '2023-08-01',
                'DOL_Allianz': '',
                'Grade': 'L4',
                'Designation': 'Senior Developer',
                'DOJ_Project': '2023-08-05',
                'DOL_Project': '',
                'Gender': 'Female',
                'Company': 'Allianz',
                'Emailid': 'jane.smith@company.com',
                'Location': 'Mumbai',
                'Billing_Rate': '75.00',
                'Rate_Card': 'Premium',
                'Remarks': 'Team lead'
            }
        ]
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(sample_data)
        
        # Create Excel file in memory
        from io import BytesIO
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Employees', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Employees']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        return send_file(
            output,
            as_attachment=True,
            download_name='employee_import_template.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        flash(f'Error generating template: {str(e)}', 'error')
        return redirect(url_for('import_excel'))
