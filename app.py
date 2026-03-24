import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# ── Face smoothing state ──
_prev_face   = None
_no_face_cnt = 0

def smooth_face(new_face):
    global _prev_face, _no_face_cnt
    if new_face is None:
        _no_face_cnt += 1
        if _no_face_cnt > 5:
            _prev_face = None
        return _prev_face
    _no_face_cnt = 0
    if _prev_face is None:
        _prev_face = new_face
        return new_face
    a = 0.35
    _prev_face = {k: _prev_face[k]*a + new_face[k]*(1-a) for k in ('fx','fy','fw','fh')}
    _prev_face['eyes'] = new_face['eyes']
    return _prev_face

# ── PRODUCTS ──
PRODUCTS = [
    {"brand": "MAC",       "name": "Ruby Woo",       "category": "Lipstick", "shade": "#CC0000", "skin_tones": ["Very Fair","Fair"],              "price": "$19"},
    {"brand": "MAC",       "name": "Velvet Teddy",   "category": "Lipstick", "shade": "#C4607A", "skin_tones": ["Medium","Olive"],                "price": "$19"},
    {"brand": "MAC",       "name": "Chili",          "category": "Lipstick", "shade": "#A0522D", "skin_tones": ["Tan/Brown","Dark"],              "price": "$19"},
    {"brand": "MAC",       "name": "Whirl",          "category": "Lipstick", "shade": "#8B6F6F", "skin_tones": ["Fair","Medium"],                "price": "$19"},
    {"brand": "MAC",       "name": "Mehr",           "category": "Lipstick", "shade": "#D4748C", "skin_tones": ["Very Fair","Fair","Medium"],     "price": "$19"},
    {"brand": "MAC",       "name": "Lady Danger",    "category": "Lipstick", "shade": "#FF4500", "skin_tones": ["Olive","Tan/Brown"],             "price": "$19"},
    {"brand": "MAC",       "name": "Diva",           "category": "Lipstick", "shade": "#800020", "skin_tones": ["Dark","Tan/Brown"],              "price": "$19"},
    {"brand": "MAC",       "name": "Candy Yum-Yum",  "category": "Lipstick", "shade": "#FF6B8A", "skin_tones": ["Very Fair","Fair"],              "price": "$19"},
    {"brand": "MAC",       "name": "Heroine",        "category": "Lipstick", "shade": "#7B3F7B", "skin_tones": ["Dark","Olive"],                  "price": "$19"},
    {"brand": "MAC",       "name": "Twig",           "category": "Lipstick", "shade": "#B87F7F", "skin_tones": ["Medium","Olive"],                "price": "$19"},
    {"brand": "MAC",       "name": "Honeylove",      "category": "Lipstick", "shade": "#D4A896", "skin_tones": ["Very Fair","Fair"],              "price": "$19"},
    {"brand": "MAC",       "name": "Taupe",          "category": "Lipstick", "shade": "#9E8080", "skin_tones": ["Medium","Olive"],                "price": "$19"},
    {"brand": "NARS",      "name": "Jungle Red",     "category": "Lipstick", "shade": "#CC2200", "skin_tones": ["Very Fair","Fair"],              "price": "$26"},
    {"brand": "NARS",      "name": "Schiap",         "category": "Lipstick", "shade": "#FF69B4", "skin_tones": ["Very Fair","Fair"],              "price": "$26"},
    {"brand": "NARS",      "name": "Heat Wave",      "category": "Lipstick", "shade": "#FF6347", "skin_tones": ["Medium","Olive"],                "price": "$26"},
    {"brand": "NARS",      "name": "Dolce Vita",     "category": "Lipstick", "shade": "#C08080", "skin_tones": ["Fair","Medium"],                "price": "$26"},
    {"brand": "NARS",      "name": "Dragon Girl",    "category": "Lipstick", "shade": "#FF0000", "skin_tones": ["Tan/Brown","Dark"],              "price": "$26"},
    {"brand": "NARS",      "name": "Cruella",        "category": "Lipstick", "shade": "#8B0000", "skin_tones": ["Dark","Tan/Brown"],              "price": "$26"},
    {"brand": "NARS",      "name": "Volga",          "category": "Lipstick", "shade": "#FFB6C1", "skin_tones": ["Very Fair"],                    "price": "$26"},
    {"brand": "NARS",      "name": "Rikugien",       "category": "Lipstick", "shade": "#D2691E", "skin_tones": ["Olive","Medium"],                "price": "$26"},
    {"brand": "NARS",      "name": "Red Square",     "category": "Lipstick", "shade": "#B22222", "skin_tones": ["Medium","Olive","Tan/Brown"],    "price": "$26"},
    {"brand": "L'Oreal",   "name": "Pure Red",       "category": "Lipstick", "shade": "#FF0000", "skin_tones": ["Very Fair","Fair","Medium"],     "price": "$11"},
    {"brand": "L'Oreal",   "name": "Spice",          "category": "Lipstick", "shade": "#A0522D", "skin_tones": ["Tan/Brown","Dark"],              "price": "$11"},
    {"brand": "L'Oreal",   "name": "Nude Beige",     "category": "Lipstick", "shade": "#D4B5A0", "skin_tones": ["Very Fair","Fair"],              "price": "$11"},
    {"brand": "L'Oreal",   "name": "Cocoa",          "category": "Lipstick", "shade": "#6B4226", "skin_tones": ["Dark","Tan/Brown"],              "price": "$11"},
    {"brand": "L'Oreal",   "name": "Rose Quartz",    "category": "Lipstick", "shade": "#F4A8B0", "skin_tones": ["Fair","Medium"],                "price": "$11"},
    {"brand": "Maybelline","name": "Red Revival",    "category": "Lipstick", "shade": "#CC0000", "skin_tones": ["Very Fair","Fair","Medium"],     "price": "$9"},
    {"brand": "Maybelline","name": "Nude Flush",     "category": "Lipstick", "shade": "#E8B4A0", "skin_tones": ["Very Fair","Fair"],              "price": "$9"},
    {"brand": "Maybelline","name": "Berry Bossy",    "category": "Lipstick", "shade": "#8B1A4A", "skin_tones": ["Olive","Tan/Brown","Dark"],      "price": "$9"},
    {"brand": "Maybelline","name": "Pink Fling",     "category": "Lipstick", "shade": "#FF8DA1", "skin_tones": ["Very Fair","Fair"],              "price": "$9"},
    {"brand": "Maybelline","name": "Caramel Kiss",   "category": "Lipstick", "shade": "#C68E5A", "skin_tones": ["Medium","Olive"],                "price": "$9"},
    {"brand": "Maybelline","name": "Dusty Rose",     "category": "Lipstick", "shade": "#C4A0A0", "skin_tones": ["Fair","Medium"],                "price": "$9"},
    {"brand": "MAC",       "name": "Fleur Power",    "category": "Blush",    "shade": "#FFB7C5", "skin_tones": ["Very Fair","Fair"],              "price": "$25"},
    {"brand": "MAC",       "name": "Warm Soul",      "category": "Blush",    "shade": "#E88080", "skin_tones": ["Medium","Olive"],                "price": "$25"},
    {"brand": "MAC",       "name": "Raizin",         "category": "Blush",    "shade": "#DDA0DD", "skin_tones": ["Tan/Brown","Dark"],              "price": "$25"},
    {"brand": "MAC",       "name": "Desert Rose",    "category": "Blush",    "shade": "#FF9999", "skin_tones": ["Fair","Medium"],                "price": "$25"},
    {"brand": "MAC",       "name": "Peaches",        "category": "Blush",    "shade": "#F4A460", "skin_tones": ["Very Fair","Fair"],              "price": "$25"},
    {"brand": "NARS",      "name": "Orgasm",         "category": "Blush",    "shade": "#FF8C69", "skin_tones": ["Very Fair","Fair","Medium"],     "price": "$30"},
    {"brand": "NARS",      "name": "Deep Throat",    "category": "Blush",    "shade": "#FFD1DC", "skin_tones": ["Very Fair","Fair"],              "price": "$30"},
    {"brand": "NARS",      "name": "Taj Mahal",      "category": "Blush",    "shade": "#FF69B4", "skin_tones": ["Olive","Tan/Brown"],             "price": "$30"},
    {"brand": "NARS",      "name": "Luster",         "category": "Blush",    "shade": "#FFB7C5", "skin_tones": ["Medium","Fair"],                "price": "$30"},
    {"brand": "NARS",      "name": "Desire",         "category": "Blush",    "shade": "#E88080", "skin_tones": ["Dark","Tan/Brown"],              "price": "$30"},
    {"brand": "NARS",      "name": "Bahama",         "category": "Blush",    "shade": "#F4A460", "skin_tones": ["Dark","Tan/Brown"],              "price": "$30"},
    {"brand": "L'Oreal",   "name": "Soft Rose",      "category": "Blush",    "shade": "#FFD1DC", "skin_tones": ["Very Fair","Fair"],              "price": "$12"},
    {"brand": "L'Oreal",   "name": "Peach Amber",    "category": "Blush",    "shade": "#F4A460", "skin_tones": ["Medium","Olive"],                "price": "$12"},
    {"brand": "L'Oreal",   "name": "Pink Coral",     "category": "Blush",    "shade": "#FF8C69", "skin_tones": ["Fair","Medium"],                "price": "$12"},
    {"brand": "L'Oreal",   "name": "Blushing Berry", "category": "Blush",    "shade": "#DDA0DD", "skin_tones": ["Dark"],                          "price": "$12"},
    {"brand": "Maybelline","name": "Pink Amber",     "category": "Blush",    "shade": "#FF9999", "skin_tones": ["Very Fair","Fair"],              "price": "$10"},
    {"brand": "Maybelline","name": "Coral Crush",    "category": "Blush",    "shade": "#E88080", "skin_tones": ["Medium","Olive","Tan/Brown"],    "price": "$10"},
    {"brand": "Maybelline","name": "Berry Chic",     "category": "Blush",    "shade": "#DDA0DD", "skin_tones": ["Dark","Tan/Brown"],              "price": "$10"},
    {"brand": "MAC",       "name": "Bronzing Powder","category": "Bronzer",  "shade": "#C68642", "skin_tones": ["Very Fair","Fair","Medium"],     "price": "$30"},
    {"brand": "MAC",       "name": "Refined Golden", "category": "Bronzer",  "shade": "#D4A043", "skin_tones": ["Olive","Tan/Brown"],             "price": "$30"},
    {"brand": "MAC",       "name": "Give Me Sun",    "category": "Bronzer",  "shade": "#B8860B", "skin_tones": ["Dark","Tan/Brown"],              "price": "$30"},
    {"brand": "NARS",      "name": "Laguna",         "category": "Bronzer",  "shade": "#C68E5A", "skin_tones": ["Very Fair","Fair","Medium"],     "price": "$38"},
    {"brand": "NARS",      "name": "Casino",         "category": "Bronzer",  "shade": "#A0785A", "skin_tones": ["Olive","Tan/Brown","Dark"],      "price": "$38"},
    {"brand": "NARS",      "name": "Copacabana",     "category": "Bronzer",  "shade": "#D4A55A", "skin_tones": ["Fair","Medium"],                "price": "$38"},
    {"brand": "L'Oreal",   "name": "True Match",     "category": "Bronzer",  "shade": "#C9956C", "skin_tones": ["Very Fair","Fair"],              "price": "$14"},
    {"brand": "L'Oreal",   "name": "Glam Bronze",    "category": "Bronzer",  "shade": "#B5743C", "skin_tones": ["Medium","Olive","Tan/Brown"],    "price": "$14"},
    {"brand": "Maybelline","name": "City Bronze",    "category": "Bronzer",  "shade": "#C68642", "skin_tones": ["Very Fair","Fair","Medium"],     "price": "$11"},
    {"brand": "Maybelline","name": "Amber Rush",     "category": "Bronzer",  "shade": "#A07850", "skin_tones": ["Olive","Tan/Brown","Dark"],      "price": "$11"},
]

def classify_skin_tone(ita):
    if ita > 55:  return "Very Fair"
    if ita > 41:  return "Fair"
    if ita > 28:  return "Medium"
    if ita > 10:  return "Olive"
    if ita > -30: return "Tan/Brown"
    return "Dark"

def get_skin_tone(face_img):
    try:
        h, w = face_img.shape[:2]
        region = face_img[int(h*0.05):int(h*0.22), int(w*0.25):int(w*0.75)]
        if region.size == 0: return "Medium", 20.0
        lab   = cv2.cvtColor(region, cv2.COLOR_BGR2LAB)
        avg   = np.mean(lab.reshape(-1,3), axis=0)
        L     = (avg[0]/255.0)*100.0
        b     = avg[2]-128.0
        if abs(b) < 1e-6: b = 1e-6
        ita   = np.arctan((L-50.0)/b)*(180.0/np.pi)
        return classify_skin_tone(ita), round(float(ita), 2)
    except:
        return "Medium", 20.0

# ── ROUTES ──
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({"status": "ok", "message": "GlowAI v3"})

@app.route('/detect_face', methods=['POST'])
def detect_face():
    """
    Lightweight endpoint — returns ONLY face/eye coordinates + skin tone.
    NO processed image is returned. The browser renders makeup itself.
    This keeps the camera feed at native quality.
    """
    try:
        data    = request.get_json(force=True)
        img_b64 = data.get('image','')
        if ',' in img_b64: img_b64 = img_b64.split(',')[1]
        np_arr  = np.frombuffer(base64.b64decode(img_b64), np.uint8)
        img     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None: return jsonify({"face_detected": False}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        raw_faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,
            minNeighbors=6,
            minSize=(70, 70),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        pipeline = {
            "face_detection": False, "landmark_extraction": False,
            "skin_tone": False, "makeup_application": True,
            "recommendations": False
        }

        if len(raw_faces) == 0:
            smooth_face(None)
            return jsonify({"face_detected": False, "pipeline_steps": pipeline})

        x, y, w, h = raw_faces[0]
        x = max(0, x); y = max(0, y)
        w = min(w, img.shape[1]-x); h = min(h, img.shape[0]-y)
        pipeline["face_detection"] = True

        face_gray = gray[y:y+h, x:x+w]
        eyes_raw  = eye_cascade.detectMultiScale(
            face_gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(int(w*0.08), int(h*0.06))
        )
        pipeline["landmark_extraction"] = True

        eyes_list = [{"ex": int(ex), "ey": int(ey), "ew": int(ew), "eh": int(eh)}
                     for (ex, ey, ew, eh) in eyes_raw[:2]]  # max 2 eyes

        face_img = img[y:y+h, x:x+w]
        skin_tone, ita_val = get_skin_tone(face_img)
        pipeline["skin_tone"] = True
        pipeline["recommendations"] = True

        raw = {"fx": float(x), "fy": float(y), "fw": float(w), "fh": float(h), "eyes": eyes_list}
        smoothed = smooth_face(raw)

        return jsonify({
            "face_detected":  True,
            "face":           smoothed,
            "skin_tone":      skin_tone,
            "ita_value":      ita_val,
            "pipeline_steps": pipeline,
        })
    except Exception as e:
        return jsonify({"error": str(e), "face_detected": False}), 500

# Keep old /process_frame for backward compatibility
@app.route('/process_frame', methods=['POST'])
def process_frame():
    return detect_face()

@app.route('/recommendations')
def recommendations():
    tone = request.args.get('skin_tone','Medium')
    filtered = [p for p in PRODUCTS if tone in p.get('skin_tones',[])]
    by_cat = {}
    for p in filtered:
        by_cat.setdefault(p['category'],[]).append(p)
    return jsonify({"skin_tone": tone, "products": by_cat, "total": len(filtered)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
