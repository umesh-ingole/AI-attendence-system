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
                 exit_timeout_seconds: int = 15):
        self.persistence_file = Path(persistence_file)
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configurations
        self.cooldown_seconds = cooldown_seconds
        self.late_grace_minutes = late_grace_minutes
        self.exit_timeout_seconds = exit_timeout_seconds
        
        # RULE 6 - ACTIVE STUDENT TRACKING
        self.active_students: Dict[str, Dict[str, Any]] = {}
        self.pending_exits: Dict[str, Dict[str, Any]] = {}  # Queue for UI confirmation
        self.pending_auto_carries: Dict[str, Dict[str, Any]] = {} # Queue for Teacher Verification
        
        # RULE 10 - ERP ATTENDANCE DATA STRUCTURE
        self.erp_data: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
        self.load_data()
        
        # RULE 12 - REAL-TIME EVENT ENGINE QUEUE
        self.event_queue = []
        self.event_logs = []
        self.lock = threading.Lock()
        self._data_file_lock = threading.Lock()  # Separate lock for data.json I/O
        self._timetable_cache_time = 0  # Unix timestamp of last timetable load
        self._timetable_cache_ttl = 30  # Reload timetable at most every 30 seconds
        self._load_timetable_from_app()

    def _load_timetable_from_app(self):
        """Load timetable from data.json with a TTL cache to avoid per-frame disk reads."""
        now_ts = time.time()
        if now_ts - self._timetable_cache_time < self._timetable_cache_ttl and self.timetable:
            return  # Cache is still warm
        self.timetable = {}
        for _ in range(3):
            try:
                with open("data.json", "r") as f:
                    data = json.load(f)
                    if "timetable" in data:
                        self.timetable = data["timetable"]
                self._timetable_cache_time = time.time()
                break
            except FileNotFoundError:
                break
            except Exception:
                time.sleep(0.1)
        if not self.timetable:
            logger.debug("Timetable not loaded or empty.")

    def _add_log(self, log_entry: dict):
        """Helper to append logs with a maximum size limit to prevent memory leaks."""
        self.event_logs.append(log_entry)
        if len(self.event_logs) > 1000:
            self.event_logs.pop(0)

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
        self._load_timetable_from_app()  # Uses cache; only reloads every 30s
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
            
        # Priority check: Do not downgrade a Present status to Late
        existing = self.erp_data[date_str][subject][period].get(roll_no)
        if existing:
            current_status = existing.get("status")
            if current_status in ["Present", "Present (Excused)", "Auto-Carried"]:
                if record.get("status") in ["Late", "Absent"]:
                    # Preserve original entry time and status
                    record["status"] = current_status
                    record["entry_time"] = existing.get("entry_time", record["entry_time"])
            
        self.erp_data[date_str][subject][period][roll_no] = record
        self.save_data()

    def process_recognition_event(self, roll_no: str, name: str) -> None:
        """
        Main entry point for face recognition engine.
        RULE 12 - Real-time non-blocking processing.
        """
        with self.lock:
            # Prevent end-of-day zombies by clearing stale day records
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            stale_rolls = [r for r, s in self.active_students.items() if s['entry_time'].strftime("%Y-%m-%d") != today_str]
            for r in stale_rolls:
                del self.active_students[r]
                self.pending_exits.pop(r, None)
                self.pending_auto_carries.pop(r, None)
                
            self._handle_recognition(roll_no, name)
            
    def _handle_recognition(self, roll_no: str, name: str):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        period = self.get_current_period()
        
        # If there is no active period, we should only process EXITS for students who are already IN.
        if not period:
            if roll_no in self.active_students:
                student = self.active_students[roll_no]
                time_since_seen = (now - student['last_seen']).total_seconds()
                
                if time_since_seen <= self.cooldown_seconds:
                    return # Ignore spam
                    
                # RULE 4 - EXIT LOGIC (Queue for UI Confirmation even if class ended)
                if time_since_seen > self.exit_timeout_seconds:
                    if roll_no not in self.pending_exits:
                        logger.info(f"[PENDING EXIT AFTER CLASS] Roll: {roll_no} | Awaiting UI confirmation.")
                        self.pending_exits[roll_no] = {
                            'name': student['name'],
                            'current_subject': student.get('current_subject', ''),
                            'current_period': student.get('current_period', '')
                        }
            return  # No active class to join for new students

        subj = period.get('subject', 'Unknown')
        per_id = period.get('period', 'Unknown')
        
        # RULE 7 - DUPLICATE RECOGNITION PREVENTION
        if roll_no in self.active_students:
            student = self.active_students[roll_no]
            time_since_seen = (now - student['last_seen']).total_seconds()
            
            if time_since_seen <= self.cooldown_seconds:
                return # Ignore spam
                
            # RULE 4 - EXIT LOGIC (Queue for UI Confirmation)
            if time_since_seen > self.exit_timeout_seconds:
                if roll_no not in self.pending_exits:
                    logger.info(f"[PENDING EXIT] Roll: {roll_no} | Awaiting UI confirmation.")
                    self.pending_exits[roll_no] = {
                        'name': student['name'],
                        'current_subject': student.get('current_subject', ''),
                        'current_period': student.get('current_period', '')
                    }
                return
            else:
                # RULE 3 - CONTINUOUS PRESENCE SYSTEM
                student['last_seen'] = now
                
                # SMART AUTO-CARRY: If period changed and camera sees them, automate it!
                if student.get('current_period') != per_id:
                    logger.info(f"[SMART AUTO-CARRY] Roll: {roll_no} | New Period: {per_id}")
                    student['current_subject'] = subj
                    student['current_period'] = per_id
                    
                    record = {
                        "name": student['name'],
                        "status": "Auto-Carried",
                        "entry_time": now.strftime('%H:%M'),
                        "exit_time": None,
                        "method": "Continuous Vision"
                    }
                    self._mark_erp_attendance(date_str, subj, per_id, roll_no, record)
                    
                    day_str = now.strftime("%A")
                    self._sync_to_app_period_attendance(date_str, day_str, subj, per_id, roll_no, "Present")
                    
                    self._add_log({
                        'type': 'AUTO-CARRY', 'name': student['name'],
                        'subject': subj, 'period': per_id,
                        'time': now.strftime('%H:%M')
                    })
                    
                    # Remove from pending auto-carry if they were in there
                    if roll_no in self.pending_auto_carries:
                        del self.pending_auto_carries[roll_no]
                else:
                    student['current_subject'] = subj
                    student['current_period'] = per_id
                    
                return
                
        # RULE 2 & 5 - ENTRY TIME WINDOW & LATE ARRIVAL
        start_time_str = period.get('start_time', '00:00')
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        start_dt = datetime.combine(now.date(), start_time)
        
        minutes_late = (now - start_dt).total_seconds() / 60.0
        
        # Check for Digital Gatepass (Student B Improvement)
        has_gatepass = False
        try:
            with open("data.json", "r") as f:
                app_data = json.load(f)
                gatepasses = app_data.get("gatepasses", {})
                if date_str in gatepasses and roll_no in gatepasses[date_str]:
                    has_gatepass = True
        except Exception as e:
            logger.error(f"[GATEPASS ERROR] Failed to read data.json: {e}")
            
        if minutes_late <= self.late_grace_minutes:
            status = "Present"
            logger.info(f"[ENTRY] Roll: {roll_no} | Subject: {subj} | Period: {per_id} | Time: {now.strftime('%H:%M')}")
            self._add_log({
                'type': 'ENTRY', 'name': name,
                'subject': subj, 'period': per_id,
                'time': now.strftime('%H:%M')
            })
        elif has_gatepass:
            status = "Present (Excused)"
            logger.info(f"[EXCUSED LATE] Roll: {roll_no} | Subject: {subj} | Time: {now.strftime('%H:%M')}")
            self._add_log({
                'type': 'EXCUSED LATE', 'name': name,
                'subject': subj, 'period': per_id,
                'time': now.strftime('%H:%M')
            })
        else:
            status = "Late"
            logger.info(f"[LATE] Roll: {roll_no} | Subject: {subj} | Time: {now.strftime('%H:%M')}")
            self._add_log({
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
        
    def confirm_exit(self, roll_no: str):
        """Called by UI when user clicks 'OK' to confirm exit."""
        with self.lock:
            if roll_no in self.pending_exits:
                now = datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                student = self.pending_exits[roll_no]
                
                logger.info(f"[EXIT CONFIRMED] Roll: {roll_no} | Time: {now.strftime('%H:%M')}")
                self._add_log({
                    'type': 'EXIT', 'name': student['name'],
                    'subject': student.get('current_subject', ''),
                    'period': student.get('current_period', ''),
                    'time': now.strftime('%H:%M')
                })
                # Mark exit time in ERP
                subj = student.get('current_subject', '')
                per = student.get('current_period', '')
                try:
                    if (date_str in self.erp_data and 
                        subj in self.erp_data[date_str] and 
                        per in self.erp_data[date_str][subj] and 
                        roll_no in self.erp_data[date_str][subj][per]):
                            self.erp_data[date_str][subj][per][roll_no]['exit_time'] = now.strftime('%H:%M')
                            self.erp_data[date_str][subj][per][roll_no]['status'] = "Exited"
                            self.save_data()
                except Exception as e:
                    logger.error(f"Failed to update ERP exit time: {e}")
                
                if roll_no in self.active_students:
                    del self.active_students[roll_no]
                del self.pending_exits[roll_no]

                # Sync the Exited status to data.json so Reports page can see it
                try:
                    day_str = now.strftime("%A")
                    self._sync_to_app_period_attendance(date_str, day_str, subj, per, roll_no, "Exited")
                except Exception as e:
                    logger.error(f"Failed to sync exit to data.json: {e}")
                
                # We do NOT process as new entry recursively here because this is just an explicit exit.

    def cancel_exit(self, roll_no: str):
        """Called by UI when user clicks 'Cancel' or ignores exit."""
        with self.lock:
            if roll_no in self.pending_exits:
                del self.pending_exits[roll_no]
            if roll_no in self.active_students:
                # Update last_seen so they don't immediately trigger another pending exit
                self.active_students[roll_no]['last_seen'] = datetime.now()

    def _sync_to_app_period_attendance(self, date_str: str, day_str: str, subj: str, per_id: str, roll_no: str, status: str):
        """
        BRIDGE: Sync AI recognition event into the app's period_attendance format
        stored in data.json so the Reports page can read it directly.
        
        Uses a dedicated file-level lock (_data_file_lock) that is SEPARATE from
        self.lock to avoid deadlocks: self.lock protects in-memory state;
        _data_file_lock protects data.json I/O.
        """
        try:
            data_path = Path("data.json")
            with self._data_file_lock:  # File I/O lock — does NOT nest inside self.lock
                # Load current data.json
                app_data = {"students": [], "period_attendance": [], "timetable": {}}
                for _ in range(5):
                    if data_path.exists():
                        try:
                            with open(data_path, 'r') as f:
                                app_data = json.load(f)
                            break
                        except Exception:
                            time.sleep(0.1)
                    else:
                        break

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

                if "attendance" not in existing_record:
                    existing_record["attendance"] = {}

                current_status = existing_record["attendance"].get(roll_no)

                # Priority logic: never downgrade a confirmed high-priority status
                HIGH_PRIORITY = {"Present", "Present (Excused)", "Auto-Carried", "Exited"}
                should_update = True
                if current_status in HIGH_PRIORITY:
                    if status in ["Late", "Absent"]:
                        should_update = False

                if should_update:
                    existing_record["attendance"][roll_no] = status

                # Save back to data.json
                app_data["period_attendance"] = period_attendance
                for attempt in range(15):
                    try:
                        with open(data_path, 'w') as f:
                            json.dump(app_data, f, indent=2)
                        break
                    except Exception as e:
                        if attempt == 14:
                            logger.error(f"[SYNC ERROR] Completely failed to write data.json after retries: {e}")
                        time.sleep(0.2)

            logger.info(f"[SYNC] Saved to period_attendance: {roll_no}={status} | {subj} {per_id} on {date_str}")
        except Exception as e:
            logger.error(f"[SYNC ERROR] Failed to sync to app period_attendance: {e}")

    def trigger_auto_transition(self):
        """
        RULE 8 - VERIFIED AUTO PERIOD TRANSITION
        Instead of blind auto-carry, put them in a pending queue for Teacher Verification via UI.
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
                    # Put in pending auto carry queue instead of blind transition
                    if roll_no not in self.pending_auto_carries:
                        logger.info(f"[PENDING AUTO_CARRY] Roll: {roll_no} | New Period: {per_id}")
                        self.pending_auto_carries[roll_no] = {
                            'name': student['name'],
                            'new_subject': subj,
                            'new_period': per_id
                        }

    def confirm_auto_carry(self, roll_no: str):
        """Called by UI when teacher verifies the student is actually in the room."""
        with self.lock:
            if roll_no in self.pending_auto_carries and roll_no in self.active_students:
                now = datetime.now()
                date_str = now.strftime("%Y-%m-%d")
                
                carry_info = self.pending_auto_carries[roll_no]
                subj = carry_info['new_subject']
                per_id = carry_info['new_period']
                student = self.active_students[roll_no]
                
                student['current_subject'] = subj
                student['current_period'] = per_id
                
                record = {
                    "name": student['name'],
                    "status": "Auto-Carried",
                    "entry_time": now.strftime('%H:%M'),
                    "exit_time": None,
                    "method": "Verified Presence"
                }
                self._mark_erp_attendance(date_str, subj, per_id, roll_no, record)
                
                day_str = now.strftime("%A")
                self._sync_to_app_period_attendance(date_str, day_str, subj, per_id, roll_no, "Present")
                logger.info(f"[VERIFIED AUTO_CARRY] Roll: {roll_no} | New Period: {per_id}")
                
                self._add_log({
                    'type': 'AUTO-CARRY', 'name': student['name'],
                    'subject': subj, 'period': per_id,
                    'time': now.strftime('%H:%M')
                })
                
                del self.pending_auto_carries[roll_no]

    def cancel_auto_carry(self, roll_no: str):
        """Called by UI when teacher marks student absent (anti-bunking)."""
        with self.lock:
            if roll_no in self.pending_auto_carries:
                logger.info(f"[CANCELLED AUTO_CARRY] Roll: {roll_no} | Marked Absent.")
                if roll_no in self.active_students:
                    # They vanished, so remove from active students.
                    now = datetime.now()
                    date_str = now.strftime("%Y-%m-%d")
                    student = self.active_students[roll_no]
                    
                    old_subj = student.get('current_subject', '')
                    old_per = student.get('current_period', '')
                    
                    self._add_log({
                        'type': 'EXIT', 'name': student['name'],
                        'subject': old_subj, 'period': old_per,
                        'time': now.strftime('%H:%M')
                    })
                    
                    try:
                        if date_str in self.erp_data and old_subj in self.erp_data[date_str] and old_per in self.erp_data[date_str][old_subj]:
                            if roll_no in self.erp_data[date_str][old_subj][old_per]:
                                self.erp_data[date_str][old_subj][old_per][roll_no]['exit_time'] = now.strftime('%H:%M')
                                self.erp_data[date_str][old_subj][old_per][roll_no]['status'] = "Exited (Unverified)"
                                self.save_data()
                    except Exception as e:
                        pass
                    
                    del self.active_students[roll_no]
                
                del self.pending_auto_carries[roll_no]

    def get_attendance_summary(self) -> Dict[str, Any]:
        """Returns today's attendance summary for the live UI."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        total_records = 0
        
        if date_str in self.erp_data:
            for subject, periods in self.erp_data[date_str].items():
                for period, records in periods.items():
                    total_records += len(records)
                    
        return {"total_records": total_records}
        
    def get_active_students_summary(self) -> Dict[str, Any]:
        """Returns currently active students for the live UI."""
        with self.lock:
            students = [{"name": s["name"]} for s in self.active_students.values()]
            return {"count": len(students), "students": students}
