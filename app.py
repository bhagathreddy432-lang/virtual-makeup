import os
import cv2
import numpy as np
import base64
import json
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Load Haar Cascade classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

PRODUCTS = [
    # MAC - Lipstick
    {"brand": "MAC", "name": "Ruby Woo", "category": "Lipstick", "shade": "#CC0000", "skin_tones": ["Very Fair", "Fair"], "price": "$19"},
    {"brand": "MAC", "name": "Velvet Teddy", "category": "Lipstick", "shade": "#C4607A", "skin_tones": ["Medium", "Olive"], "price": "$19"},
    {"brand": "MAC", "name": "Chili", "category": "Lipstick", "shade": "#A0522D", "skin_tones": ["Tan/Brown", "Dark"], "price": "$19"},
    {"brand": "MAC", "name": "Whirl", "category": "Lipstick", "shade": "#8B6F6F", "skin_tones": ["Fair", "Medium"], "price": "$19"},
    {"brand": "MAC", "name": "Mehr", "category": "Lipstick", "shade": "#D4748C", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$19"},
    {"brand": "MAC", "name": "Lady Danger", "category": "Lipstick", "shade": "#FF4500", "skin_tones": ["Olive", "Tan/Brown"], "price": "$19"},
    {"brand": "MAC", "name": "Diva", "category": "Lipstick", "shade": "#800020", "skin_tones": ["Dark", "Tan/Brown"], "price": "$19"},
    {"brand": "MAC", "name": "Candy Yum-Yum", "category": "Lipstick", "shade": "#FF6B8A", "skin_tones": ["Very Fair", "Fair"], "price": "$19"},
    {"brand": "MAC", "name": "Heroine", "category": "Lipstick", "shade": "#7B3F7B", "skin_tones": ["Dark", "Olive"], "price": "$19"},
    {"brand": "MAC", "name": "Twig", "category": "Lipstick", "shade": "#B87F7F", "skin_tones": ["Medium", "Olive"], "price": "$19"},
    # NARS - Lipstick
    {"brand": "NARS", "name": "Jungle Red", "category": "Lipstick", "shade": "#CC2200", "skin_tones": ["Very Fair", "Fair"], "price": "$26"},
    {"brand": "NARS", "name": "Schiap", "category": "Lipstick", "shade": "#FF69B4", "skin_tones": ["Very Fair", "Fair"], "price": "$26"},
    {"brand": "NARS", "name": "Heat Wave", "category": "Lipstick", "shade": "#FF6347", "skin_tones": ["Medium", "Olive"], "price": "$26"},
    {"brand": "NARS", "name": "Dolce Vita", "category": "Lipstick", "shade": "#C08080", "skin_tones": ["Fair", "Medium"], "price": "$26"},
    {"brand": "NARS", "name": "Dragon Girl", "category": "Lipstick", "shade": "#FF0000", "skin_tones": ["Tan/Brown", "Dark"], "price": "$26"},
    {"brand": "NARS", "name": "Cruella", "category": "Lipstick", "shade": "#8B0000", "skin_tones": ["Dark", "Tan/Brown"], "price": "$26"},
    {"brand": "NARS", "name": "Volga", "category": "Lipstick", "shade": "#FFB6C1", "skin_tones": ["Very Fair"], "price": "$26"},
    {"brand": "NARS", "name": "Rikugien", "category": "Lipstick", "shade": "#D2691E", "skin_tones": ["Olive", "Medium"], "price": "$26"},
    # L'Oreal - Lipstick
    {"brand": "L'Oreal", "name": "Pure Red", "category": "Lipstick", "shade": "#FF0000", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$11"},
    {"brand": "L'Oreal", "name": "Spice", "category": "Lipstick", "shade": "#A0522D", "skin_tones": ["Tan/Brown", "Dark"], "price": "$11"},
    {"brand": "L'Oreal", "name": "Nude Bege", "category": "Lipstick", "shade": "#D4B5A0", "skin_tones": ["Very Fair", "Fair"], "price": "$11"},
    {"brand": "L'Oreal", "name": "Cocoa", "category": "Lipstick", "shade": "#6B4226", "skin_tones": ["Dark", "Tan/Brown"], "price": "$11"},
    {"brand": "L'Oreal", "name": "Rose Quartz", "category": "Lipstick", "shade": "#F4A8B0", "skin_tones": ["Fair", "Medium"], "price": "$11"},
    # Maybelline - Lipstick
    {"brand": "Maybelline", "name": "Red Revival", "category": "Lipstick", "shade": "#CC0000", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$9"},
    {"brand": "Maybelline", "name": "Nude Flush", "category": "Lipstick", "shade": "#E8B4A0", "skin_tones": ["Very Fair", "Fair"], "price": "$9"},
    {"brand": "Maybelline", "name": "Berry Bossy", "category": "Lipstick", "shade": "#8B1A4A", "skin_tones": ["Olive", "Tan/Brown", "Dark"], "price": "$9"},
    {"brand": "Maybelline", "name": "Pink Fling", "category": "Lipstick", "shade": "#FF8DA1", "skin_tones": ["Very Fair", "Fair"], "price": "$9"},
    {"brand": "Maybelline", "name": "Caramel Kiss", "category": "Lipstick", "shade": "#C68E5A", "skin_tones": ["Medium", "Olive"], "price": "$9"},
    # MAC - Blush
    {"brand": "MAC", "name": "Fleur Power", "category": "Blush", "shade": "#FFB7C5", "skin_tones": ["Very Fair", "Fair"], "price": "$25"},
    {"brand": "MAC", "name": "Warm Soul", "category": "Blush", "shade": "#E88080", "skin_tones": ["Medium", "Olive"], "price": "$25"},
    {"brand": "MAC", "name": "Raizin", "category": "Blush", "shade": "#DDA0DD", "skin_tones": ["Tan/Brown", "Dark"], "price": "$25"},
    {"brand": "MAC", "name": "Desert Rose", "category": "Blush", "shade": "#FF9999", "skin_tones": ["Fair", "Medium"], "price": "$25"},
    {"brand": "MAC", "name": "Peaches", "category": "Blush", "shade": "#F4A460", "skin_tones": ["Very Fair", "Fair"], "price": "$25"},
    # NARS - Blush
    {"brand": "NARS", "name": "Orgasm", "category": "Blush", "shade": "#FF8C69", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$30"},
    {"brand": "NARS", "name": "Deep Throat", "category": "Blush", "shade": "#FFD1DC", "skin_tones": ["Very Fair", "Fair"], "price": "$30"},
    {"brand": "NARS", "name": "Taj Mahal", "category": "Blush", "shade": "#FF69B4", "skin_tones": ["Olive", "Tan/Brown"], "price": "$30"},
    {"brand": "NARS", "name": "Luster", "category": "Blush", "shade": "#FFB7C5", "skin_tones": ["Medium", "Fair"], "price": "$30"},
    {"brand": "NARS", "name": "Desire", "category": "Blush", "shade": "#E88080", "skin_tones": ["Dark", "Tan/Brown"], "price": "$30"},
    # L'Oreal - Blush
    {"brand": "L'Oreal", "name": "Soft Rose", "category": "Blush", "shade": "#FFD1DC", "skin_tones": ["Very Fair", "Fair"], "price": "$12"},
    {"brand": "L'Oreal", "name": "Peach Amber", "category": "Blush", "shade": "#F4A460", "skin_tones": ["Medium", "Olive"], "price": "$12"},
    {"brand": "L'Oreal", "name": "Pink Coral", "category": "Blush", "shade": "#FF8C69", "skin_tones": ["Fair", "Medium"], "price": "$12"},
    # Maybelline - Blush
    {"brand": "Maybelline", "name": "Pink Amber", "category": "Blush", "shade": "#FF9999", "skin_tones": ["Very Fair", "Fair"], "price": "$10"},
    {"brand": "Maybelline", "name": "Coral Crush", "category": "Blush", "shade": "#E88080", "skin_tones": ["Medium", "Olive", "Tan/Brown"], "price": "$10"},
    {"brand": "Maybelline", "name": "Berry Chic", "category": "Blush", "shade": "#DDA0DD", "skin_tones": ["Dark", "Tan/Brown"], "price": "$10"},
    # MAC - Bronzer
    {"brand": "MAC", "name": "Bronzing Powder", "category": "Bronzer", "shade": "#C68642", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$30"},
    {"brand": "MAC", "name": "Refined Golden", "category": "Bronzer", "shade": "#D4A043", "skin_tones": ["Olive", "Tan/Brown"], "price": "$30"},
    {"brand": "MAC", "name": "Give Me Sun", "category": "Bronzer", "shade": "#B8860B", "skin_tones": ["Dark", "Tan/Brown"], "price": "$30"},
    # NARS - Bronzer
    {"brand": "NARS", "name": "Laguna", "category": "Bronzer", "shade": "#C68E5A", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$38"},
    {"brand": "NARS", "name": "Casino", "category": "Bronzer", "shade": "#A0785A", "skin_tones": ["Olive", "Tan/Brown", "Dark"], "price": "$38"},
    {"brand": "NARS", "name": "Copacabana", "category": "Bronzer", "shade": "#D4A55A", "skin_tones": ["Fair", "Medium"], "price": "$38"},
    # L'Oreal - Bronzer
    {"brand": "L'Oreal", "name": "True Match Bronzer", "category": "Bronzer", "shade": "#C9956C", "skin_tones": ["Very Fair", "Fair"], "price": "$14"},
    {"brand": "L'Oreal", "name": "Glam Bronze", "category": "Bronzer", "shade": "#B5743C", "skin_tones": ["Medium", "Olive", "Tan/Brown"], "price": "$14"},
    # Maybelline - Bronzer
    {"brand": "Maybelline", "name": "City Bronze", "category": "Bronzer", "shade": "#C68642", "skin_tones": ["Very Fair", "Fair", "Medium"], "price": "$11"},
    {"brand": "Maybelline", "name": "Amber Rush", "category": "Bronzer", "shade": "#A07850", "skin_tones": ["Olive", "Tan/Brown", "Dark"], "price": "$11"},
    # More MAC Lipstick
    {"brand": "MAC", "name": "Honeylove", "category": "Lipstick", "shade": "#D4A896", "skin_tones": ["Very Fair", "Fair"], "price": "$19"},
    {"brand": "MAC", "name": "Taupe", "category": "Lipstick", "shade": "#9E8080", "skin_tones": ["Medium", "Olive"], "price": "$19"},
    {"brand": "NARS", "name": "Red Square", "category": "Lipstick", "shade": "#B22222", "skin_tones": ["Medium", "Olive", "Tan/Brown"], "price": "$26"},
    {"brand": "NARS", "name": "Bahama", "category": "Blush", "shade": "#F4A460", "skin_tones": ["Dark", "Tan/Brown"], "price": "$30"},
    {"brand": "L'Oreal", "name": "Blushing Berry", "category": "Blush", "shade": "#DDA0DD", "skin_tones": ["Dark"], "price": "$12"},
    {"brand": "Maybelline", "name": "Dusty Rose", "category": "Lipstick", "shade": "#C4A0A0", "skin_tones": ["Fair", "Medium"], "price": "$9"},
]

def hex_to_bgr(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)

def classify_skin_tone(ita_angle):
    if ita_angle > 55:
        return "Very Fair"
    elif ita_angle > 41:
        return "Fair"
    elif ita_angle > 28:
        return "Medium"
    elif ita_angle > 10:
        return "Olive"
    elif ita_angle > -30:
        return "Tan/Brown"
    else:
        return "Dark"

def get_skin_tone(face_img):
    try:
        h, w = face_img.shape[:2]
        # Sample forehead region (top 20% of face, center 50%)
        forehead_y1 = int(h * 0.05)
        forehead_y2 = int(h * 0.20)
        forehead_x1 = int(w * 0.25)
        forehead_x2 = int(w * 0.75)
        forehead = face_img[forehead_y1:forehead_y2, forehead_x1:forehead_x2]
        if forehead.size == 0:
            return "Medium", 20.0
        lab = cv2.cvtColor(forehead, cv2.COLOR_BGR2LAB)
        avg_lab = np.mean(lab.reshape(-1, 3), axis=0)
        L_star = (avg_lab[0] / 255.0) * 100.0
        b_star = avg_lab[2] - 128.0
        if abs(b_star) < 1e-6:
            b_star = 1e-6
        ita = np.arctan((L_star - 50.0) / b_star) * (180.0 / np.pi)
        tone = classify_skin_tone(ita)
        return tone, round(ita, 2)
    except Exception:
        return "Medium", 20.0

def apply_lipstick(img, face_rect, eyes, lip_color_bgr, opacity):
    x, y, w, h = face_rect
    overlay = img.copy()
    if eyes is not None and len(eyes) >= 1:
        eye_bottom = max([ey + eh for (ex, ey, ew, eh) in eyes]) if len(eyes) > 0 else int(h * 0.5)
        lip_y = y + eye_bottom + int((h - eye_bottom) * 0.55)
    else:
        lip_y = y + int(h * 0.78)
    lip_center_x = x + w // 2
    lip_w = int(w * 0.38)
    lip_h = int(h * 0.065)
    cv2.ellipse(overlay, (lip_center_x, lip_y), (lip_w, lip_h), 0, 0, 360, lip_color_bgr, -1)
    cv2.ellipse(overlay, (lip_center_x, lip_y - lip_h // 2), (lip_w // 2, lip_h // 2), 0, 0, 180, lip_color_bgr, -1)
    blurred = cv2.GaussianBlur(overlay, (15, 15), 5)
    result = cv2.addWeighted(blurred, opacity, img, 1 - opacity, 0)
    return result

def apply_blush(img, face_rect, blush_color_bgr, opacity):
    x, y, w, h = face_rect
    overlay = img.copy()
    left_cheek = (x + int(w * 0.2), y + int(h * 0.55))
    right_cheek = (x + int(w * 0.8), y + int(h * 0.55))
    radius = int(w * 0.15)
    cv2.circle(overlay, left_cheek, radius, blush_color_bgr, -1)
    cv2.circle(overlay, right_cheek, radius, blush_color_bgr, -1)
    blurred = cv2.GaussianBlur(overlay, (51, 51), 20)
    result = cv2.addWeighted(blurred, opacity * 0.6, img, 1 - opacity * 0.6, 0)
    return result

def apply_eyeshadow(img, face_rect, eyes, eye_color_bgr, opacity):
    if eyes is None or len(eyes) == 0:
        return img
    x, y, w, h = face_rect
    overlay = img.copy()
    for (ex, ey, ew, eh) in eyes:
        abs_ex = x + ex + ew // 2
        abs_ey = y + ey + int(eh * 0.3)
        cv2.ellipse(overlay, (abs_ex, abs_ey), (int(ew * 0.6), int(eh * 0.4)), 0, 0, 360, eye_color_bgr, -1)
    blurred = cv2.GaussianBlur(overlay, (21, 21), 8)
    result = cv2.addWeighted(blurred, opacity * 0.55, img, 1 - opacity * 0.55, 0)
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({"status": "ok", "message": "GlowAI backend running"})

@app.route('/process_frame', methods=['POST'])
def process_frame():
    try:
        data = request.get_json()
        image_data = data.get('image', '')
        settings = data.get('settings', {})
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "Invalid image"}), 400

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

        skin_tone = None
        ita_value = None
        pipeline_steps = {
            "face_detection": False,
            "landmark_extraction": False,
            "skin_tone": False,
            "makeup_application": False,
            "recommendations": False
        }

        if len(faces) > 0:
            pipeline_steps["face_detection"] = True
            face_rect = faces[0]
            x, y, w, h = face_rect
            face_img = img[y:y+h, x:x+w]
            face_gray = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(face_gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
            pipeline_steps["landmark_extraction"] = True
            skin_tone, ita_value = get_skin_tone(face_img)
            pipeline_steps["skin_tone"] = True

            opacity = float(settings.get('opacity', 0.5))
            if settings.get('lipstick', False):
                lip_hex = settings.get('lip_color', '#C4607A')
                lip_bgr = hex_to_bgr(lip_hex)
                img = apply_lipstick(img, face_rect, eyes if len(eyes) > 0 else None, lip_bgr, opacity)

            if settings.get('blush', False):
                blush_hex = settings.get('blush_color', '#FFB7C5')
                blush_bgr = hex_to_bgr(blush_hex)
                img = apply_blush(img, face_rect, blush_bgr, opacity)

            if settings.get('eyeshadow', False):
                eye_hex = settings.get('eye_color', '#B46482')
                eye_bgr = hex_to_bgr(eye_hex)
                img = apply_eyeshadow(img, face_rect, eyes if len(eyes) > 0 else None, eye_bgr, opacity)

            pipeline_steps["makeup_application"] = True
            pipeline_steps["recommendations"] = True

            cv2.rectangle(img, (x, y), (x+w, y+h), (196, 96, 122), 1)

        _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 75])
        processed_b64 = base64.b64encode(buffer).decode('utf-8')

        return jsonify({
            "processed_image": f"data:image/jpeg;base64,{processed_b64}",
            "skin_tone": skin_tone,
            "ita_value": ita_value,
            "face_detected": len(faces) > 0,
            "pipeline_steps": pipeline_steps
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/recommendations')
def recommendations():
    tone = request.args.get('skin_tone', 'Medium')
    filtered = [p for p in PRODUCTS if tone in p.get('skin_tones', [])]
    by_category = {}
    for p in filtered:
        cat = p['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(p)
    return jsonify({"skin_tone": tone, "products": by_category, "total": len(filtered)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
