"""
AI Smart Attendance System - MVP (Data-Driven)
A fully functional Streamlit application for attendance management.
Uses Streamlit session_state for real data management.
"""

import streamlit as st
from datetime import datetime
import json
import base64
import os
import json
import base64
import os


# ============================================================================
# A. PAGE CONFIGURATION & STYLING
# ============================================================================

st.set_page_config(
    page_title="AI Smart Attendance System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, clean UI
st.markdown("""
    <style>
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .metric-value {
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
        }
        .metric-label {
            font-size: 14px;
            opacity: 0.9;
        }
        .dashboard-header {
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid #667eea;
            margin-bottom: 30px;
        }
        .student-item {
            padding: 10px;
            margin: 5px 0;
            background: #f0f0f0;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
""", unsafe_allow_html=True)


# ============================================================================
# B.5 DATA PERSISTENCE FUNCTIONS
# ============================================================================

DATA_FILE = "data.json"

def get_period_label(period):
    """Get readable label for a period."""
    if not period:
        return ""
    period_type = period.get("type", "lecture").capitalize()
    subject = period.get("subject", "-")
    start = period.get("start_time", "")
    end = period.get("end_time", "")
    return f"{period_type}: {subject} ({start}-{end})"


def get_period_number(period_index):
    """Convert period index to period ID (P1, P2, etc.)."""
    return f"P{period_index + 1}"


def migrate_attendance_to_new_format():
    """
    Migrate old attendance format to new period-based format.
    Old: Individual records with roll_no per entry
    New: Single record per period with attendance dict
    """
    old_records = st.session_state.period_attendance
    if not old_records:
        return
    
    # Check if already in new format (has "attendance" key with dict)
    if old_records and isinstance(old_records[0].get("attendance"), dict):
        return  # Already in new format
    
    new_records = {}  # Key: (date, day, period)
    
    for record in old_records:
        # Check if this is old format (has roll_no key)
        if "roll_no" not in record:
            # Already in new format, skip
            new_records_list = [r for r in st.session_state.period_attendance if isinstance(r.get("attendance"), dict)]
            if new_records_list:
                return
        
        date = record.get("date", datetime.now().strftime("%Y-%m-%d"))
        day = record.get("day")
        period_label = record.get("period", "")
        
        # Extract subject and type from period label
        subject = "-"
        period_type = "Lecture"
        if ":" in period_label:
            type_part, rest = period_label.split(":", 1)
            period_type = type_part.strip()
            if "(" in rest:
                subject_part, _ = rest.split("(", 1)
                subject = subject_part.strip()
        
        key = (date, day, period_label)
        
        if key not in new_records:
            # Find period index for this label
            day_periods = st.session_state.timetable.get(day, [])
            period_index = 0
            for idx, p in enumerate(day_periods):
                if get_period_label(p) == period_label:
                    period_index = idx
                    break
            
            new_records[key] = {
                "date": date,
                "day": day,
                "period": get_period_number(period_index),
                "subject": subject,
                "type": period_type.lower(),
                "attendance": {}
            }
        
        # Add student attendance
        roll_no = record.get("roll_no")
        status = record.get("status", "Absent")
        new_records[key]["attendance"][roll_no] = status
    
    # Replace old format with new format
    st.session_state.period_attendance = list(new_records.values())


def convert_bytes_to_base64(photo_bytes):
    """Convert image bytes to base64 string for JSON serialization."""
    if photo_bytes is None or not isinstance(photo_bytes, bytes):
        return None
    return base64.b64encode(photo_bytes).decode('utf-8')


def convert_base64_to_bytes(base64_string):
    """Convert base64 string back to image bytes."""
    if base64_string is None or not isinstance(base64_string, str):
        return None
    try:
        return base64.b64decode(base64_string.encode('utf-8'))
    except Exception:
        return None


def load_data():
    """Load data from JSON file and restore session state with base64 image conversion."""
    try:
        if not os.path.exists(DATA_FILE):
            return  # File doesn't exist yet, use defaults
        
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        # Restore students with converted base64 photos back to bytes
        st.session_state.students = []
        for student in data.get("students", []):
            student_copy = student.copy()
            if student_copy.get("photo"):
                student_copy["photo"] = convert_base64_to_bytes(student_copy["photo"])
            st.session_state.students.append(student_copy)
        
        # Restore period attendance and migrate to new format if needed
        st.session_state.period_attendance = data.get("period_attendance", [])
        
        # Restore timetable
        st.session_state.timetable = data.get("timetable", {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": []
        })
        
        # Migrate old attendance format to new format if needed
        migrate_attendance_to_new_format()
    except Exception as e:
        st.error(f"❌ Error loading data: {str(e)}")


def save_data():
    """Save session state data to JSON file with base64-encoded images."""
    try:
        data_to_save = {
            "students": [],
            "period_attendance": st.session_state.period_attendance,
            "timetable": st.session_state.timetable
        }
        
        # Convert student photos to base64 before saving
        for student in st.session_state.students:
            student_copy = student.copy()
            if student_copy.get("photo"):
                student_copy["photo"] = convert_bytes_to_base64(student_copy["photo"])
            data_to_save["students"].append(student_copy)
        
        # Write to JSON file
        with open(DATA_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)
    except Exception as e:
        st.error(f"❌ Error saving data: {str(e)}")


# ============================================================================
# B. SESSION STATE INITIALIZATION (MVP - Real Data Structures)
# ============================================================================

def initialize_session_state():
    """Initialize session state with empty structures for real college data."""
    
    # Load persisted data first
    load_data()
    
    # Page navigation state
    if 'page' not in st.session_state:
        st.session_state.page = "Dashboard"
    
    # Students list: List of dictionaries with college structure
    if 'students' not in st.session_state:
        st.session_state.students = []
        # Student structure: {
        #     "name": "",
        #     "roll_no": "",
        #     "prn": "",
        #     "branch": "",
        #     "class": "",
        #     "photo": ""
        # }
    
    # Attendance list: List of attendance records
    if 'attendance' not in st.session_state:
        st.session_state.attendance = []
    
    # Timetable: Dictionary by day with period types
    if 'timetable' not in st.session_state:
        st.session_state.timetable = {
            "Monday": [],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": []
        }
        # Period structure: {
        #     "type": "lecture",  # or "break", "recess"
        #     "subject": "",
        #     "start_time": "",
        #     "end_time": ""
        # }
    
    # Period-based attendance: Store with day and period
    if 'period_attendance' not in st.session_state:
        st.session_state.period_attendance = []
    
    # Selected period for attendance marking
    if 'selected_day' not in st.session_state:
        st.session_state.selected_day = "Monday"
    if 'selected_period' not in st.session_state:
        st.session_state.selected_period = None
    
    # Active students for display (optional tracking)
    if 'active_students' not in st.session_state:
        st.session_state.active_students = {}
    
    # Ensure Saturday is added to timetable (backward compatibility)
    if "Saturday" not in st.session_state.timetable:
        st.session_state.timetable["Saturday"] = []


initialize_session_state()


# ============================================================================
# C. HELPER FUNCTIONS (MVP Logic)
# ============================================================================

def get_attendance_stats():
    """Calculate real attendance statistics from session state."""
    total_students = len(st.session_state.students)
    
    # Get today's attendance records
    today = datetime.now().strftime("%Y-%m-%d")
    today_attendance = [a for a in st.session_state.attendance if a.get("date") == today]
    
    present_count = sum(1 for a in today_attendance if a.get("status") == "Present")
    absent_count = sum(1 for a in today_attendance if a.get("status") == "Absent")
    
    attendance_rate = (present_count / total_students * 100) if total_students > 0 else 0
    
    return {
        "total": total_students,
        "present": present_count,
        "absent": absent_count,
        "late": sum(1 for a in today_attendance if a.get("status") == "Late"),
        "rate": attendance_rate
    }


def get_student_by_roll_no(roll_no):
    """Find student by roll number."""
    for student in st.session_state.students:
        if student.get("roll_no") == roll_no:
            return student
    return None


def get_student_by_prn(prn):
    """Find student by PRN (unique identifier)."""
    for student in st.session_state.students:
        if student.get("prn") == prn:
            return student
    return None


def check_overlapping_periods(day, new_start, new_end):
    """Check if new period overlaps with existing periods on the day."""
    periods = st.session_state.timetable.get(day, [])
    for period in periods:
        existing_start = period.get("start_time")
        existing_end = period.get("end_time")
        
        # Simple string comparison for time (works for HH:MM format)
        if not (new_end <= existing_start or new_start >= existing_end):
            return True  # Overlap found
    return False  # No overlap


def is_break_period(day, start_time):
    """Check if a given time slot is a break/recess on the day."""
    periods = st.session_state.timetable.get(day, [])
    for period in periods:
        if period.get("start_time") == start_time:
            period_type = period.get("type", "lecture")
            return period_type in ["break", "recess"]
    return False


def add_period_attendance(day, period, roll_no, name, status):
    """
    Add or update period-based attendance record.
    Stores all students for a period in a single record.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    period_label = get_period_label(period)
    
    # Extract subject and type from period
    subject = period.get("subject", "-")
    period_type = period.get("type", "lecture")
    
    # Find period index to generate period ID
    day_periods = st.session_state.timetable.get(day, [])
    period_index = 0
    for idx, p in enumerate(day_periods):
        if get_period_label(p) == period_label:
            period_index = idx
            break
    
    period_id = get_period_number(period_index)
    
    # Check if record already exists for this day/period
    for record in st.session_state.period_attendance:
        if (record.get("date") == today and 
            record.get("day") == day and 
            record.get("period") == period_id):
            # Update existing record
            record["attendance"][roll_no] = status
            return True
    
    # Create new period record
    new_record = {
        "date": today,
        "day": day,
        "period": period_id,
        "subject": subject,
        "type": period_type,
        "attendance": {roll_no: status}
    }
    st.session_state.period_attendance.append(new_record)
    return True


def add_attendance_record(roll_no, name, status):
    """Add attendance record for a student."""
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if record already exists for today
    for record in st.session_state.attendance:
        if record.get("roll_no") == roll_no and record.get("date") == today:
            record["status"] = status
            record["timestamp"] = timestamp
            return True
    
    # Add new record
    st.session_state.attendance.append({
        "roll_no": roll_no,
        "name": name,
        "status": status,
        "date": today,
        "timestamp": timestamp
    })
    return True


def get_today_attendance():
    """Get all attendance records for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    return [a for a in st.session_state.attendance if a.get("date") == today]


def calculate_attendance_percentage(student_roll):
    """
    Calculate attendance percentage for a student.
    Works with new period-based attendance format.
    
    Args:
        student_roll: Roll number of the student
        
    Returns:
        float: Attendance percentage (0-100), or 0 if no records
    """
    attendance_records = []
    
    # Get all period-based attendance records for this student
    for record in st.session_state.period_attendance:
        # Check if student has attendance in this period
        if isinstance(record.get("attendance"), dict):
            if student_roll in record.get("attendance", {}):
                attendance_records.append({
                    "type": record.get("type", "lecture"),
                    "status": record.get("attendance", {}).get(student_roll, "Absent")
                })
    
    if not attendance_records:
        return 0.0
    
    # Count only lecture/lab/practical periods (ignore break/recess)
    attendance_classes = [
        a for a in attendance_records 
        if a.get("type") in ["lecture", "lab", "practical"]
    ]
    
    if not attendance_classes:
        return 0.0
    
    # Count present status
    present_count = sum(
        1 for a in attendance_classes 
        if a.get("status") == "Present"
    )
    
    # Calculate percentage
    attendance_percentage = (present_count / len(attendance_classes)) * 100
    return round(attendance_percentage, 2)


def get_student_attendance_summary():
    """
    Get attendance summary for all students.
    Works with new period-based attendance format.
    
    Returns:
        list: List of dictionaries with format:
            {
                "roll_no": "",
                "name": "",
                "total_classes": 0,
                "present": 0,
                "attendance_percentage": 0
            }
    """
    summary = []
    
    # Iterate through all students
    for student in st.session_state.students:
        student_roll = student.get("roll_no")
        student_name = student.get("name")
        
        # Get all attendance records for this student from period records
        total_classes = 0
        present_count = 0
        
        for record in st.session_state.period_attendance:
            # Check if this is a lecture/lab/practical period (not break/recess)
            if record.get("type") not in ["lecture", "lab", "practical"]:
                continue
            
            attendance_dict = record.get("attendance", {})
            if isinstance(attendance_dict, dict) and student_roll in attendance_dict:
                total_classes += 1
                if attendance_dict[student_roll] == "Present":
                    present_count += 1
        
        # Calculate percentage
        attendance_percentage = (
            (present_count / total_classes * 100) 
            if total_classes > 0 
            else 0
        )
        
        # Add to summary
        summary.append({
            "roll_no": student_roll,
            "name": student_name,
            "total_classes": total_classes,
            "present": present_count,
            "attendance_percentage": round(attendance_percentage, 2)
        })
    
    return summary


# ============================================================================
# D. DASHBOARD PAGE
# ============================================================================

def show_dashboard():
    """Display the main dashboard with college attendance metrics."""
    
    st.markdown("""
        <div class="dashboard-header">
            <h1>📊 Attendance Dashboard</h1>
            <p>College Attendance Management System</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Get current stats
    stats = get_attendance_stats()
    
    # Display date/time and system info
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📅 Today's Date", datetime.now().strftime("%B %d, %Y"))
    with col2:
        today_name = datetime.now().strftime("%A")
        st.metric("📋 Day", today_name)
    with col3:
        today_periods = st.session_state.timetable.get(today_name, [])
        lecture_count = sum(1 for p in today_periods if p.get("type") == "lecture")
        st.metric("🎓 Lectures Today", lecture_count)
    with col4:
        st.metric("🕐 Current Time", datetime.now().strftime("%H:%M:%S"))
    
    st.markdown("---")
    
    # ===== SELECTED PERIOD SECTION =====
    st.subheader("📌 Selected Period for Attendance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_day = st.selectbox(
            "Select Day",
            list(st.session_state.timetable.keys()),
            key="dashboard_day"
        )
        st.session_state.selected_day = selected_day
    
    with col2:
        day_periods = st.session_state.timetable.get(selected_day, [])
        period_options = [get_period_label(p) for p in day_periods]
        
        if period_options:
            selected_period_label = st.selectbox(
                "Select Period",
                period_options,
                key="dashboard_period"
            )
            # Find the period object
            for p in day_periods:
                if get_period_label(p) == selected_period_label:
                    st.session_state.selected_period = p
                    break
        else:
            st.info("No periods for selected day")
    
    with col3:
        if st.session_state.selected_period:
            period_type = st.session_state.selected_period.get("type", "").upper()
            st.metric("Period Type", period_type)
        else:
            st.info("No period selected")
    
    st.markdown("---")
    
    # ===== PERIOD-WISE ATTENDANCE SUMMARY =====
    st.subheader("📊 Period-wise Attendance Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Total Students Card
    with col1:
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Students</div>
                <div class="metric-value">{stats['total']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Present Today Card
    with col2:
        st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="metric-label">Present Today</div>
                <div class="metric-value">{stats['present']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Absent Today Card
    with col3:
        st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="metric-label">Absent Today</div>
                <div class="metric-value">{stats['absent']}</div>
            </div>
        """, unsafe_allow_html=True)
    
    # Attendance Rate Card
    with col4:
        st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <div class="metric-label">Attendance Rate</div>
                <div class="metric-value">{stats['rate']:.1f}%</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick Stats and Session Info
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📌 Quick Stats")
        st.info(f"✅ Present: {stats['present']}/{stats['total']}")
        st.warning(f"❌ Absent: {stats['absent']}/{stats['total']}")
        st.metric("⏱️ Late", stats['late'])
    
    with col2:
        st.subheader("📊 Summary")
        if stats['total'] == 0:
            st.warning("No students added yet. Go to 'Add Student' to get started!")
        else:
            if stats['present'] > stats['absent']:
                st.success(f"Good attendance rate: {stats['rate']:.1f}%")
            elif stats['rate'] >= 75:
                st.info(f"Attendance rate is acceptable: {stats['rate']:.1f}%")
            else:
                st.error(f"Low attendance rate: {stats['rate']:.1f}%")
    
    st.markdown("---")
    
    # ===== PERIOD-WISE ATTENDANCE SECTION =====
    if st.session_state.period_attendance:
        st.subheader("📈 Period-wise Attendance Breakdown")
        
        # Group attendance by period
        period_summary = {}
        today = datetime.now().strftime("%Y-%m-%d")
        
        for record in st.session_state.period_attendance:
            if record.get("date") == today:
                period_key = f"{record.get('day')} - {record.get('period')}"
                if period_key not in period_summary:
                    period_summary[period_key] = {"Present": 0, "Absent": 0, "Late": 0}
                
                # Count attendance from the attendance dictionary
                for roll_no, status in record.get("attendance", {}).items():
                    period_summary[period_key][status] = period_summary[period_key].get(status, 0) + 1
        
        if period_summary:
            cols = st.columns(min(3, len(period_summary)))
            for idx, (period, counts) in enumerate(sorted(period_summary.items())):
                with cols[idx % len(cols)]:
                    total_marked = sum(counts.values())
                    st.metric(f"📌 {period.split(' - ')[1][:20]}", 
                             f"{counts['Present']}/{total_marked}")
                    st.caption(f"✅ {counts['Present']} | ❌ {counts['Absent']} | ⏱️ {counts['Late']}")
        else:
            st.info("No period-wise attendance marked yet. Go to 'Live Attendance' to mark attendance by period.")



# ============================================================================
# E. ADD STUDENT PAGE
# ============================================================================

def show_add_student():
    """Add Student page - Collect student details and add to session state."""
    st.title("➕ Add Student")
    
    st.write("Add new students to the college system. Each student must have unique roll number and PRN.")
    st.markdown("---")
    
    # ===== STUDENT DETAILS SECTION =====
    st.subheader("👤 Student Details")
    col1, col2 = st.columns(2)
    
    with col1:
        student_name = st.text_input(
            "Student Name",
            placeholder="Enter full name",
            key="add_student_name"
        )
    
    with col2:
        roll_number = st.text_input(
            "Roll Number",
            placeholder="e.g., 101",
            key="add_student_roll"
        )
    
    col3, col4 = st.columns(2)
    
    with col3:
        prn = st.text_input(
            "PRN (Permanent Registration Number)",
            placeholder="e.g., 2024001",
            key="add_student_prn"
        )
    
    with col4:
        st.text("")  # Spacer
        st.text("")
    
    # ===== ACADEMIC DETAILS SECTION =====
    st.subheader("📚 Academic Details")
    col5, col6 = st.columns(2)
    
    with col5:
        branch = st.selectbox(
            "Branch",
            ["Computer Science", "Electronics", "Mechanical", "Civil", "Electrical", "Other"],
            key="add_student_branch"
        )
    
    with col6:
        class_name = st.text_input(
            "Class/Semester",
            placeholder="e.g., FE (First Year), SE, TE, BE",
            key="add_student_class"
        )
    
    # ===== PHOTO UPLOAD SECTION =====
    st.subheader("📷 Photo Upload")
    uploaded_file = st.file_uploader(
        "Upload Student Photo (Optional)",
        type=["jpg", "jpeg", "png"],
        key="add_student_photo"
    )
    
    photo_bytes = None
    if uploaded_file is not None:
        photo_bytes = uploaded_file.read()
        if isinstance(photo_bytes, bytes):
            st.image(photo_bytes, width=150, caption="Uploaded Photo")
        else:
            st.warning("⚠️ Old image format not supported. Please re-upload.")
    
    # Validation and Add button
    st.markdown("---")
    if st.button("➕ Add Student", key="btn_add_student"):
        # Validation
        if not student_name or not roll_number or not prn or not branch or not class_name:
            st.error("❌ Please fill in all required fields (Name, Roll, PRN, Branch, Class)")
        elif get_student_by_roll_no(roll_number):
            st.error(f"❌ Roll number '{roll_number}' already exists!")
        elif get_student_by_prn(prn):
            st.error(f"❌ PRN '{prn}' already exists!")
        else:
            # Add student to session state
            new_student = {
                "name": student_name,
                "roll_no": roll_number,
                "prn": prn,
                "branch": branch,
                "class": class_name,
                "photo": photo_bytes
            }
            st.session_state.students.append(new_student)
            save_data()  # Persist changes
            st.success(f"✅ Student '{student_name}' (Roll: {roll_number}, PRN: {prn}) added successfully!")

    
    st.markdown("---")
    st.subheader(f"📋 All Students ({len(st.session_state.students)})")
    
    if len(st.session_state.students) == 0:
        st.info("No students added yet. Add a student using the form above.")
    else:
        # Display students in a table-like format
        for i, student in enumerate(st.session_state.students, 1):
            col1, col2, col3 = st.columns([2, 3, 1])
            
            with col1:
                st.write(f"**{student['name']}**")
                st.caption(f"Roll: {student['roll_no']} | PRN: {student['prn']}")
            
            with col2:
                st.write(f"**{student['branch']}** | {student['class']}")
            
            with col3:
                if student['photo']:
                    st.caption("📷 Photo")




# ============================================================================
# E.5 STUDENT DIRECTORY PAGE (NEW)
# ============================================================================

def show_student_directory():
    """Display all students in a hybrid table + detail panel layout."""
    st.title("📖 Student Directory")
    
    st.write("View and manage all students in the system with their complete information and attendance analytics.")
    st.markdown("---")
    
    # ===== ADD STUDENT BUTTON =====
    col1, col2 = st.columns([0.15, 0.85])
    with col1:
        if st.button("➕ Add Student", use_container_width=True):
            st.session_state.page = "Add Student"
            st.rerun()
    
    st.markdown("---")
    
    # ===== EMPTY STATE =====
    if len(st.session_state.students) == 0:
        st.info("📌 No students in the system yet. Click the 'Add Student' button above to get started.")
        return
    
    # ===== STATS SECTION =====
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Total Students", len(st.session_state.students))
    with col2:
        unique_branches = len(set(s.get('branch', 'Unknown') for s in st.session_state.students))
        st.metric("🏢 Branches", unique_branches)
    with col3:
        students_with_photo = sum(1 for s in st.session_state.students if s.get('photo'))
        st.metric("📷 With Photos", students_with_photo)
    
    st.markdown("---")
    
    # ===== PRIMARY TABLE VIEW =====
    st.subheader("📊 Student Directory Table")
    st.write("Click on a row number below to view detailed information:")
    
    # Create table data with all required columns
    table_data = []
    for idx, student in enumerate(st.session_state.students):
        attendance_pct = calculate_attendance_percentage(student.get('roll_no'))
        table_data.append({
            "Index": idx,
            "Roll No": student.get('roll_no'),
            "Name": student.get('name'),
            "PRN": student.get('prn'),
            "Branch": student.get('branch'),
            "Class": student.get('class'),
            "Photo": "✅" if student.get('photo') else "❌",
            "Attendance %": f"{attendance_pct}%"
        })
    
    # Display as professional dataframe
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Index": st.column_config.NumberColumn("ID", width="small"),
            "Roll No": st.column_config.TextColumn("Roll No", width="small"),
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "PRN": st.column_config.TextColumn("PRN", width="medium"),
            "Branch": st.column_config.TextColumn("Branch", width="medium"),
            "Class": st.column_config.TextColumn("Class", width="small"),
            "Photo": st.column_config.TextColumn("Photo", width="small"),
            "Attendance %": st.column_config.TextColumn("Attendance %", width="small")
        }
    )
    
    st.markdown("---")
    
    # ===== ROW SELECTION & DETAIL PANEL =====
    st.subheader("🔍 Student Details & Management")
    
    col1, col2 = st.columns([0.3, 0.7])
    
    with col1:
        selected_index = st.number_input(
            "Select Student (by ID):",
            min_value=0,
            max_value=len(st.session_state.students) - 1,
            value=0,
            step=1,
            key="dir_student_index"
        )
    
    # Get selected student
    selected_student = st.session_state.students[int(selected_index)]
    attendance_pct = calculate_attendance_percentage(selected_student.get('roll_no'))
    
    # Display detail panel
    detail_col1, detail_col2, detail_col3 = st.columns([0.35, 0.35, 0.3])
    
    with detail_col1:
        st.write("### � Student Photo")
        if selected_student.get('photo'):
            if isinstance(selected_student['photo'], bytes):
                st.image(selected_student['photo'], width=200, caption=f"{selected_student['name']}'s Photo")
            else:
                st.warning("⚠️ Old image format not supported. Please re-upload.")
        else:
            st.info("📌 No photo uploaded")
    
    with detail_col2:
        st.write("### 📋 Student Information")
        st.write(f"**Name:** {selected_student['name']}")
        st.write(f"**Roll No:** {selected_student['roll_no']}")
        st.write(f"**PRN:** {selected_student['prn']}")
        st.write(f"**Branch:** {selected_student['branch']}")
        st.write(f"**Class:** {selected_student['class']}")
    
    with detail_col3:
        st.write("### 📊 Attendance")
        st.metric("Attendance %", f"{attendance_pct}%")
        
        # Get total and present counts
        summary = get_student_attendance_summary()
        for record in summary:
            if record['roll_no'] == selected_student['roll_no']:
                st.write(f"**Total:** {record['total_classes']}")
                st.write(f"**Present:** {record['present']}")
                st.write(f"**Absent:** {record['total_classes'] - record['present']}")
                break
    
    st.markdown("---")
    
    # ===== ACTION BUTTONS =====
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 View Full Attendance", use_container_width=True):
            st.info(f"📌 Attendance records for {selected_student['name']} (Roll: {selected_student['roll_no']})")
            # Display period-based attendance for this student
            student_attendance = []
            for record in st.session_state.period_attendance:
                attendance_dict = record.get("attendance", {})
                if isinstance(attendance_dict, dict) and selected_student['roll_no'] in attendance_dict:
                    status = attendance_dict[selected_student['roll_no']]
                    student_attendance.append({
                        "date": record.get("date"),
                        "day": record.get("day"),
                        "period": record.get("period"),
                        "subject": record.get("subject"),
                        "type": record.get("type"),
                        "status": status
                    })
            
            if student_attendance:
                for record in student_attendance:
                    st.write(f"**{record['date']}** | {record['day']} | {record['period']} ({record['subject']}) | {record['type'].upper()} | Status: **{record['status']}**")
            else:
                st.write("No attendance records found.")
    
    with col2:
        st.write("")  # Spacer
    
    with col3:
        if st.button("🗑️ Remove Student", use_container_width=True, key="dir_remove_btn"):
            # Remove student from list
            removed_name = st.session_state.students[int(selected_index)]['name']
            st.session_state.students.pop(int(selected_index))
            save_data()  # Persist changes
            st.success(f"✅ Student '{removed_name}' removed successfully!")
            st.rerun()



# ============================================================================
# F. REMOVE STUDENT PAGE



# ============================================================================
# F. REMOVE STUDENT PAGE
# ============================================================================

def show_remove_student():
    """Remove Student page - Remove students with college details."""
    st.title("➖ Remove Student")
    
    st.write("Remove students from the system. All related attendance records will also be removed.")
    st.markdown("---")
    
    if len(st.session_state.students) == 0:
        st.info("No students to remove. Add students first using the 'Add Student' page.")
        return
    
    # Display current students
    st.subheader(f"Current Students ({len(st.session_state.students)})")
    
    # Create roll number options
    roll_numbers = [s["roll_no"] for s in st.session_state.students]
    
    selected_roll = st.selectbox(
        "Select student to remove:",
        roll_numbers,
        format_func=lambda x: f"{x} - {get_student_by_roll_no(x)['name']}"
    )
    
    # Show selected student details
    if selected_roll:
        student = get_student_by_roll_no(selected_roll)
        st.info(f"""
        **Student to Remove:**
        - Name: {student['name']}
        - Roll: {student['roll_no']}
        - PRN: {student['prn']}
        - Branch: {student['branch']}
        - Class: {student['class']}
        """)
    
    if st.button("🗑️ Remove Selected Student"):
        # Find and remove student
        for i, student in enumerate(st.session_state.students):
            if student["roll_no"] == selected_roll:
                removed_student = st.session_state.students.pop(i)
                st.session_state.attendance = [
                    a for a in st.session_state.attendance 
                    if a.get("roll_no") != selected_roll
                ]
                save_data()  # Persist changes
                st.success(f"✅ Student '{removed_student['name']}' (PRN: {removed_student['prn']}) removed successfully!")
                st.info("✓ All related attendance records also removed.")
                break
    
    st.markdown("---")
    st.subheader("📋 Remaining Students")
    if st.session_state.students:
        for i, student in enumerate(st.session_state.students, 1):
            st.write(f"{i}. **{student['name']}** (Roll: {student['roll_no']}, PRN: {student['prn']}) - {student['branch']}")


# ============================================================================
# G. TIMETABLE PAGE
# ============================================================================

def show_timetable():
    """Timetable page - Display and manage class schedule with period types."""
    st.title("📅 Timetable Management")
    
    st.write("Manage your college class schedule. Add lectures, breaks, and recess periods.")
    st.markdown("---")
    
    # ===== RESET OPTIONS =====
    st.subheader("🔄 Reset Timetable Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Reset Day Timetable", key="btn_reset_day"):
            st.warning("⚠️ Select the day to reset in the form below, then click this button again.")
    
    with col2:
        if st.button("🗑️ Reset Full Timetable", key="btn_reset_all"):
            if st.session_state.get("confirm_reset_all"):
                st.session_state.timetable = {
                    "Monday": [],
                    "Tuesday": [],
                    "Wednesday": [],
                    "Thursday": [],
                    "Friday": [],
                    "Saturday": []
                }
                save_data()  # Persist changes
                st.success("✅ Full timetable reset successfully!")
                st.session_state.confirm_reset_all = False
                st.rerun()
            else:
                st.error("⚠️ Click the 'Confirm Reset' button below to reset the full timetable.")
    
    col1, col2 = st.columns(2)
    with col1:
        reset_day = st.selectbox("Day to Reset", list(st.session_state.timetable.keys()), key="reset_day_select")
        if st.button("✅ Reset Selected Day", key="btn_confirm_reset_day"):
            st.session_state.timetable[reset_day] = []
            save_data()  # Persist changes
            st.success(f"✅ {reset_day} timetable reset successfully!")
            st.rerun()
    
    with col2:
        st.session_state.confirm_reset_all = st.checkbox("I confirm to reset the entire timetable", key="confirm_reset_check")
    
    st.markdown("---")
    
    # ===== ADD PERIOD SECTION =====
    st.subheader("➕ Add New Period")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        day = st.selectbox("Day", list(st.session_state.timetable.keys()), key="tt_day")
    
    with col2:
        period_type = st.selectbox(
            "Period Type",
            ["Lecture", "Break", "Recess", "Lab", "Practical"],
            key="tt_type"
        )
    
    with col3:
        subject = st.text_input(
            "Subject",
            placeholder="e.g., Mathematics",
            key="tt_subject"
        )
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        start_time = st.text_input("Start Time", placeholder="09:00", key="tt_start")
    
    with col5:
        end_time = st.text_input("End Time", placeholder="10:00", key="tt_end")
    
    with col6:
        st.text("")  # Spacer
    
    # Add Period Button
    if st.button("➕ Add Period", key="btn_add_period"):
        if not start_time or not end_time:
            st.error("❌ Please fill in start and end times")
        elif period_type in ["Lecture", "Lab", "Practical"] and not subject:
            st.error("❌ Subject is required for lecture, lab, and practical periods")
        elif check_overlapping_periods(day, start_time, end_time):
            st.error(f"❌ Period overlaps with existing period on {day}")
        else:
            new_period = {
                "type": period_type.lower(),
                "subject": subject if period_type not in ["Break", "Recess"] else period_type,
                "start_time": start_time,
                "end_time": end_time
            }
            st.session_state.timetable[day].append(new_period)
            save_data()  # Persist changes
            st.success(f"✅ {period_type} period added for {day} ({start_time}-{end_time})!")
            st.rerun()
    
    st.markdown("---")
    
    # ===== WEEKLY SCHEDULE SECTION =====
    st.subheader("📊 Weekly Schedule")
    
    # Display timetable by day
    for day, periods in st.session_state.timetable.items():
        with st.expander(f"**{day}** ({len(periods)} periods)", expanded=False):
            if len(periods) == 0:
                st.info("No periods added yet")
            else:
                for idx, period in enumerate(periods):
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        period_type_display = period.get("type", "lecture").capitalize()
                        subject = period.get("subject", "-")
                        start = period.get("start_time", "-")
                        end = period.get("end_time", "-")
                        
                        st.write(f"**{period_type_display}**: {subject} ({start} - {end})")
                    
                    with col2:
                        st.caption(f"#{idx + 1}")
                    
                    with col3:
                        if st.button("🗑️ Remove", key=f"btn_remove_period_{day}_{idx}"):
                            st.session_state.timetable[day].pop(idx)
                            save_data()  # Persist changes
                            st.success(f"✅ Period removed from {day}")
                            st.rerun()
    
    st.markdown("---")
    
    # ===== PERIOD TYPE LEGEND =====
    st.subheader("📌 Period Type Legend")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.success("**Lecture**: Regular class (attendance required)")
    
    with col2:
        st.warning("**Break**: Short break (no attendance)")
    
    with col3:
        st.warning("**Recess**: Long recess (no attendance)")
    
    with col4:
        st.info("**Lab**: Practical lab session (attendance required)")
    
    with col5:
        st.info("**Practical**: Practical session (attendance required)")


# ============================================================================
# H. LIVE ATTENDANCE PAGE
# ============================================================================

def show_live_attendance():
    """Live Attendance page - Mark attendance linked to specific periods."""
    st.title("🎥 Live Attendance Management (Period-Based)")
    
    st.write("Mark attendance for students linked to specific lecture/lab/practical periods.")
    st.markdown("---")
    
    if len(st.session_state.students) == 0:
        st.warning("⚠️ No students in the system. Add students first!")
        return
    
    # ===== SELECT PERIOD SECTION =====
    st.subheader("📅 Select Period for Attendance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        selected_day = st.selectbox(
            "Select Day",
            list(st.session_state.timetable.keys()),
            index=0,
            key="att_day"
        )
    
    with col2:
        day_periods = st.session_state.timetable.get(selected_day, [])
        # Filter out break and recess periods
        markable_periods = [p for p in day_periods if p.get("type") not in ["break", "recess"]]
        period_labels = [get_period_label(p) for p in markable_periods]
        
        if period_labels:
            selected_period_label = st.selectbox(
                "Select Period (Lectures/Labs/Practicals Only)",
                period_labels,
                key="att_period"
            )
            # Find the period object
            selected_period = None
            for p in markable_periods:
                if get_period_label(p) == selected_period_label:
                    selected_period = p
                    break
        else:
            st.error("❌ No lecture/lab/practical periods available for selected day!")
            selected_period = None
    
    if not selected_period:
        st.info("⏳ Please select a period with lectures, labs, or practicals to mark attendance.")
        return
    
    # Display selected period details
    st.info(f"📌 Selected: {selected_period_label}")
    
    st.markdown("---")
    
    # ===== MARK ATTENDANCE SECTION =====
    st.subheader("✅ Mark Attendance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        selected_roll = st.selectbox(
            "Select Student",
            [s["roll_no"] for s in st.session_state.students],
            format_func=lambda x: f"{x} - {get_student_by_roll_no(x)['name']}",
            key="att_student"
        )
    
    with col2:
        status = st.selectbox("Status", ["Present", "Absent", "Late"], key="att_status")
    
    with col3:
        if st.button("✅ Mark Attendance", key="btn_mark_att"):
            student = get_student_by_roll_no(selected_roll)
            add_period_attendance(selected_day, selected_period, selected_roll, student["name"], status)
            save_data()  # Persist changes
            st.success(f"✅ Attendance marked: {student['name']} ({student['roll_no']}) - {status}")
            st.rerun()
    
    st.markdown("---")
    
    # ===== PERIOD ATTENDANCE STATISTICS =====
    st.subheader(f"📊 {selected_period_label} - Attendance Summary")
    
    today = datetime.now().strftime("%Y-%m-%d")
    period_index = 0
    day_periods = st.session_state.timetable.get(selected_day, [])
    for idx, p in enumerate(day_periods):
        if get_period_label(p) == selected_period_label:
            period_index = idx
            break
    period_id = get_period_number(period_index)
    
    # Find the period record for today
    period_record = None
    for record in st.session_state.period_attendance:
        if (record.get("date") == today and 
            record.get("day") == selected_day and 
            record.get("period") == period_id):
            period_record = record
            break
    
    # Get attendance data from the period record
    attendance_dict = period_record.get("attendance", {}) if period_record else {}
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Students", len(st.session_state.students))
    with col2:
        present_count = sum(1 for status in attendance_dict.values() if status == "Present")
        st.metric("✅ Present", present_count)
    with col3:
        absent_count = sum(1 for status in attendance_dict.values() if status == "Absent")
        st.metric("❌ Absent", absent_count)
    with col4:
        late_count = sum(1 for status in attendance_dict.values() if status == "Late")
        st.metric("⏱️ Late", late_count)
    
    st.markdown("---")
    
    # ===== DETAILED ATTENDANCE LIST =====
    st.subheader("📋 Attendance Details for This Period")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**✅ Present:**")
        present_list = [(roll, status) for roll, status in attendance_dict.items() if status == "Present"]
        if present_list:
            for roll_no, status in present_list:
                student = get_student_by_roll_no(roll_no)
                student_name = student.get("name", roll_no) if student else roll_no
                st.write(f"✅ {student_name} ({roll_no})")
        else:
            st.info("No present records yet")
    
    with col2:
        st.write("**❌ Absent / ⏱️ Late:**")
        absent_list = [(roll, status) for roll, status in attendance_dict.items() if status in ["Absent", "Late"]]
        if absent_list:
            for roll_no, status in absent_list:
                student = get_student_by_roll_no(roll_no)
                student_name = student.get("name", roll_no) if student else roll_no
                status_emoji = "❌" if status == "Absent" else "⏱️"
                st.write(f"{status_emoji} {student_name} ({roll_no}) - {status}")
        else:
            st.info("No absent/late records yet")
    
    st.markdown("---")
    
    # ===== UNMARKED STUDENTS =====
    st.subheader("⏳ Students Not Yet Marked for This Period")
    
    marked_rolls = set(attendance_dict.keys())
    unmarked_students = [s for s in st.session_state.students if s["roll_no"] not in marked_rolls]
    
    if unmarked_students:
        for s in unmarked_students:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"⏳ {s['name']} ({s['roll_no']}) - {s['branch']}")
            with col2:
                st.caption(f"{s['class']}")
    else:
        st.success("✅ All students marked for this period!")


# ============================================================================
# I. SIDEBAR NAVIGATION
# ============================================================================

def render_sidebar():
    """Render sidebar navigation and update session state page."""
    st.sidebar.title("📚 Navigation")
    st.sidebar.markdown("---")
    
    # Page selection using selectbox
    page_options = [
        "Dashboard",
        "Add Student",
        "All Students",
        "Remove Student",
        "Timetable",
        "Live Attendance"
    ]
    
    # Get current page from session state (default to Dashboard)
    current_page = st.session_state.get('page', 'Dashboard')
    
    # Find the index of current page in options
    try:
        current_index = page_options.index(current_page)
    except ValueError:
        current_index = 0
    
    # Create selectbox with current page as default
    def on_page_change():
        """Callback function when page selection changes."""
        st.session_state.page = st.session_state.page_navigation
    
    selected_page = st.sidebar.selectbox(
        "Select a page:",
        page_options,
        index=current_index,
        on_change=on_page_change,
        key="page_navigation"
    )
    
    # Ensure session state is updated
    st.session_state.page = selected_page
    
    st.sidebar.markdown("---")
    
    # Summary stats in sidebar
    stats = get_attendance_stats()
    st.sidebar.info(f"""
    **📊 Quick Stats**
    
    Total Students: {stats['total']}
    Present Today: {stats['present']}
    Absent Today: {stats['absent']}
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.caption("🔧 AI Smart Attendance System v2.1 (College-Grade)")
    
    return st.session_state.page


# ============================================================================
# J. PAGE ROUTING & MAIN APP
# ============================================================================

def main():
    """Main application entry point with page routing."""
    
    # Render sidebar and get selected page
    selected_page = render_sidebar()
    
    # Route to the selected page
    page_routing = {
        "Dashboard": show_dashboard,
        "Add Student": show_add_student,
        "All Students": show_student_directory,
        "Remove Student": show_remove_student,
        "Timetable": show_timetable,
        "Live Attendance": show_live_attendance,
    }
    
    # Use session state page if available (respects button navigation)
    current_page = st.session_state.get('page', selected_page)
    
    # Execute the selected page function
    page_function = page_routing.get(current_page, show_dashboard)
    page_function()


# ============================================================================
# K. APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
