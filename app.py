import os
import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

# ── Persistent face smoother (server-side EMA) ──
_smooth = None
_miss   = 0

def smooth_face(raw):
    global _smooth, _miss
    if raw is None:
        _miss += 1
        if _miss > 6:
            _smooth = None
        return _smooth
    _miss = 0
    if _smooth is None:
        _smooth = raw
        return raw
    a = 0.30
    _smooth = (
        int(_smooth[0]*a + raw[0]*(1-a)),
        int(_smooth[1]*a + raw[1]*(1-a)),
        int(_smooth[2]*a + raw[2]*(1-a)),
        int(_smooth[3]*a + raw[3]*(1-a)),
    )
    return _smooth

# ── PRODUCTS ──
PRODUCTS = [
    {"brand":"MAC","name":"Ruby Woo","category":"Lipstick","shade":"#CC0000","skin_tones":["Very Fair","Fair"],"price":"$19"},
    {"brand":"MAC","name":"Velvet Teddy","category":"Lipstick","shade":"#C4607A","skin_tones":["Medium","Olive"],"price":"$19"},
    {"brand":"MAC","name":"Chili","category":"Lipstick","shade":"#A0522D","skin_tones":["Tan/Brown","Dark"],"price":"$19"},
    {"brand":"MAC","name":"Whirl","category":"Lipstick","shade":"#8B6F6F","skin_tones":["Fair","Medium"],"price":"$19"},
    {"brand":"MAC","name":"Mehr","category":"Lipstick","shade":"#D4748C","skin_tones":["Very Fair","Fair","Medium"],"price":"$19"},
    {"brand":"MAC","name":"Lady Danger","category":"Lipstick","shade":"#FF4500","skin_tones":["Olive","Tan/Brown"],"price":"$19"},
    {"brand":"MAC","name":"Diva","category":"Lipstick","shade":"#800020","skin_tones":["Dark","Tan/Brown"],"price":"$19"},
    {"brand":"MAC","name":"Candy Yum-Yum","category":"Lipstick","shade":"#FF6B8A","skin_tones":["Very Fair","Fair"],"price":"$19"},
    {"brand":"MAC","name":"Heroine","category":"Lipstick","shade":"#7B3F7B","skin_tones":["Dark","Olive"],"price":"$19"},
    {"brand":"MAC","name":"Twig","category":"Lipstick","shade":"#B87F7F","skin_tones":["Medium","Olive"],"price":"$19"},
    {"brand":"MAC","name":"Honeylove","category":"Lipstick","shade":"#D4A896","skin_tones":["Very Fair","Fair"],"price":"$19"},
    {"brand":"MAC","name":"Taupe","category":"Lipstick","shade":"#9E8080","skin_tones":["Medium","Olive"],"price":"$19"},
    {"brand":"NARS","name":"Jungle Red","category":"Lipstick","shade":"#CC2200","skin_tones":["Very Fair","Fair"],"price":"$26"},
    {"brand":"NARS","name":"Schiap","category":"Lipstick","shade":"#FF69B4","skin_tones":["Very Fair","Fair"],"price":"$26"},
    {"brand":"NARS","name":"Heat Wave","category":"Lipstick","shade":"#FF6347","skin_tones":["Medium","Olive"],"price":"$26"},
    {"brand":"NARS","name":"Dolce Vita","category":"Lipstick","shade":"#C08080","skin_tones":["Fair","Medium"],"price":"$26"},
    {"brand":"NARS","name":"Dragon Girl","category":"Lipstick","shade":"#FF0000","skin_tones":["Tan/Brown","Dark"],"price":"$26"},
    {"brand":"NARS","name":"Cruella","category":"Lipstick","shade":"#8B0000","skin_tones":["Dark","Tan/Brown"],"price":"$26"},
    {"brand":"NARS","name":"Volga","category":"Lipstick","shade":"#FFB6C1","skin_tones":["Very Fair"],"price":"$26"},
    {"brand":"NARS","name":"Rikugien","category":"Lipstick","shade":"#D2691E","skin_tones":["Olive","Medium"],"price":"$26"},
    {"brand":"NARS","name":"Red Square","category":"Lipstick","shade":"#B22222","skin_tones":["Medium","Olive","Tan/Brown"],"price":"$26"},
    {"brand":"L'Oreal","name":"Pure Red","category":"Lipstick","shade":"#FF0000","skin_tones":["Very Fair","Fair","Medium"],"price":"$11"},
    {"brand":"L'Oreal","name":"Spice","category":"Lipstick","shade":"#A0522D","skin_tones":["Tan/Brown","Dark"],"price":"$11"},
    {"brand":"L'Oreal","name":"Nude Beige","category":"Lipstick","shade":"#D4B5A0","skin_tones":["Very Fair","Fair"],"price":"$11"},
    {"brand":"L'Oreal","name":"Cocoa","category":"Lipstick","shade":"#6B4226","skin_tones":["Dark","Tan/Brown"],"price":"$11"},
    {"brand":"L'Oreal","name":"Rose Quartz","category":"Lipstick","shade":"#F4A8B0","skin_tones":["Fair","Medium"],"price":"$11"},
    {"brand":"Maybelline","name":"Red Revival","category":"Lipstick","shade":"#CC0000","skin_tones":["Very Fair","Fair","Medium"],"price":"$9"},
    {"brand":"Maybelline","name":"Nude Flush","category":"Lipstick","shade":"#E8B4A0","skin_tones":["Very Fair","Fair"],"price":"$9"},
    {"brand":"Maybelline","name":"Berry Bossy","category":"Lipstick","shade":"#8B1A4A","skin_tones":["Olive","Tan/Brown","Dark"],"price":"$9"},
    {"brand":"Maybelline","name":"Pink Fling","category":"Lipstick","shade":"#FF8DA1","skin_tones":["Very Fair","Fair"],"price":"$9"},
    {"brand":"Maybelline","name":"Caramel Kiss","category":"Lipstick","shade":"#C68E5A","skin_tones":["Medium","Olive"],"price":"$9"},
    {"brand":"Maybelline","name":"Dusty Rose","category":"Lipstick","shade":"#C4A0A0","skin_tones":["Fair","Medium"],"price":"$9"},
    {"brand":"MAC","name":"Fleur Power","category":"Blush","shade":"#FFB7C5","skin_tones":["Very Fair","Fair"],"price":"$25"},
    {"brand":"MAC","name":"Warm Soul","category":"Blush","shade":"#E88080","skin_tones":["Medium","Olive"],"price":"$25"},
    {"brand":"MAC","name":"Raizin","category":"Blush","shade":"#DDA0DD","skin_tones":["Tan/Brown","Dark"],"price":"$25"},
    {"brand":"MAC","name":"Desert Rose","category":"Blush","shade":"#FF9999","skin_tones":["Fair","Medium"],"price":"$25"},
    {"brand":"MAC","name":"Peaches","category":"Blush","shade":"#F4A460","skin_tones":["Very Fair","Fair"],"price":"$25"},
    {"brand":"NARS","name":"Orgasm","category":"Blush","shade":"#FF8C69","skin_tones":["Very Fair","Fair","Medium"],"price":"$30"},
    {"brand":"NARS","name":"Deep Throat","category":"Blush","shade":"#FFD1DC","skin_tones":["Very Fair","Fair"],"price":"$30"},
    {"brand":"NARS","name":"Taj Mahal","category":"Blush","shade":"#FF69B4","skin_tones":["Olive","Tan/Brown"],"price":"$30"},
    {"brand":"NARS","name":"Luster","category":"Blush","shade":"#FFB7C5","skin_tones":["Medium","Fair"],"price":"$30"},
    {"brand":"NARS","name":"Desire","category":"Blush","shade":"#E88080","skin_tones":["Dark","Tan/Brown"],"price":"$30"},
    {"brand":"NARS","name":"Bahama","category":"Blush","shade":"#F4A460","skin_tones":["Dark","Tan/Brown"],"price":"$30"},
    {"brand":"L'Oreal","name":"Soft Rose","category":"Blush","shade":"#FFD1DC","skin_tones":["Very Fair","Fair"],"price":"$12"},
    {"brand":"L'Oreal","name":"Peach Amber","category":"Blush","shade":"#F4A460","skin_tones":["Medium","Olive"],"price":"$12"},
    {"brand":"L'Oreal","name":"Pink Coral","category":"Blush","shade":"#FF8C69","skin_tones":["Fair","Medium"],"price":"$12"},
    {"brand":"L'Oreal","name":"Blushing Berry","category":"Blush","shade":"#DDA0DD","skin_tones":["Dark"],"price":"$12"},
    {"brand":"Maybelline","name":"Pink Amber","category":"Blush","shade":"#FF9999","skin_tones":["Very Fair","Fair"],"price":"$10"},
    {"brand":"Maybelline","name":"Coral Crush","category":"Blush","shade":"#E88080","skin_tones":["Medium","Olive","Tan/Brown"],"price":"$10"},
    {"brand":"Maybelline","name":"Berry Chic","category":"Blush","shade":"#DDA0DD","skin_tones":["Dark","Tan/Brown"],"price":"$10"},
    {"brand":"MAC","name":"Bronzing Powder","category":"Bronzer","shade":"#C68642","skin_tones":["Very Fair","Fair","Medium"],"price":"$30"},
    {"brand":"MAC","name":"Refined Golden","category":"Bronzer","shade":"#D4A043","skin_tones":["Olive","Tan/Brown"],"price":"$30"},
    {"brand":"MAC","name":"Give Me Sun","category":"Bronzer","shade":"#B8860B","skin_tones":["Dark","Tan/Brown"],"price":"$30"},
    {"brand":"NARS","name":"Laguna","category":"Bronzer","shade":"#C68E5A","skin_tones":["Very Fair","Fair","Medium"],"price":"$38"},
    {"brand":"NARS","name":"Casino","category":"Bronzer","shade":"#A0785A","skin_tones":["Olive","Tan/Brown","Dark"],"price":"$38"},
    {"brand":"NARS","name":"Copacabana","category":"Bronzer","shade":"#D4A55A","skin_tones":["Fair","Medium"],"price":"$38"},
    {"brand":"L'Oreal","name":"True Match","category":"Bronzer","shade":"#C9956C","skin_tones":["Very Fair","Fair"],"price":"$14"},
    {"brand":"L'Oreal","name":"Glam Bronze","category":"Bronzer","shade":"#B5743C","skin_tones":["Medium","Olive","Tan/Brown"],"price":"$14"},
    {"brand":"Maybelline","name":"City Bronze","category":"Bronzer","shade":"#C68642","skin_tones":["Very Fair","Fair","Medium"],"price":"$11"},
    {"brand":"Maybelline","name":"Amber Rush","category":"Bronzer","shade":"#A07850","skin_tones":["Olive","Tan/Brown","Dark"],"price":"$11"},
]

def hex_to_bgr(h):
    h = h.lstrip('#')
    return (int(h[4:6],16), int(h[2:4],16), int(h[0:2],16))

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
        r = face_img[int(h*.05):int(h*.22), int(w*.25):int(w*.75)]
        if r.size == 0: return "Medium", 20.0
        lab = cv2.cvtColor(r, cv2.COLOR_BGR2LAB)
        avg = np.mean(lab.reshape(-1,3), axis=0)
        L = (avg[0]/255.)*100.; b = avg[2]-128.
        if abs(b)<1e-6: b=1e-6
        ita = np.arctan((L-50.)/b)*(180./np.pi)
        return classify_skin_tone(ita), round(float(ita),2)
    except:
        return "Medium", 20.0

def alpha_blend(img, mask_2d, color_bgr, strength):
    """Blend a solid color onto img using a float mask [0,1]."""
    alpha = np.clip(mask_2d * strength, 0, 1)
    for c, col in enumerate(color_bgr):
        img[:,:,c] = np.clip(
            img[:,:,c].astype(np.float32) * (1 - alpha) + col * alpha, 0, 255
        ).astype(np.uint8)
    return img

def apply_lipstick(img, x, y, w, h, eyes, color_bgr, opacity):
    if eyes is not None and len(eyes):
        eb = max(ey+eh for ex,ey,ew,eh in eyes)
        ly = y + eb + int((h - eb) * 0.58)
    else:
        ly = y + int(h * 0.80)
    cx = x + w//2
    lw = int(w * 0.34); lh = int(h * 0.058)

    mask = np.zeros(img.shape[:2], np.float32)
    # lower lip
    cv2.ellipse(mask,(cx,ly),(lw,lh),0,0,180,1.,-1)
    # upper lip
    cv2.ellipse(mask,(cx,ly),(lw,lh),0,180,360,0.85,-1)
    # cupid bow bumps
    cv2.ellipse(mask,(cx-lw//4,ly-lh//2),(lw//4,lh//2),0,180,360,0.7,-1)
    cv2.ellipse(mask,(cx+lw//4,ly-lh//2),(lw//4,lh//2),0,180,360,0.7,-1)
    # soft edge
    mask = cv2.GaussianBlur(mask,(9,9),3)
    img = alpha_blend(img, mask, color_bgr, opacity * 0.92)

    # subtle shine highlight
    shine = np.zeros(img.shape[:2], np.float32)
    cv2.ellipse(shine,(cx - lw//8, ly + lh//4),(lw//6, lh//5),0,0,360,1.,-1)
    shine = cv2.GaussianBlur(shine,(7,7),2)
    img = alpha_blend(img, shine, (255,255,255), opacity * 0.18)
    return img

def apply_blush(img, x, y, w, h, color_bgr, opacity):
    mask = np.zeros(img.shape[:2], np.float32)
    for cx in [x+int(w*.18), x+int(w*.82)]:
        cy = y+int(h*.58); r = int(w*.18)
        cv2.ellipse(mask,(cx,cy),(r,int(r*.75)),0,0,360,1.,-1)
    mask = cv2.GaussianBlur(mask,(71,71),26)
    return alpha_blend(img, mask, color_bgr, opacity * 0.52)

def apply_eyeshadow(img, x, y, w, h, eyes, color_bgr, opacity):
    if not eyes or not len(eyes): return img
    mask = np.zeros(img.shape[:2], np.float32)
    for ex,ey,ew,eh in eyes:
        ax=x+ex+ew//2; ay=y+ey+int(eh*.25)
        cv2.ellipse(mask,(ax,ay),(int(ew*.65),int(eh*.5)),0,0,360,1.,-1)
    mask = cv2.GaussianBlur(mask,(29,29),10)
    return alpha_blend(img, mask, color_bgr, opacity * 0.50)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return jsonify({"status":"ok"})

@app.route('/process_frame', methods=['POST'])
def process_frame():
    try:
        data    = request.get_json(force=True)
        b64     = data.get('image','')
        sett    = data.get('settings',{})
        if ',' in b64: b64 = b64.split(',')[1]
        img = cv2.imdecode(np.frombuffer(base64.b64decode(b64),np.uint8), cv2.IMREAD_COLOR)
        if img is None: return jsonify({"error":"bad image"}),400

        # ── Upscale small input for better quality output ──
        # Client sends 480x360; upscale to 720p for processing & output
        orig_h, orig_w = img.shape[:2]
        scale = 720 / orig_h if orig_h < 720 else 1.0
        if scale > 1.0:
            img = cv2.resize(img, (int(orig_w*scale), int(orig_h*scale)),
                             interpolation=cv2.INTER_LANCZOS4)

        gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        raw_faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=6,
            minSize=(80,80), flags=cv2.CASCADE_SCALE_IMAGE)

        pipeline = {k:False for k in
            ["face_detection","landmark_extraction","skin_tone","makeup_application","recommendations"]}

        raw   = tuple(map(int, raw_faces[0])) if len(raw_faces) else None
        face  = smooth_face(raw)
        tone  = None; ita = None

        if face:
            x,y,w,h = face
            x=max(0,x); y=max(0,y)
            w=min(w,img.shape[1]-x); h=min(h,img.shape[0]-y)
            pipeline["face_detection"] = True

            fg = gray[y:y+h, x:x+w]
            eyes = eye_cascade.detectMultiScale(fg,1.1,4,
                       minSize=(int(w*.08),int(h*.06)))
            pipeline["landmark_extraction"] = True

            tone, ita = get_skin_tone(img[y:y+h,x:x+w])
            pipeline["skin_tone"] = True

            op = float(sett.get('opacity',0.5))
            el = list(eyes) if len(eyes) else None

            if sett.get('lipstick'):
                img = apply_lipstick(img,x,y,w,h,el,hex_to_bgr(sett.get('lip_color','#C4607A')),op)
            if sett.get('blush'):
                img = apply_blush(img,x,y,w,h,hex_to_bgr(sett.get('blush_color','#FFB7C5')),op)
            if sett.get('eyeshadow'):
                img = apply_eyeshadow(img,x,y,w,h,el,hex_to_bgr(sett.get('eye_color','#B46482')),op)

            pipeline["makeup_application"] = True
            pipeline["recommendations"]    = True

            # Premium corner markers
            c=(196,96,122); t=2; cs=int(min(w,h)*.09)
            pts=[(x,y),(x+w,y),(x,y+h),(x+w,y+h)]
            dirs=[(1,1),(-1,1),(1,-1),(-1,-1)]
            for (px,py),(dx,dy) in zip(pts,dirs):
                cv2.line(img,(px,py),(px+dx*cs,py),c,t)
                cv2.line(img,(px,py),(px,py+dy*cs),c,t)

        # ── Downscale back to 640×480 for fast transfer ──
        out = cv2.resize(img,(640,480),interpolation=cv2.INTER_LANCZOS4)

        # Encode at quality 88 — sharp but not huge
        _, buf = cv2.imencode('.jpg', out,
                              [cv2.IMWRITE_JPEG_QUALITY, 88,
                               cv2.IMWRITE_JPEG_OPTIMIZE, 1])
        b64out = base64.b64encode(buf).decode()

        return jsonify({
            "processed_image": f"data:image/jpeg;base64,{b64out}",
            "skin_tone":   tone,
            "ita_value":   ita,
            "face_detected": face is not None,
            "pipeline_steps": pipeline,
        })
    except Exception as e:
        return jsonify({"error":str(e)}),500

@app.route('/recommendations')
def recommendations():
    tone = request.args.get('skin_tone','Medium')
    f = [p for p in PRODUCTS if tone in p.get('skin_tones',[])]
    by_cat = {}
    for p in f: by_cat.setdefault(p['category'],[]).append(p)
    return jsonify({"skin_tone":tone,"products":by_cat,"total":len(f)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=False)
    
