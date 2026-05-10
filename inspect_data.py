import json
import pickle
import os

print("--- INSPECTING data.json ---")
try:
    with open('data.json', 'r', encoding='utf-8') as f:
        d = json.load(f)
    print("Keys in data.json:", list(d.keys()))
    students = d.get('students', [])
    print("Students count:", len(students))
    for s in students:
        print(f"  Roll={repr(s.get('roll_no'))} Name={repr(s.get('name'))} PRN={repr(s.get('prn'))}")
    
    # Check attendance
    pa = d.get('period_attendance', [])
    print("Period attendance records:", len(pa))
    for i, r in enumerate(pa):
        att = r.get('attendance', {})
        matched_keys = [k for k in att.keys() if k in ['46', 'AI3046', '2'] or 'umesh' in str(att.get(k)).lower()]
        if matched_keys:
            print(f"  [{i}] {r.get('date')} | {r.get('period')} | {r.get('subject')} contains keys: {matched_keys} -> { {k: att[k] for k in matched_keys} }")
except Exception as e:
    print("Error reading data.json:", e)

print("\n--- INSPECTING data/erp_attendance.json ---")
erp_path = 'data/erp_attendance.json'
if os.path.exists(erp_path):
    try:
        with open(erp_path, 'r', encoding='utf-8') as f:
            erp = json.load(f)
        print("ERP records count:", len(erp))
        # ERP records are usually a list of logs or dict
        # Let's see structure
        if erp:
            print("ERP first record keys/structure:", erp[0] if isinstance(erp, list) else list(erp.keys())[:5])
            # search for Umesh
            matched_erp = []
            if isinstance(erp, list):
                for j, entry in enumerate(erp):
                    entry_str = json.dumps(entry).lower()
                    if any(term in entry_str for term in ['46', 'ai3046', 'umesh']):
                        matched_erp.append((j, entry))
            print(f"Matched ERP records containing Umesh/46/AI3046: {len(matched_erp)}")
            for idx, m in matched_erp[:10]:
                print(f"  [{idx}] {m}")
    except Exception as e:
        print("Error reading erp_attendance.json:", e)
else:
    print("erp_attendance.json does not exist at", erp_path)

print("\n--- INSPECTING data/face_embeddings.pkl ---")
pkl_path = 'data/face_embeddings.pkl'
if os.path.exists(pkl_path):
    try:
        with open(pkl_path, 'rb') as f:
            emb = pickle.load(f)
        print("Embeddings keys:", list(emb.keys()))
    except Exception as e:
        print("Error reading face_embeddings.pkl:", e)
else:
    print("face_embeddings.pkl does not exist at", pkl_path)
