/* GlowAI — app.js v3 — Native Camera Clarity + Client-Side Makeup Rendering */
(function () {
  'use strict';

  // ── STATE ──
  const state = {
    cameraActive: false,
    currentSkinTone: null,
    lipColor:   '#FF0000',
    blushColor: '#FFB7C5',
    eyeColor:   '#B46482',
    opacity:    0.5,
    lipstickOn:  false,
    blushOn:     false,
    eyeshadowOn: false,

    // From server — updated every ~250ms
    faceData: null,   // { fx,fy,fw,fh, eyes:[{ex,ey,ew,eh},...], skin_tone, ita_value, pipeline_steps }

    isSending:   false,
    frameTimer:  null,
    animFrame:   null,
    displayCanvas: null,
    displayCtx:    null,
    sendCanvas:    null,
    sendCtx:       null,

    // Smoothed face rect (client-side EMA for buttery tracking)
    smoothFace: null,
  };

  const TONE_COLORS = {
    'Very Fair': '#F5DEB3',
    'Fair':      '#E8C99A',
    'Medium':    '#C68642',
    'Olive':     '#A0785A',
    'Tan/Brown': '#7A4B2A',
    'Dark':      '#3D1F10',
  };

  // ── ELEMENTS ──
  const video             = document.getElementById('video');
  const processedImg      = document.getElementById('processedImg');
  const startBtn          = document.getElementById('startBtn');
  const skinToneEl        = document.getElementById('skinTone');
  const skinDot           = document.getElementById('skinDot');
  const itaBadge          = document.getElementById('itaBadge');
  const cameraPlaceholder = document.getElementById('cameraPlaceholder');
  const faceDot           = document.getElementById('faceDot');
  const faceStatus        = document.getElementById('faceStatus');
  const opacitySlider     = document.getElementById('opacitySlider');
  const opacityValue      = document.getElementById('opacityValue');
  const lipstickToggle    = document.getElementById('lipstickToggle');
  const blushToggle       = document.getElementById('blushToggle');
  const eyeshadowToggle   = document.getElementById('eyeshadowToggle');
  const lipRow            = document.getElementById('lipRow');
  const blushRow          = document.getElementById('blushRow');
  const eyeRow            = document.getElementById('eyeRow');
  const recsEl            = document.getElementById('recommendations');

  const STEP_MAP = {
    face_detection:      'step-face',
    landmark_extraction: 'step-landmark',
    skin_tone:           'step-skin',
    makeup_application:  'step-makeup',
    recommendations:     'step-recs',
  };

  // ── CANVAS INIT ──
  function initCanvases() {
    // Send canvas — small, for face detection only
    state.sendCanvas = document.createElement('canvas');
    state.sendCanvas.width  = 480;
    state.sendCanvas.height = 360;
    state.sendCtx = state.sendCanvas.getContext('2d');

    // Display canvas — native resolution, lives on top of video
    state.displayCanvas = document.createElement('canvas');
    state.displayCanvas.style.cssText = `
      position:absolute;inset:0;width:100%;height:100%;
      object-fit:cover;border-radius:inherit;z-index:3;pointer-events:none;
    `;
    document.getElementById('cameraWrap').appendChild(state.displayCanvas);
    state.displayCtx = state.displayCanvas.getContext('2d', { alpha: true });
  }

  // ─────────────────────────────────────────────────────────────
  // RENDER LOOP — runs at 60fps
  // Draws ONLY the makeup overlays on a transparent canvas
  // The actual video element underneath stays native & crisp
  // ─────────────────────────────────────────────────────────────
  function renderLoop() {
    if (!state.cameraActive) return;
    state.animFrame = requestAnimationFrame(renderLoop);

    const canvas = state.displayCanvas;
    const ctx    = state.displayCtx;
    const vw     = video.videoWidth;
    const vh     = video.videoHeight;
    if (!vw || !vh) return;

    // Match canvas to video native resolution
    if (canvas.width !== vw || canvas.height !== vh) {
      canvas.width  = vw;
      canvas.height = vh;
    }

    // Clear — transparent, video shows through below
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const fd = state.smoothFace;
    if (!fd) return;

    const { fx, fy, fw, fh, eyes } = fd;

    // Scale coords from send-canvas (480x360) → display canvas (native res)
    const scaleX = canvas.width  / state.sendCanvas.width;
    const scaleY = canvas.height / state.sendCanvas.height;

    // Mirror: server processed non-mirrored image, display is mirrored
    // So we mirror the X coordinates to match the flipped video
    const mfx = canvas.width - (fx + fw) * scaleX;
    const mfy = fy * scaleY;
    const mfw = fw * scaleX;
    const mfh = fh * scaleY;

    const opacity = state.opacity;

    // ── BLUSH ──
    if (state.blushOn) {
      drawBlush(ctx, mfx, mfy, mfw, mfh, opacity);
    }

    // ── EYESHADOW ──
    if (state.eyeshadowOn && eyes && eyes.length > 0) {
      drawEyeshadow(ctx, mfx, mfy, mfw, mfh, eyes, scaleX, scaleY, opacity);
    }

    // ── LIPSTICK ──
    if (state.lipstickOn) {
      drawLipstick(ctx, mfx, mfy, mfw, mfh, eyes, scaleX, scaleY, opacity);
    }

    // ── FACE CORNERS ──
    drawCorners(ctx, mfx, mfy, mfw, mfh);
  }

  // ─────────────────────────────────────────────────────────────
  // CLIENT-SIDE MAKEUP DRAWING — pure Canvas 2D API
  // ─────────────────────────────────────────────────────────────

  function hexToRgba(hex, alpha) {
    const h = hex.replace('#','');
    const r = parseInt(h.slice(0,2),16);
    const g = parseInt(h.slice(2,4),16);
    const b = parseInt(h.slice(4,6),16);
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function drawLipstick(ctx, fx, fy, fw, fh, eyes, scaleX, scaleY, opacity) {
    let lipY;
    if (eyes && eyes.length > 0) {
      const eyeBottom = Math.max(...eyes.map(e => (e.ey + e.eh) * scaleY));
      lipY = fy + eyeBottom + (fh - eyeBottom) * 0.58;
    } else {
      lipY = fy + fh * 0.80;
    }
    const cx   = fx + fw / 2;
    const lipW = fw * 0.36;
    const lipH = fh * 0.060;

    const color   = hexToRgba(state.lipColor, opacity * 0.85);
    const colorSoft = hexToRgba(state.lipColor, opacity * 0.5);

    ctx.save();

    // Soft glow behind lips
    const grd = ctx.createRadialGradient(cx, lipY, 0, cx, lipY, lipW);
    grd.addColorStop(0,   hexToRgba(state.lipColor, opacity * 0.45));
    grd.addColorStop(0.6, hexToRgba(state.lipColor, opacity * 0.25));
    grd.addColorStop(1,   hexToRgba(state.lipColor, 0));
    ctx.fillStyle = grd;
    ctx.beginPath();
    ctx.ellipse(cx, lipY, lipW * 1.2, lipH * 2.5, 0, 0, Math.PI * 2);
    ctx.fill();

    // Lower lip
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.ellipse(cx, lipY, lipW, lipH, 0, 0, Math.PI);
    ctx.fill();

    // Upper lip
    ctx.beginPath();
    ctx.ellipse(cx, lipY, lipW, lipH, 0, Math.PI, Math.PI * 2);
    ctx.fill();

    // Upper cupid bow dip
    ctx.beginPath();
    ctx.ellipse(cx - lipW * 0.25, lipY - lipH * 0.5, lipW * 0.28, lipH * 0.6, 0, 0, Math.PI * 2);
    ctx.fillStyle = colorSoft;
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(cx + lipW * 0.25, lipY - lipH * 0.5, lipW * 0.28, lipH * 0.6, 0, 0, Math.PI * 2);
    ctx.fill();

    // Highlight shine
    ctx.fillStyle = `rgba(255,255,255,${opacity * 0.18})`;
    ctx.beginPath();
    ctx.ellipse(cx - lipW * 0.1, lipY + lipH * 0.2, lipW * 0.25, lipH * 0.22, -0.3, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  }

  function drawBlush(ctx, fx, fy, fw, fh, opacity) {
    const lx  = fx + fw * 0.16;
    const rx  = fx + fw * 0.84;
    const cy  = fy + fh * 0.58;
    const rad = fw * 0.18;

    [lx, rx].forEach(x => {
      const grd = ctx.createRadialGradient(x, cy, 0, x, cy, rad);
      grd.addColorStop(0,   hexToRgba(state.blushColor, opacity * 0.55));
      grd.addColorStop(0.5, hexToRgba(state.blushColor, opacity * 0.30));
      grd.addColorStop(1,   hexToRgba(state.blushColor, 0));
      ctx.fillStyle = grd;
      ctx.beginPath();
      ctx.ellipse(x, cy, rad, rad * 0.75, 0, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawEyeshadow(ctx, fx, fy, fw, fh, eyes, scaleX, scaleY, opacity) {
    eyes.forEach(({ ex, ey, ew, eh }) => {
      // Mirror eye X to match flipped canvas
      const rawEyeCx = ex * scaleX + (ew * scaleX) / 2;
      const eyeCx = fw - rawEyeCx; // mirror within face
      const eyeCy = ey * scaleY + (eh * scaleY) * 0.3;
      const eyeW  = ew * scaleX * 0.7;
      const eyeH  = eh * scaleY * 0.55;

      const absCx = fx + eyeCx;
      const absCy = fy + eyeCy;

      const grd = ctx.createRadialGradient(absCx, absCy, 0, absCx, absCy, eyeW);
      grd.addColorStop(0,   hexToRgba(state.eyeColor, opacity * 0.60));
      grd.addColorStop(0.6, hexToRgba(state.eyeColor, opacity * 0.35));
      grd.addColorStop(1,   hexToRgba(state.eyeColor, 0));
      ctx.fillStyle = grd;
      ctx.beginPath();
      ctx.ellipse(absCx, absCy, eyeW, eyeH, 0, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function drawCorners(ctx, fx, fy, fw, fh) {
    ctx.strokeStyle = 'rgba(196,96,122,0.75)';
    ctx.lineWidth   = 2;
    const cs = Math.min(fw, fh) * 0.08;

    const corners = [
      [fx,    fy,    cs,  0, 0, cs],
      [fx+fw, fy,    -cs, 0, 0, cs],
      [fx,    fy+fh, cs,  0, 0,-cs],
      [fx+fw, fy+fh, -cs, 0, 0,-cs],
    ];
    corners.forEach(([x, y, dx1, dy1, dx2, dy2]) => {
      ctx.beginPath();
      ctx.moveTo(x + dx1, y);
      ctx.lineTo(x, y);
      ctx.lineTo(x, y + dy2 || y + (dy1 || dy2));
      ctx.stroke();
    });

    // Simpler corner drawing
    ctx.beginPath();
    // TL
    ctx.moveTo(fx + cs, fy); ctx.lineTo(fx, fy); ctx.lineTo(fx, fy + cs);
    // TR
    ctx.moveTo(fx+fw-cs, fy); ctx.lineTo(fx+fw, fy); ctx.lineTo(fx+fw, fy+cs);
    // BL
    ctx.moveTo(fx+cs, fy+fh); ctx.lineTo(fx, fy+fh); ctx.lineTo(fx, fy+fh-cs);
    // BR
    ctx.moveTo(fx+fw-cs, fy+fh); ctx.lineTo(fx+fw, fy+fh); ctx.lineTo(fx+fw, fy+fh-cs);
    ctx.stroke();
  }

  // ─────────────────────────────────────────────────────────────
  // SEND LOOP — sends frame to server every 250ms
  // Server returns ONLY face/eye coordinates + skin tone
  // No image comes back — camera stays pristine
  // ─────────────────────────────────────────────────────────────
  function startSendLoop() {
    if (!state.cameraActive) return;
    state.frameTimer = setTimeout(async () => {
      if (state.cameraActive) {
        await captureAndSend();
        startSendLoop();
      }
    }, 250);
  }

  async function captureAndSend() {
    if (state.isSending || !video.videoWidth) return;
    state.isSending = true;
    try {
      const sCtx   = state.sendCtx;
      const sCv    = state.sendCanvas;
      // Capture non-mirrored for server (server expects normal orientation)
      sCtx.drawImage(video, 0, 0, sCv.width, sCv.height);
      const imageData = sCv.toDataURL('image/jpeg', 0.7);

      const res = await fetch('/detect_face', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ image: imageData }),
      });
      if (!res.ok) return;
      const data = await res.json();
      handleDetectionResponse(data);
    } catch (e) {
      console.warn('Detection error:', e);
    } finally {
      state.isSending = false;
    }
  }

  const EMA = 0.35; // smoothing factor
  function smoothRect(prev, next) {
    if (!prev) return next;
    return {
      fx: prev.fx * EMA + next.fx * (1 - EMA),
      fy: prev.fy * EMA + next.fy * (1 - EMA),
      fw: prev.fw * EMA + next.fw * (1 - EMA),
      fh: prev.fh * EMA + next.fh * (1 - EMA),
      eyes: next.eyes,
      skin_tone: next.skin_tone,
      ita_value: next.ita_value,
      pipeline_steps: next.pipeline_steps,
    };
  }

  let noFaceCount = 0;
  function handleDetectionResponse(data) {
    if (data.face_detected && data.face) {
      noFaceCount = 0;
      state.smoothFace = smoothRect(state.smoothFace, data.face);
      faceDot.classList.add('active');
      faceStatus.textContent = 'Face Found';
    } else {
      noFaceCount++;
      if (noFaceCount > 5) {
        state.smoothFace = null;
        faceDot.classList.remove('active');
        faceStatus.textContent = 'Scanning…';
      }
    }

    if (data.skin_tone) {
      skinToneEl.textContent = data.skin_tone;
      const tc = TONE_COLORS[data.skin_tone] || '#c68642';
      skinDot.style.background = tc;
      skinDot.style.boxShadow  = `0 0 14px ${tc}99`;
      if (data.ita_value != null) itaBadge.textContent = `ITA ${data.ita_value}°`;
      if (data.skin_tone !== state.currentSkinTone) {
        state.currentSkinTone = data.skin_tone;
        loadRecommendations(data.skin_tone);
      }
    }

    updatePipeline(data.pipeline_steps || {});
  }

  // ── CAMERA START/STOP ──
  startBtn.addEventListener('click', async () => {
    if (state.cameraActive) { stopCamera(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width:     { ideal: 1280, min: 640 },
          height:    { ideal: 720,  min: 480 },
          frameRate: { ideal: 30,   min: 15 },
          facingMode: 'user',
        },
        audio: false,
      });
      video.srcObject = stream;
      // Show native video element — it stays untouched and crisp
      video.style.display = 'block';
      video.style.transform = 'scaleX(-1)'; // mirror it naturally
      processedImg.style.display = 'none';
      await video.play();

      state.cameraActive = true;
      cameraPlaceholder.classList.add('hidden');
      startBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Stop Camera`;
      startBtn.classList.add('active');
      lipRow.classList.remove('disabled');
      blushRow.classList.remove('disabled');
      eyeRow.classList.remove('disabled');

      initCanvases();
      renderLoop();    // 60fps overlay drawing
      startSendLoop(); // 250ms face detection
    } catch (err) {
      alert('Camera error: ' + err.message + '\n\nEnsure HTTPS and camera permission.');
    }
  });

  function stopCamera() {
    state.cameraActive = false;
    clearTimeout(state.frameTimer);
    cancelAnimationFrame(state.animFrame);
    state.smoothFace = null;
    noFaceCount = 0;

    if (video.srcObject) {
      video.srcObject.getTracks().forEach(t => t.stop());
      video.srcObject = null;
    }
    video.style.transform = '';

    const wrap = document.getElementById('cameraWrap');
    if (state.displayCanvas && wrap.contains(state.displayCanvas)) {
      wrap.removeChild(state.displayCanvas);
    }
    state.displayCanvas = null;
    state.sendCanvas = null;

    video.style.display = 'block';
    processedImg.style.display = 'none';
    cameraPlaceholder.classList.remove('hidden');
    startBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg> Start Camera`;
    startBtn.classList.remove('active');
    lipRow.classList.add('disabled');
    blushRow.classList.add('disabled');
    eyeRow.classList.add('disabled');

    resetPipeline();
    faceDot.classList.remove('active');
    faceStatus.textContent = 'No Face';
    skinToneEl.textContent = '—';
    itaBadge.textContent = 'ITA —°';
    skinDot.style.background = '#c68642';
    skinDot.style.boxShadow = 'none';
    state.currentSkinTone = null;
    recsEl.innerHTML = '<div class="recs-placeholder">Start the camera to get personalized recommendations</div>';
  }

  // ── PIPELINE ──
  function updatePipeline(steps) {
    for (const [key, elId] of Object.entries(STEP_MAP)) {
      const el = document.getElementById(elId);
      if (el) el.classList.toggle('done', !!steps[key]);
    }
  }
  function resetPipeline() {
    Object.values(STEP_MAP).forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('done');
    });
  }

  // ── TOGGLES ──
  lipstickToggle.addEventListener('change',  () => { state.lipstickOn  = lipstickToggle.checked;  updateMakeupRowState(); });
  blushToggle.addEventListener('change',     () => { state.blushOn     = blushToggle.checked;     updateMakeupRowState(); });
  eyeshadowToggle.addEventListener('change', () => { state.eyeshadowOn = eyeshadowToggle.checked; updateMakeupRowState(); });

  function updateMakeupRowState() {
    [[lipRow, state.lipstickOn], [blushRow, state.blushOn], [eyeRow, state.eyeshadowOn]]
      .forEach(([row, isOn]) => {
        row.querySelectorAll('.swatch').forEach(s => {
          s.style.opacity = isOn ? '1' : '0.4';
          s.style.pointerEvents = isOn ? 'auto' : 'none';
        });
      });
  }

  // ── SWATCHES ──
  function setupSwatches(id, key) {
    document.getElementById(id).addEventListener('click', e => {
      const sw = e.target.closest('.swatch');
      if (!sw) return;
      document.querySelectorAll(`#${id} .swatch`).forEach(s => s.classList.remove('selected'));
      sw.classList.add('selected');
      state[key] = sw.dataset.color;
    });
  }
  setupSwatches('lipS',   'lipColor');
  setupSwatches('blushS', 'blushColor');
  setupSwatches('eyeS',   'eyeColor');

  // ── OPACITY ──
  opacitySlider.addEventListener('input', () => {
    const val = parseInt(opacitySlider.value);
    opacityValue.textContent = val + '%';
    state.opacity = val / 100;
  });

  // ── RECOMMENDATIONS ──
  async function loadRecommendations(tone) {
    recsEl.innerHTML = '<div class="recs-placeholder" style="color:var(--pink)">Loading…</div>';
    try {
      const res  = await fetch(`/recommendations?skin_tone=${encodeURIComponent(tone)}`);
      const data = await res.json();
      renderRecommendations(data);
    } catch (e) { console.warn(e); }
  }

  function renderRecommendations(data) {
    const products = data.products || {};
    const keys = Object.keys(products);
    if (!keys.length) { recsEl.innerHTML = '<div class="recs-placeholder">No products found.</div>'; return; }
    let html = '';
    for (const cat of keys) {
      const items = products[cat];
      if (!items?.length) continue;
      html += `<div class="recs-category"><div class="recs-cat-title">${cat}</div><div class="product-list">`;
      for (const p of items) {
        html += `<div class="product-item">
          <div class="product-swatch" style="background:${p.shade}"></div>
          <div class="product-info">
            <div class="product-brand">${esc(p.brand)}</div>
            <div class="product-name">${esc(p.name)}</div>
          </div>
          <div class="product-price">${esc(p.price)}</div>
          ${cat === 'Lipstick' ? `<button class="try-btn" data-shade="${p.shade}">Try On</button>` : ''}
        </div>`;
      }
      html += `</div></div>`;
    }
    recsEl.innerHTML = html;
    recsEl.querySelectorAll('.try-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.lipColor = btn.dataset.shade;
        document.querySelectorAll('#lipS .swatch').forEach(sw =>
          sw.classList.toggle('selected', sw.dataset.color === state.lipColor));
        if (!state.lipstickOn) {
          lipstickToggle.checked = true;
          state.lipstickOn = true;
          updateMakeupRowState();
        }
      });
    });
  }

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  updateMakeupRowState();
})();
                
