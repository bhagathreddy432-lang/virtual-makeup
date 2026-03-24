import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Load cascades
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# ── FACE TRACKING SMOOTHER ──
# Stores previous face rect to stabilise jittery detection
_prev_face = None
_no_face_count = 0
SMOOTHING = 0.35   # 0=instant, 1=frozen. 0.35 = snappy but smooth

def smooth_face(new_face):
    global _prev_face, _no_face_count
    if new_face is None:
        _no_face_count += 1
        if _no_face_count > 4:          # only clear after 4 misses in a row
            _prev_face = None
        return _prev_face
    _no_face_count = 0
    if _prev_face is None:
        _prev_face = new_face
        return new_face
    # Exponential moving average on x,y,w,h
    sx = int(_prev_face[0] * SMOOTHING + new_face[0] * (1 - SMOOTHING))
    sy = int(_prev_face[1] * SMOOTHING + new_face[1] * (1 - SMOOTHING))
    sw = int(_prev_face[2] * SMOOTHING + new_face[2] * (1 - SMOOTHING))
    sh = int(_prev_face[3] * SMOOTHING + new_face[3] * (1 - SMOOTHING))
    _prev_face = (sx, sy, sw, sh)
    return _prev_face

# ── PRODUCTS ──
PRODUCTS = [
    {"brand": "MAC", "name": "Ruby Woo",       "category": "Lipstick", "shade": "#CC0000", "skin_tones": ["Very Fair", "Fair"],            "price": "$19"},
    {"brand": "MAC", "name": "Velvet Teddy",   "category": "Lipstick", "shade": "#C4607A", "skin_tones": ["Medium", "Olive"],              "price": "$19"},
    {"brand": "MAC", "name": "Chili",          "category": "Lipstick", "shade": "#A0522D", "skin_tones": ["Tan/Brown", "Dark"],            "price": "$19"},
    {"brand": "MAC", "name": "Whirl",          "category": "Lipstick", "shade": "#8B6F6F", "skin_tones": ["Fair", "Medium"],              "price": "$19"},
    {"brand": "MAC", "name": "Mehr",           "category": "Lipstick", "shade": "#D4748C", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$19"},
    {"brand": "MAC", "name": "Lady Danger",    "category": "Lipstick", "shade": "#FF4500", "skin_tones": ["Olive", "Tan/Brown"],          "price": "$19"},
    {"brand": "MAC", "name": "Diva",           "category": "Lipstick", "shade": "#800020", "skin_tones": ["Dark", "Tan/Brown"],           "price": "$19"},
    {"brand": "MAC", "name": "Candy Yum-Yum",  "category": "Lipstick", "shade": "#FF6B8A", "skin_tones": ["Very Fair", "Fair"],           "price": "$19"},
    {"brand": "MAC", "name": "Heroine",        "category": "Lipstick", "shade": "#7B3F7B", "skin_tones": ["Dark", "Olive"],               "price": "$19"},
    {"brand": "MAC", "name": "Twig",           "category": "Lipstick", "shade": "#B87F7F", "skin_tones": ["Medium", "Olive"],             "price": "$19"},
    {"brand": "MAC", "name": "Honeylove",      "category": "Lipstick", "shade": "#D4A896", "skin_tones": ["Very Fair", "Fair"],           "price": "$19"},
    {"brand": "MAC", "name": "Taupe",          "category": "Lipstick", "shade": "#9E8080", "skin_tones": ["Medium", "Olive"],             "price": "$19"},
    {"brand": "NARS", "name": "Jungle Red",    "category": "Lipstick", "shade": "#CC2200", "skin_tones": ["Very Fair", "Fair"],           "price": "$26"},
    {"brand": "NARS", "name": "Schiap",        "category": "Lipstick", "shade": "#FF69B4", "skin_tones": ["Very Fair", "Fair"],           "price": "$26"},
    {"brand": "NARS", "name": "Heat Wave",     "category": "Lipstick", "shade": "#FF6347", "skin_tones": ["Medium", "Olive"],             "price": "$26"},
    {"brand": "NARS", "name": "Dolce Vita",    "category": "Lipstick", "shade": "#C08080", "skin_tones": ["Fair", "Medium"],             "price": "$26"},
    {"brand": "NARS", "name": "Dragon Girl",   "category": "Lipstick", "shade": "#FF0000", "skin_tones": ["Tan/Brown", "Dark"],           "price": "$26"},
    {"brand": "NARS", "name": "Cruella",       "category": "Lipstick", "shade": "#8B0000", "skin_tones": ["Dark", "Tan/Brown"],          "price": "$26"},
    {"brand": "NARS", "name": "Volga",         "category": "Lipstick", "shade": "#FFB6C1", "skin_tones": ["Very Fair"],                  "price": "$26"},
    {"brand": "NARS", "name": "Rikugien",      "category": "Lipstick", "shade": "#D2691E", "skin_tones": ["Olive", "Medium"],            "price": "$26"},
    {"brand": "NARS", "name": "Red Square",    "category": "Lipstick", "shade": "#B22222", "skin_tones": ["Medium", "Olive", "Tan/Brown"],"price": "$26"},
    {"brand": "L'Oreal", "name": "Pure Red",   "category": "Lipstick", "shade": "#FF0000", "skin_tones": ["Very Fair", "Fair", "Medium"],"price": "$11"},
    {"brand": "L'Oreal", "name": "Spice",      "category": "Lipstick", "shade": "#A0522D", "skin_tones": ["Tan/Brown", "Dark"],          "price": "$11"},
    {"brand": "L'Oreal", "name": "Nude Beige", "category": "Lipstick", "shade": "#D4B5A0", "skin_tones": ["Very Fair", "Fair"],          "price": "$11"},
    {"brand": "L'Oreal", "name": "Cocoa",      "category": "Lipstick", "shade": "#6B4226", "skin_tones": ["Dark", "Tan/Brown"],          "price": "$11"},
    {"brand": "L'Oreal", "name": "Rose Quartz","category": "Lipstick", "shade": "#F4A8B0", "skin_tones": ["Fair", "Medium"],             "price": "$11"},
    {"brand": "Maybelline","name": "Red Revival","category":"Lipstick", "shade": "#CC0000", "skin_tones": ["Very Fair", "Fair", "Medium"],"price": "$9"},
    {"brand": "Maybelline","name": "Nude Flush","category": "Lipstick","shade": "#E8B4A0", "skin_tones": ["Very Fair", "Fair"],           "price": "$9"},
    {"brand": "Maybelline","name": "Berry Bossy","category":"Lipstick","shade": "#8B1A4A", "skin_tones": ["Olive", "Tan/Brown", "Dark"],  "price": "$9"},
    {"brand": "Maybelline","name": "Pink Fling","category": "Lipstick","shade": "#FF8DA1", "skin_tones": ["Very Fair", "Fair"],           "price": "$9"},
    {"brand": "Maybelline","name": "Caramel Kiss","category":"Lipstick","shade":"#C68E5A", "skin_tones": ["Medium", "Olive"],             "price": "$9"},
    {"brand": "Maybelline","name": "Dusty Rose","category": "Lipstick","shade": "#C4A0A0", "skin_tones": ["Fair", "Medium"],             "price": "$9"},
    {"brand": "MAC", "name": "Fleur Power",    "category": "Blush",    "shade": "#FFB7C5", "skin_tones": ["Very Fair", "Fair"],          "price": "$25"},
    {"brand": "MAC", "name": "Warm Soul",      "category": "Blush",    "shade": "#E88080", "skin_tones": ["Medium", "Olive"],            "price": "$25"},
    {"brand": "MAC", "name": "Raizin",         "category": "Blush",    "shade": "#DDA0DD", "skin_tones": ["Tan/Brown", "Dark"],          "price": "$25"},
    {"brand": "MAC", "name": "Desert Rose",    "category": "Blush",    "shade": "#FF9999", "skin_tones": ["Fair", "Medium"],            "price": "$25"},
    {"brand": "MAC", "name": "Peaches",        "category": "Blush",    "shade": "#F4A460", "skin_tones": ["Very Fair", "Fair"],          "price": "$25"},
    {"brand": "NARS", "name": "Orgasm",        "category": "Blush",    "shade": "#FF8C69", "skin_tones": ["Very Fair", "Fair", "Medium"],"price": "$30"},
    {"brand": "NARS", "name": "Deep Throat",   "category": "Blush",    "shade": "#FFD1DC", "skin_tones": ["Very Fair", "Fair"],          "price": "$30"},
    {"brand": "NARS", "name": "Taj Mahal",     "category": "Blush",    "shade": "#FF69B4", "skin_tones": ["Olive", "Tan/Brown"],         "price": "$30"},
    {"brand": "NARS", "name": "Luster",        "category": "Blush",    "shade": "#FFB7C5", "skin_tones": ["Medium", "Fair"],            "price": "$30"},
    {"brand": "NARS", "name": "Desire",        "category": "Blush",    "shade": "#E88080", "skin_tones": ["Dark", "Tan/Brown"],         "price": "$30"},
    {"brand": "NARS", "name": "Bahama",        "category": "Blush",    "shade": "#F4A460", "skin_tones": ["Dark", "Tan/Brown"],         "price": "$30"},
    {"brand": "L'Oreal","name": "Soft Rose",   "category": "Blush",    "shade": "#FFD1DC", "skin_tones": ["Very Fair", "Fair"],          "price": "$12"},
    {"brand": "L'Oreal","name": "Peach Amber", "category": "Blush",    "shade": "#F4A460", "skin_tones": ["Medium", "Olive"],           "price": "$12"},
    {"brand": "L'Oreal","name": "Pink Coral",  "category": "Blush",    "shade": "#FF8C69", "skin_tones": ["Fair", "Medium"],            "price": "$12"},
    {"brand": "L'Oreal","name": "Blushing Berry","category":"Blush",   "shade": "#DDA0DD", "skin_tones": ["Dark"],                      "price": "$12"},
    {"brand": "Maybelline","name":"Pink Amber", "category": "Blush",   "shade": "#FF9999", "skin_tones": ["Very Fair", "Fair"],          "price": "$10"},
    {"brand": "Maybelline","name":"Coral Crush","category": "Blush",   "shade": "#E88080", "skin_tones": ["Medium", "Olive", "Tan/Brown"],"price":"$10"},
    {"brand": "Maybelline","name":"Berry Chic", "category": "Blush",   "shade": "#DDA0DD", "skin_tones": ["Dark", "Tan/Brown"],          "price": "$10"},
    {"brand": "MAC", "name": "Bronzing Powder","category": "Bronzer",  "shade": "#C68642", "skin_tones": ["Very Fair", "Fair", "Medium"],"price": "$30"},
    {"brand": "MAC", "name": "Refined Golden", "category": "Bronzer",  "shade": "#D4A043", "skin_tones": ["Olive", "Tan/Brown"],         "price": "$30"},
    {"brand": "MAC", "name": "Give Me Sun",    "category": "Bronzer",  "shade": "#B8860B", "skin_tones": ["Dark", "Tan/Brown"],          "price": "$30"},
    {"brand": "NARS", "name": "Laguna",        "category": "Bronzer",  "shade": "#C68E5A", "skin_tones": ["Very Fair", "Fair", "Medium"],"price": "$38"},
    {"brand": "NARS", "name": "Casino",        "category": "Bronzer",  "shade": "#A0785A", "skin_tones": ["Olive", "Tan/Brown", "Dark"], "price": "$38"},
    {"brand": "NARS", "name": "Copacabana",    "category": "Bronzer",  "shade": "#D4A55A", "skin_tones": ["Fair", "Medium"],            "price": "$38"},
    {"brand": "L'Oreal","name":"True Match",   "category": "Bronzer",  "shade": "#C9956C", "skin_tones": ["Very Fair", "Fair"],          "price": "$14"},
    {"brand": "L'Oreal","name":"Glam Bronze",  "category": "Bronzer",  "shade": "#B5743C", "skin_tones": ["Medium", "Olive", "Tan/Brown"],"price":"$14"},
    {"brand": "Maybelline","name":"City Bronze","category":"Bronzer",   "shade": "#C68642", "skin_tones": ["Very Fair", "Fair", "Medium"],"price": "$11"},
    {"brand": "Maybelline","name":"Amber Rush", "category":"Bronzer",   "shade": "#A07850", "skin_tones": ["Olive", "Tan/Brown", "Dark"], "price": "$11"},
]

# ── HELPERS ──
def hex_to_bgr(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return (b, g, r)

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
        y1, y2 = int(h*0.05), int(h*0.22)
        x1, x2 = int(w*0.25), int(w*0.75)
        forehead = face_img[y1:y2, x1:x2]
        if forehead.size == 0:
            return "Medium", 20.0
        lab = cv2.cvtColor(forehead, cv2.COLOR_BGR2LAB)
        avg = np.mean(lab.reshape(-1, 3), axis=0)
        L_star = (avg[0] / 255.0) * 100.0
        b_star  = avg[2] - 128.0
        if abs(b_star) < 1e-6: b_star = 1e-6
        ita = np.arctan((L_star - 50.0) / b_star) * (180.0 / np.pi)
        return classify_skin_tone(ita), round(float(ita), 2)
    except Exception:
        return "Medium", 20.0

def apply_lipstick(img, fx, fy, fw, fh, eyes, color_bgr, opacity):
    overlay = img.copy()
    if eyes is not None and len(eyes) >= 1:
        eye_bottom = max(ey + eh for (ex, ey, ew, eh) in eyes)
        lip_y = fy + eye_bottom + int((fh - eye_bottom) * 0.58)
    else:
        lip_y = fy + int(fh * 0.80)

    cx    = fx + fw // 2
    lip_w = int(fw * 0.36)
    lip_h = int(fh * 0.060)

    # Lower lip
    cv2.ellipse(overlay, (cx, lip_y), (lip_w, lip_h), 0, 0, 360, color_bgr, -1)
    # Upper lip cupid bow
    cv2.ellipse(overlay, (cx, lip_y - lip_h), (lip_w, lip_h), 0, 180, 360, color_bgr, -1)
    # Soften edges
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.ellipse(mask, (cx, lip_y), (lip_w, lip_h), 0, 0, 360, 255, -1)
    cv2.ellipse(mask, (cx, lip_y - lip_h), (lip_w, lip_h), 0, 180, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (11, 11), 4)

    blended = cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0)
    # Apply only on lip mask region for clean edges
    result = img.copy()
    alpha  = mask.astype(float) / 255.0
    for c in range(3):
        result[:, :, c] = (blended[:, :, c] * alpha + img[:, :, c] * (1 - alpha)).astype(np.uint8)
    return result

def apply_blush(img, fx, fy, fw, fh, color_bgr, opacity):
    lx = fx + int(fw * 0.18)
    rx = fx + int(fw * 0.82)
    cy = fy + int(fh * 0.58)
    rad = int(fw * 0.17)

    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    cv2.circle(mask, (lx, cy), rad, 255, -1)
    cv2.circle(mask, (rx, cy), rad, 255, -1)
    mask = cv2.GaussianBlur(mask, (61, 61), 22)

    overlay = img.copy()
    overlay[mask > 0] = color_bgr
    alpha = (mask.astype(float) / 255.0) * opacity * 0.55
    result = img.copy()
    for c in range(3):
        result[:, :, c] = (overlay[:, :, c] * alpha + img[:, :, c] * (1 - alpha)).astype(np.uint8)
    return result

def apply_eyeshadow(img, fx, fy, fw, fh, eyes, color_bgr, opacity):
    if not eyes or len(eyes) == 0:
        return img
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for (ex, ey, ew, eh) in eyes:
        ax = fx + ex + ew // 2
        ay = fy + ey + int(eh * 0.25)
        cv2.ellipse(mask, (ax, ay), (int(ew * 0.65), int(eh * 0.5)), 0, 0, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (25, 25), 9)

    overlay = img.copy()
    overlay[mask > 0] = color_bgr
    alpha = (mask.astype(float) / 255.0) * opacity * 0.5
    result = img.copy()
    for c in range(3):
        result[:, :, c] = (overlay[:, :, c] * alpha + img[:, :, c] * (1 - alpha)).astype(np.uint8)
    return result

# ── ROUTES ──
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({"status": "ok", "message": "GlowAI v2 running"})

@app.route('/process_frame', methods=['POST'])
def process_frame():
    try:
        data      = request.get_json(force=True)
        img_b64   = data.get('image', '')
        settings  = data.get('settings', {})

        if ',' in img_b64:
            img_b64 = img_b64.split(',')[1]
        img_bytes = base64.b64decode(img_b64)
        np_arr    = np.frombuffer(img_bytes, np.uint8)
        img       = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "bad image"}), 400

        # Sharpen input slightly for better detection
        kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
        img_sharp = cv2.filter2D(img, -1, kernel)

        gray  = cv2.cvtColor(img_sharp, cv2.COLOR_BGR2GRAY)
        gray  = cv2.equalizeHist(gray)  # improve contrast for detection

        raw_faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.05,    # finer scale steps → catches more faces
            minNeighbors=6,      # higher = less false positives
            minSize=(80, 80),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        pipeline = {k: False for k in
                    ["face_detection","landmark_extraction","skin_tone","makeup_application","recommendations"]}

        raw_face  = raw_faces[0] if len(raw_faces) > 0 else None
        face_rect = smooth_face(tuple(raw_face) if raw_face is not None else None)
        skin_tone = None
        ita_val   = None

        if face_rect:
            pipeline["face_detection"] = True
            fx, fy, fw, fh = face_rect

            # Clamp to image bounds
            fx = max(0, fx); fy = max(0, fy)
            fw = min(fw, img.shape[1] - fx)
            fh = min(fh, img.shape[0] - fy)

            face_gray = gray[fy:fy+fh, fx:fx+fw]
            eyes = eye_cascade.detectMultiScale(
                face_gray,
                scaleFactor=1.1,
                minNeighbors=4,
                minSize=(int(fw*0.1), int(fh*0.08))
            )
            pipeline["landmark_extraction"] = True

            face_img  = img[fy:fy+fh, fx:fx+fw]
            skin_tone, ita_val = get_skin_tone(face_img)
            pipeline["skin_tone"] = True

            opacity = float(settings.get('opacity', 0.5))
            eyes_list = list(eyes) if len(eyes) > 0 else None

            if settings.get('lipstick'):
                img = apply_lipstick(img, fx, fy, fw, fh, eyes_list,
                                     hex_to_bgr(settings.get('lip_color','#C4607A')), opacity)
            if settings.get('blush'):
                img = apply_blush(img, fx, fy, fw, fh,
                                  hex_to_bgr(settings.get('blush_color','#FFB7C5')), opacity)
            if settings.get('eyeshadow'):
                img = apply_eyeshadow(img, fx, fy, fw, fh, eyes_list,
                                      hex_to_bgr(settings.get('eye_color','#B46482')), opacity)

            pipeline["makeup_application"] = True
            pipeline["recommendations"]    = True

            # Subtle face border — just corners, premium feel
            c = (196, 96, 122)
            t = 2; cs = 18
            cv2.line(img,(fx,fy),(fx+cs,fy),c,t); cv2.line(img,(fx,fy),(fx,fy+cs),c,t)
            cv2.line(img,(fx+fw,fy),(fx+fw-cs,fy),c,t); cv2.line(img,(fx+fw,fy),(fx+fw,fy+cs),c,t)
            cv2.line(img,(fx,fy+fh),(fx+cs,fy+fh),c,t); cv2.line(img,(fx,fy+fh),(fx,fy+fh-cs),c,t)
            cv2.line(img,(fx+fw,fy+fh),(fx+fw-cs,fy+fh),c,t); cv2.line(img,(fx+fw,fy+fh),(fx+fw,fy+fh-cs),c,t)

        # Output at high quality — 90 JPEG
        _, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        b64_out = base64.b64encode(buf).decode('utf-8')

        return jsonify({
            "processed_image": f"data:image/jpeg;base64,{b64_out}",
            "skin_tone":   skin_tone,
            "ita_value":   ita_val,
            "face_detected": face_rect is not None,
            "pipeline_steps": pipeline,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/recommendations')
def recommendations():
    tone = request.args.get('skin_tone', 'Medium')
    filtered = [p for p in PRODUCTS if tone in p.get('skin_tones', [])]
    by_cat = {}
    for p in filtered:
        by_cat.setdefault(p['category'], []).append(p)
    return jsonify({"skin_tone": tone, "products": by_cat, "total": len(filtered)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
