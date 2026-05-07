import logging
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

# ============================================================================
# RULE 13 - PROFESSIONAL LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class TimetableValidator:
    """RULE 9 - PERIOD VALIDATION ENGINE"""
    
    @staticmethod
    def validate(timetable: Dict[str, List[Dict[str, str]]]) -> List[str]:
        warnings = []
        if not isinstance(timetable, dict):
            return ["Invalid format: Timetable must be a dictionary mapping days to periods."]
            
        for day, periods in timetable.items():
            if not isinstance(periods, list):
                warnings.append(f"Invalid format for day {day}")
                continue
                
            sorted_periods = []
            for idx, p in enumerate(periods):
                if 'period' not in p or 'start_time' not in p or 'end_time' not in p or 'subject' not in p:
                    warnings.append(f"{day} - Period at index {idx} is missing required fields.")
                    continue
                try:
                    start = datetime.strptime(p['start_time'], "%H:%M").time()
                    end = datetime.strptime(p['end_time'], "%H:%M").time()
                    if start >= end:
                        warnings.append(f"{day} - {p['period']}: Invalid time range ({start} to {end}).")
                    sorted_periods.append((start, end, p['period']))
                except ValueError:
                    warnings.append(f"{day} - {p['period']}: Invalid time format.")
            
            sorted_periods.sort(key=lambda x: x[0])
            for i in range(len(sorted_periods) - 1):
                if sorted_periods[i][1] > sorted_periods[i+1][0]:
                    warnings.append(f"{day}: Overlapping periods detected between {sorted_periods[i][2]} and {sorted_periods[i+1][2]}.")
                    
        return warnings

class AttendanceLogicEngine:
    """
    Production-grade timetable-aware attendance logic system.
    """
    
    def __init__(self, 
                 persistence_file: str = "data/erp_attendance.json",
                 cooldown_seconds: int = 10,
                 late_grace_minutes: int = 10,
                 exit_timeout_seconds: int = 30):
        self.persistence_file = Path(persistence_file)
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configurations
        self.cooldown_seconds = cooldown_seconds
        self.late_grace_minutes = late_grace_minutes
        self.exit_timeout_seconds = exit_timeout_seconds
        
        # RULE 6 - ACTIVE STUDENT TRACKING
        self.active_students: Dict[str, Dict[str, Any]] = {}
        
        # RULE 10 - ERP ATTENDANCE DATA STRUCTURE
        self.erp_data: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        self.load_data()
        
        # RULE 12 - REAL-TIME EVENT ENGINE QUEUE
        self.event_queue = []
        self.event_logs = []
        self.lock = threading.Lock()
        self._load_timetable_from_app()

    def _load_timetable_from_app(self):
        """Attempts to dynamically load timetable from Streamlit or data.json"""
        self.timetable = {}
        try:
            with open("data.json", "r") as f:
                data = json.load(f)
                if "timetable" in data:
                    self.timetable = data["timetable"]
        except Exception as e:
            logger.warning(f"Could not load timetable from data.json: {e}")

    def load_data(self):
        """Load ERP structured data"""
        if self.persistence_file.exists():
            try:
                with open(self.persistence_file, 'r') as f:
                    self.erp_data = json.load(f)
            except Exception as e:
                logger.error(f"Error loading ERP data: {e}")
                self.erp_data = {}

    def save_data(self):
        """Save ERP structured data"""
        try:
            with open(self.persistence_file, 'w') as f:
                json.dump(self.erp_data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving ERP data: {e}")

    def get_current_period(self) -> Optional[Dict[str, str]]:
        """RULE 1 - PERIOD-BASED ATTENDANCE: Identify active period"""
        self._load_timetable_from_app() # Refresh timetable
        if not self.timetable:
            return None
            
        now = datetime.now()
        day_str = now.strftime("%A")
        date_str = now.strftime("%Y-%m-%d")
        current_time = now.time()
        
        # Check date-specific schedule first, fallback to weekday name
        if date_str in self.timetable:
            periods = self.timetable[date_str]
        else:
            periods = self.timetable.get(day_str, [])
        for p in periods:
            try:
                start = datetime.strptime(p.get('start_time', '00:00'), "%H:%M").time()
                end = datetime.strptime(p.get('end_time', '23:59'), "%H:%M").time()
                if start <= current_time <= end:
                    return p
            except Exception:
                continue
        return None

    def _mark_erp_attendance(self, date_str: str, subject: str, period: str, roll_no: str, record: Dict[str, Any]):
        """RULE 10 - Helper to store in ERP format"""
        if date_str not in self.erp_data:
            self.erp_data[date_str] = {}
        if subject not in self.erp_data[date_str]:
            self.erp_data[date_str][subject] = {}
        if period not in self.erp_data[date_str][subject]:
            self.erp_data[date_str][subject][period] = {}
            
        self.erp_data[date_str][subject][period][roll_no] = record
        self.save_data()

    def process_recognition_event(self, roll_no: str, name: str) -> None:
        """
        Main entry point for face recognition engine.
        RULE 12 - Real-time non-blocking processing.
        """
        with self.lock:
            self._handle_recognition(roll_no, name)
            
    def _handle_recognition(self, roll_no: str, name: str):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        period = self.get_current_period()
        if not period:
            return  # No active class

        subj = period.get('subject', 'Unknown')
        per_id = period.get('period', 'Unknown')
        
        # RULE 7 - DUPLICATE RECOGNITION PREVENTION
        if roll_no in self.active_students:
            student = self.active_students[roll_no]
            time_since_seen = (now - student['last_seen']).total_seconds()
            
            if time_since_seen <= self.cooldown_seconds:
                return # Ignore spam
                
            # RULE 4 - EXIT LOGIC
            if time_since_seen > self.exit_timeout_seconds:
                logger.info(f"[EXIT] Roll: {roll_no} | Time: {now.strftime('%H:%M')}")
                self.event_logs.append({
                    'type': 'EXIT', 'name': student['name'],
                    'subject': student.get('current_subject', ''),
                    'period': student.get('current_period', ''),
                    'time': now.strftime('%H:%M')
                })
                # Mark exit time in ERP
                try:
                    self.erp_data[date_str][student['current_subject']][student['current_period']][roll_no]['exit_time'] = now.strftime('%H:%M')
                    self.erp_data[date_str][student['current_subject']][student['current_period']][roll_no]['status'] = "Exited"
                    self.save_data()
                except KeyError:
                    pass
                del self.active_students[roll_no]
                # Process as new entry recursively
                self._handle_recognition(roll_no, name)
                return
            else:
                # RULE 3 - CONTINUOUS PRESENCE SYSTEM
                student['last_seen'] = now
                student['current_subject'] = subj
                student['current_period'] = per_id
                return
                
        # RULE 2 & 5 - ENTRY TIME WINDOW & LATE ARRIVAL
        start_time_str = period.get('start_time', '00:00')
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        start_dt = datetime.combine(now.date(), start_time)
        
        minutes_late = (now - start_dt).total_seconds() / 60.0
        
        if minutes_late <= self.late_grace_minutes:
            status = "Present"
            logger.info(f"[ENTRY] Roll: {roll_no} | Subject: {subj} | Period: {per_id} | Time: {now.strftime('%H:%M')}")
            self.event_logs.append({
                'type': 'ENTRY', 'name': name,
                'subject': subj, 'period': per_id,
                'time': now.strftime('%H:%M')
            })
        else:
            status = "Late"
            logger.info(f"[LATE] Roll: {roll_no} | Subject: {subj} | Time: {now.strftime('%H:%M')}")
            self.event_logs.append({
                'type': 'LATE', 'name': name,
                'subject': subj, 'period': per_id,
                'time': now.strftime('%H:%M')
            })

        record = {
            "name": name,
            "status": status,
            "entry_time": now.strftime('%H:%M'),
            "exit_time": None,
            "method": "Face Recognition"
        }
        
        self._mark_erp_attendance(date_str, subj, per_id, roll_no, record)
        
        # BRIDGE: Also sync to app period_attendance in data.json for Reports
        day_str = now.strftime("%A")
        self._sync_to_app_period_attendance(date_str, day_str, subj, per_id, roll_no, status)
        
        self.active_students[roll_no] = {
            "name": name,
            "status": "IN",
            "entry_time": now,
            "last_seen": now,
            "current_subject": subj,
            "current_period": per_id
        }

    def _sync_to_app_period_attendance(self, date_str: str, day_str: str, subj: str, per_id: str, roll_no: str, status: str):
        """
        BRIDGE: Sync AI recognition event into the app's period_attendance format
        stored in data.json so the Reports page can read it directly.
        
        data.json period_attendance format:
        [
            {
                "date": "2024-05-08",
                "day": "Wednesday",
                "period": "P1",
                "subject": "Mathematics",
                "type": "lecture",
                "attendance": {"46": "Present", "47": "Absent", ...}
            }, ...
        ]
        """
        try:
            # Load current data.json
            data_path = Path("data.json")
            if data_path.exists():
                with open(data_path, 'r') as f:
                    app_data = json.load(f)
            else:
                app_data = {"students": [], "period_attendance": [], "timetable": {}}
            
            period_attendance = app_data.get("period_attendance", [])
            
            # Find existing record for this date+period
            existing_record = None
            for rec in period_attendance:
                if (rec.get("date") == date_str and
                    rec.get("period") == per_id and
                    rec.get("subject") == subj):
                    existing_record = rec
                    break
            
            if existing_record is None:
                # Get period type from timetable
                period_type = "lecture"
                periods = self.timetable.get(date_str, self.timetable.get(day_str, []))
                for p in periods:
                    if p.get('period') == per_id and p.get('subject') == subj:
                        period_type = p.get('type', 'lecture')
                        break
                
                # Create new record
                new_record = {
                    "date": date_str,
                    "day": day_str,
                    "period": per_id,
                    "subject": subj,
                    "type": period_type,
                    "attendance": {}
                }
                period_attendance.append(new_record)
                existing_record = new_record
            
            # Update attendance for this student
            if "attendance" not in existing_record:
                existing_record["attendance"] = {}
            existing_record["attendance"][roll_no] = status
            
            # Save back to data.json
            app_data["period_attendance"] = period_attendance
            with open(data_path, 'w') as f:
                json.dump(app_data, f, indent=2)
                
            logger.info(f"[SYNC] Saved to period_attendance: {roll_no}={status} | {subj} {per_id} on {date_str}")
        except Exception as e:
            logger.error(f"[SYNC ERROR] Failed to sync to app period_attendance: {e}")

    def get_attendance_summary(self) -> dict:
        """Return today's attendance summary for the UI overlay."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_data = self.erp_data.get(today_str, {})
        total_records = sum(
            len(students)
            for subj in today_data.values()
            for students in subj.values()
        )
        return {"total_records": total_records, "date": today_str}

    def get_active_students_summary(self) -> dict:
        """Return list of currently active (in-room) students."""
        students_list = [
            {"roll_no": rn, "name": s["name"], "entry_time": s["entry_time"].strftime("%H:%M")}
            for rn, s in self.active_students.items()
        ]
        return {"count": len(students_list), "students": students_list}

    def trigger_auto_transition(self):
        """
        RULE 8 - AUTO PERIOD TRANSITION
        To be called periodically (e.g., by a background thread or UI refresh)
        """
        with self.lock:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            period = self.get_current_period()
            
            if not period:
                return
                
            subj = period.get('subject', 'Unknown')
            per_id = period.get('period', 'Unknown')
            
            for roll_no, student in list(self.active_students.items()):
                # If they are IN and active, but period has changed
                if student['current_period'] != per_id:
                    # Check if they timed out before transition
                    time_since_seen = (now - student['last_seen']).total_seconds()
                    if time_since_seen > self.exit_timeout_seconds:
                        # They left during the break, don't carry forward
                        try:
                            self.erp_data[date_str][student['current_subject']][student['current_period']][roll_no]['exit_time'] = student['last_seen'].strftime('%H:%M')
                            self.save_data()
                        except KeyError:
                            pass
                        del self.active_students[roll_no]
                    else:
                        # Auto carry forward!
                        student['current_subject'] = subj
                        student['current_period'] = per_id
                        
                        record = {
                            "name": student['name'],
                            "status": "Auto-Carried",
                            "entry_time": now.strftime('%H:%M'),
                            "exit_time": None,
                            "method": "Continuous Presence"
                        }
                        self._mark_erp_attendance(date_str, subj, per_id, roll_no, record)
                        # Also sync auto-carried attendance to app format
                        day_str = now.strftime("%A")
                        self._sync_to_app_period_attendance(date_str, day_str, subj, per_id, roll_no, "Present")
                        logger.info(f"[AUTO_CARRY] Roll: {roll_no} | New Period: {per_id}")
