import json
import os

print("=== RUNNING STUDENT DATA CLEANER ===")

# Load data.json
data_path = 'data.json'
if os.path.exists(data_path):
    try:
        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Clean students list
        students = data.get('students', [])
        cleaned_count = 0
        for s in students:
            for field in ['name', 'roll_no', 'prn', 'branch', 'class']:
                if field in s and isinstance(s[field], str):
                    orig = s[field]
                    s[field] = orig.strip()
                    if s[field] != orig:
                        print(f"Cleaned {field}: {repr(orig)} -> {repr(s[field])}")
                        cleaned_count += 1
                        
        # Filter out any student entry that might be Umesh Vilas Ingole (Roll 46, AI3046, or 2)
        original_len = len(students)
        data['students'] = [
            s for s in students 
            if s.get('roll_no') not in ['46', 'AI3046', '2'] 
            and 'umesh' not in str(s.get('name', '')).lower()
        ]
        removed_len = original_len - len(data['students'])
        if removed_len > 0:
            print(f"Removed {removed_len} old Umesh student record(s) from students list.")

        # Clean period_attendance list
        pa = data.get('period_attendance', [])
        cleaned_pa = []
        for r in pa:
            att = r.get('attendance', {})
            # Remove any keys in attendance dict matching the old roll numbers of Umesh
            cleaned_att = {
                k: v for k, v in att.items()
                if k not in ['46', 'AI3046', '2']
            }
            if len(cleaned_att) != len(att):
                print(f"Cleaned attendance for date={r.get('date')} period={r.get('period')} subject={r.get('subject')}")
            r['attendance'] = cleaned_att
            cleaned_pa.append(r)
        data['period_attendance'] = cleaned_pa

        # Write back data.json
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"SUCCESS: data.json cleaned and written back. Cleaned fields: {cleaned_count}")
    except Exception as e:
        print("Error cleaning data.json:", e)
else:
    print("data.json not found!")

# Clean face_embeddings.pkl
pkl_path = 'data/face_embeddings.pkl'
if os.path.exists(pkl_path):
    try:
        import pickle
        with open(pkl_path, 'rb') as f:
            emb = pickle.load(f)
        
        orig_keys = list(emb.keys())
        # Remove any keys representing Umesh
        cleaned_emb = {
            k: v for k, v in emb.items()
            if k not in ['46', 'AI3046', '2']
        }
        if len(cleaned_emb) != len(emb):
            removed_keys = [k for k in orig_keys if k not in cleaned_emb]
            with open(pkl_path, 'wb') as f:
                pickle.load = pickle.dump(cleaned_emb, f)
            print(f"Cleaned face_embeddings.pkl. Removed keys: {removed_keys}")
        else:
            print("face_embeddings.pkl is already clean.")
    except Exception as e:
        print("Error cleaning face_embeddings.pkl:", e)
else:
    print("face_embeddings.pkl not found!")

# Clean dataset directories
dataset_path = 'dataset'
if os.path.exists(dataset_path):
    try:
        import shutil
        for folder in os.listdir(dataset_path):
            folder_lower = folder.lower()
            if any(term in folder_lower for term in ['umesh', '46', 'ai3046']):
                dir_to_remove = os.path.join(dataset_path, folder)
                shutil.rmtree(dir_to_remove)
                print(f"Removed Umesh dataset folder: {folder}")
    except Exception as e:
        print("Error cleaning dataset directories:", e)
else:
    print("dataset directory not found!")
