# utils.py
import pandas as pd
import json
from datetime import datetime
import re

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_excel_file(file, manager_id):
    """Process uploaded Excel file and create employee records"""
    from app import db
    from models import Employee

    result = {
        'success': False,
        'count': 0,
        'skipped': 0,
        'errors': [],
        'error': None
    }

    try:
        # Read Excel file with multiple sheet support
        try:
            df = pd.read_excel(file, sheet_name=0)  # Read first sheet
        except Exception as e:
            result['error'] = f"Failed to read Excel file: {str(e)}"
            return result

        if df.empty:
            result['error'] = "Excel file is empty"
            return result

        # Normalize column names (remove extra spaces, handle case variations)
        df.columns = df.columns.str.strip()

        # Expected columns matching the database schema
        expected_columns = {
            'Employment_Type': 'employment_type',
            'Billable_Status': 'billable_status', 
            'Employee_Status': 'employee_status',
            'System_ID': 'system_id',
            'Bensl_ID': 'bensl_id',
            'Full_Name': 'full_name',
            'Role': 'role',
            'Skill': 'skill',
            'Team': 'team',
            'Manager_Name': 'manager_name',
            'Manager_ID': 'manager_id',
            'Critical': 'critical',
            'DOJ_Allianz': 'doj_allianz',
            'DOL_Allianz': 'dol_allianz',
            'Grade': 'grade',
            'Designation': 'designation',
            'DOJ_Project': 'doj_project',
            'DOL_Project': 'dol_project',
            'Gender': 'gender',
            'Company': 'company',
            'Emailid': 'emailid',
            'Location': 'location',
            'Billing_Rate': 'billing_rate',
            'Rate_Card': 'rate_card',
            'Remarks': 'remarks'
        }

        # Validate that we have at least one recognizable column
        found_columns = []
        column_mapping = {}

        for excel_col, db_field in expected_columns.items():
            if excel_col in df.columns:
                found_columns.append(excel_col)
                column_mapping[excel_col] = db_field

        if not found_columns:
            result['error'] = f"No recognized columns found. Expected columns: {', '.join(expected_columns.keys())}"
            return result

        # Store employee data for processing
        temp_employees = []

        # Process each row in the Excel file
        for index, row in df.iterrows():
            try:
                # Skip completely empty rows
                if row.isna().all():
                    continue

                # Create employee data dictionary
                employee_data = {}

                # Map Excel columns to database fields
                for excel_col, db_field in column_mapping.items():
                    value = row.get(excel_col)
                    if pd.notna(value):
                        if excel_col in ['Billing_Rate']:
                            # Handle numeric fields
                            try:
                                employee_data[db_field] = float(value)
                            except (ValueError, TypeError):
                                employee_data[db_field] = None
                        elif excel_col in ['DOJ_Allianz', 'DOL_Allianz', 'DOJ_Project', 'DOL_Project']:
                            # Handle date fields
                            try:
                                if isinstance(value, str):
                                    # Try multiple date formats
                                    for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                                        try:
                                            employee_data[db_field] = datetime.strptime(value, date_format).date()
                                            break
                                        except ValueError:
                                            continue
                                    else:
                                        employee_data[db_field] = None
                                else:
                                    employee_data[db_field] = value.date() if hasattr(value, 'date') else None
                            except (ValueError, TypeError):
                                employee_data[db_field] = None
                        else:
                            # Handle text fields
                            employee_data[db_field] = str(value).strip() if value else None
                    else:
                        employee_data[db_field] = None

                # Check if we have enough data to create an employee
                if not employee_data.get('system_id') and not employee_data.get('full_name'):
                    result['errors'].append(f"Row {index + 2}: Missing System ID or Full Name")
                    continue

                # Check if employee already exists (by system_id or emailid)
                existing_employee = None
                if employee_data.get('system_id'):
                    existing_employee = Employee.query.filter_by(system_id=employee_data['system_id']).first()
                elif employee_data.get('emailid'):
                    existing_employee = Employee.query.filter_by(emailid=employee_data['emailid']).first()

                if existing_employee:
                    result['skipped'] += 1
                    result['errors'].append(f"Row {index + 2}: Employee with System ID {employee_data.get('system_id')} already exists")
                    continue

                temp_employees.append(employee_data)

            except Exception as e:
                result['errors'].append(f"Row {index + 2}: Error processing row - {str(e)}")
                continue

        # Second pass: Create employees in database
        for emp_data in temp_employees:
            try:
                employee = Employee()

                # Map all the fields from employee_data to Employee model
                for field, value in emp_data.items():
                    if hasattr(employee, field) and value is not None:
                        setattr(employee, field, value)

                # Set default manager to importing user
                if not employee.manager_id:
                    employee.manager_id = manager_id

                # Set default values for required fields if not provided
                if not employee.employment_type:
                    employee.employment_type = 'Permanent'
                if not employee.billable_status:
                    employee.billable_status = 'Billable'
                if not employee.employee_status:
                    employee.employee_status = 'Active'

                # Set default password
                employee.set_password('password123')

                db.session.add(employee)
                result['count'] += 1

            except Exception as e:
                result['errors'].append(f"Failed to create employee: {str(e)}")
                continue

        db.session.commit()
        result['success'] = True

    except Exception as e:
        db.session.rollback()
        result['error'] = f"Unexpected error: {str(e)}"

    return result

def get_dashboard_analytics(employees):
    """Generate analytics data for dashboard charts"""
    if not employees:
        return {
            'skills': {},
            'employment_type': {},
            'billable_status': {},
            'location': {},
            'team': {},
            'total_employees': 0
        }

    analytics = {
        'skills': {},
        'employment_type': {},
        'billable_status': {},
        'location': {},
        'team': {},
        'total_employees': len(employees)
    }

    for employee in employees:
        # Employment type analytics
        emp_type = employee.employment_type or 'Unknown'
        analytics['employment_type'][emp_type] = analytics['employment_type'].get(emp_type, 0) + 1

        # Billable status analytics
        billable = employee.billable_status or 'Unknown'
        analytics['billable_status'][billable] = analytics['billable_status'].get(billable, 0) + 1

        # Location analytics
        location = employee.location or 'Unknown'
        analytics['location'][location] = analytics['location'].get(location, 0) + 1

        # Team analytics
        team = employee.team or 'Unknown'
        analytics['team'][team] = analytics['team'].get(team, 0) + 1

        # Skills analytics (assuming skills are comma-separated)
        if employee.skill:
            skills_list = [skill.strip() for skill in employee.skill.split(',')]
            for skill in skills_list:
                if skill:
                    analytics['skills'][skill] = analytics['skills'].get(skill, 0) + 1

    return analytics

def create_sample_data():
    """Create sample users if database is empty"""
    try:
        # Import here to avoid circular imports
        from app import db
        from models import Employee
        if Employee.query.first():
            return

        # Create top manager
        top_manager = Employee(
            system_id='SYS001',
            bensl_id='BEN001',
            full_name='Sooraj Kumar',
            emailid='sooraj@company.com',
            designation='VP Engineering',
            role='VP',
            team='Leadership',
            location='Bangalore',
            employment_type='Permanent',
            employee_status='Active',
            billable_status='Non-billable',
            is_manager=True,
            manager_id=None,
            company='Allianz Technology'
        )
        top_manager.set_password('password123')
        db.session.add(top_manager)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample data: {str(e)}")

def build_hierarchy_from_excel(file_path):
    """Build hierarchy relationships after importing employee data"""
    try:
        # Read the Excel file
        df = pd.read_excel(file_path)

        # Process each row to establish manager relationships
        for index, row in df.iterrows():
            try:
                # Find the employee
                employee_id = row.get('System_ID') or row.get('Bensl_ID')
                manager_name = row.get('Manager_Name') or row.get('Manager Name')

                if pd.isna(employee_id) or pd.isna(manager_name):
                    continue

                # Find the employee in database
                employee = Employee.query.filter(
                    (Employee.system_id == str(employee_id)) | 
                    (Employee.bensl_id == str(employee_id))
                ).first()

                if not employee:
                    continue

                # Find the manager
                manager = Employee.query.filter(
                    Employee.full_name.ilike(f'%{manager_name}%')
                ).first()

                if manager and manager.id != employee.id:
                    employee.manager_id = manager.id
                    employee.manager_name = manager.full_name

                    # Set manager flag if not already set
                    if not manager.is_manager:
                        manager.is_manager = True

            except Exception as e:
                print(f"Error processing row {index}: {str(e)}")
                continue

        db.session.commit()
        return {'success': True, 'message': 'Hierarchy relationships updated successfully'}

    except Exception as e:
        db.session.rollback()
        return {'success': False, 'error': f'Error building hierarchy: {str(e)}'}