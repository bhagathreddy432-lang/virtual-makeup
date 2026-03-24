/* GlowAI — app.js v4 */
(function () {
  'use strict';

  const state = {
    cameraActive: false,
    currentSkinTone: null,
    lipColor:    '#FF0000',
    blushColor:  '#FFB7C5',
    eyeColor:    '#B46482',
    opacity:     0.5,
    lipstickOn:  false,
    blushOn:     false,
    eyeshadowOn: false,
    isSending:   false,
    frameTimer:  null,
    canvas:      null,
    ctx:         null,
    // Double-buffer: two Image objects, swap on load
    bufA:        new Image(),
    bufB:        new Image(),
    activeBuf:   'A',
  };

  const TONE_COLORS = {
    'Very Fair':'#F5DEB3','Fair':'#E8C99A','Medium':'#C68642',
    'Olive':'#A0785A','Tan/Brown':'#7A4B2A','Dark':'#3D1F10',
  };

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
    face_detection:'step-face', landmark_extraction:'step-landmark',
    skin_tone:'step-skin', makeup_application:'step-makeup', recommendations:'step-recs',
  };

  // ── CANVAS SETUP ──
  function initCanvas() {
    state.canvas = document.createElement('canvas');
    // Send at 480×360 — good detection quality, fast upload
    state.canvas.width  = 480;
    state.canvas.height = 360;
    state.ctx = state.canvas.getContext('2d');
  }

  // ── SEND LOOP ──
  // Fires immediately after previous response arrives — no fixed timer gaps
  // This gives the fastest possible frame rate within network latency
  function startLoop() {
    if (!state.cameraActive) return;
    sendFrame();
  }

  async function sendFrame() {
    if (!state.cameraActive) return;
    if (!video.videoWidth) {
      state.frameTimer = setTimeout(sendFrame, 50);
      return;
    }
    if (state.isSending) {
      state.frameTimer = setTimeout(sendFrame, 30);
      return;
    }
    state.isSending = true;
    try {
      const ctx = state.ctx;
      // Mirror horizontally — matches what user sees
      ctx.save();
      ctx.translate(state.canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, state.canvas.width, state.canvas.height);
      ctx.restore();

      // Quality 0.82 — high enough to look great, low enough to be fast
      const imageData = state.canvas.toDataURL('image/jpeg', 0.82);

      const res = await fetch('/process_frame', {
        method:  'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({
          image: imageData,
          settings: {
            lip_color:   state.lipColor,
            blush_color: state.blushColor,
            eye_color:   state.eyeColor,
            opacity:     state.opacity,
            lipstick:    state.lipstickOn,
            blush:       state.blushOn,
            eyeshadow:   state.eyeshadowOn,
          }
        }),
      });

      if (res.ok) {
        const data = await res.json();
        handleResponse(data);
      }
    } catch(e) {
      console.warn(e);
    } finally {
      state.isSending = false;
      // Chain next frame immediately after response
      if (state.cameraActive) {
        // Small delay only to avoid CPU spin if server is very fast locally
        state.frameTimer = setTimeout(sendFrame, 16);
      }
    }
  }

  function handleResponse(data) {
    if (data.processed_image) {
      // Double-buffer swap: load into inactive buffer,
      // flip to active only when fully decoded — zero flicker
      const next = state.activeBuf === 'A' ? state.bufB : state.bufA;
      next.onload = () => {
        processedImg.src = next.src;
        processedImg.style.display = 'block';
        video.style.display = 'none';
        state.activeBuf = state.activeBuf === 'A' ? 'B' : 'A';
      };
      next.src = data.processed_image;
    }

    // Face badge
    if (data.face_detected) {
      faceDot.classList.add('active');
      faceStatus.textContent = 'Face Found';
    } else {
      faceDot.classList.remove('active');
      faceStatus.textContent = 'Scanning…';
    }

    // Skin tone
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

  // ── CAMERA ──
  startBtn.addEventListener('click', async () => {
    if (state.cameraActive) { stopCamera(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width:     {ideal:1280, min:640},
          height:    {ideal:720,  min:480},
          frameRate: {ideal:30},
          facingMode: 'user',
        },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      state.cameraActive = true;

      cameraPlaceholder.classList.add('hidden');
      startBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Stop Camera`;
      startBtn.classList.add('active');
      lipRow.classList.remove('disabled');
      blushRow.classList.remove('disabled');
      eyeRow.classList.remove('disabled');

      // Show native video first — crisp while first frame loads
      video.style.display = 'block';
      processedImg.style.display = 'none';

      initCanvas();
      startLoop();
    } catch(err) {
      alert('Camera error: ' + err.message);
    }
  });

  function stopCamera() {
    state.cameraActive = false;
    clearTimeout(state.frameTimer);
    if (video.srcObject) {
      video.srcObject.getTracks().forEach(t => t.stop());
      video.srcObject = null;
    }
    processedImg.style.display = 'none';
    video.style.display = 'block';
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
    itaBadge.textContent   = 'ITA —°';
    skinDot.style.background = '#c68642';
    skinDot.style.boxShadow  = 'none';
    state.currentSkinTone = null;
    recsEl.innerHTML = '<div class="recs-placeholder">Start the camera to get personalized recommendations</div>';
  }

  // ── PIPELINE ──
  function updatePipeline(steps) {
    for (const [k,id] of Object.entries(STEP_MAP)) {
      const el = document.getElementById(id);
      if (el) el.classList.toggle('done', !!steps[k]);
    }
  }
  function resetPipeline() {
    Object.values(STEP_MAP).forEach(id => {
      const el = document.getElementById(id);
      if (el) el.classList.remove('done');
    });
  }

  // ── TOGGLES ──
  lipstickToggle.addEventListener('change',  () => { state.lipstickOn  = lipstickToggle.checked;  updateRows(); });
  blushToggle.addEventListener('change',     () => { state.blushOn     = blushToggle.checked;     updateRows(); });
  eyeshadowToggle.addEventListener('change', () => { state.eyeshadowOn = eyeshadowToggle.checked; updateRows(); });

  function updateRows() {
    [[lipRow,state.lipstickOn],[blushRow,state.blushOn],[eyeRow,state.eyeshadowOn]]
      .forEach(([row,on]) => row.querySelectorAll('.swatch').forEach(s => {
        s.style.opacity = on ? '1' : '0.4';
        s.style.pointerEvents = on ? 'auto' : 'none';
      }));
  }

  // ── SWATCHES ──
  ['lipS','blushS','eyeS'].forEach((id,i) => {
    const key = ['lipColor','blushColor','eyeColor'][i];
    document.getElementById(id).addEventListener('click', e => {
      const sw = e.target.closest('.swatch');
      if (!sw) return;
      document.querySelectorAll(`#${id} .swatch`).forEach(s => s.classList.remove('selected'));
      sw.classList.add('selected');
      state[key] = sw.dataset.color;
    });
  });

  // ── OPACITY ──
  opacitySlider.addEventListener('input', () => {
    const v = parseInt(opacitySlider.value);
    opacityValue.textContent = v + '%';
    state.opacity = v / 100;
  });

  // ── RECOMMENDATIONS ──
  async function loadRecommendations(tone) {
    recsEl.innerHTML = '<div class="recs-placeholder" style="color:var(--pink)">Loading…</div>';
    try {
      const data = await (await fetch(`/recommendations?skin_tone=${encodeURIComponent(tone)}`)).json();
      renderRecs(data);
    } catch(e) { console.warn(e); }
  }

  function renderRecs(data) {
    const cats = data.products || {};
    if (!Object.keys(cats).length) {
      recsEl.innerHTML = '<div class="recs-placeholder">No products found.</div>'; return;
    }
    let html = '';
    for (const cat of Object.keys(cats)) {
      const items = cats[cat];
      if (!items?.length) continue;
      html += `<div class="recs-category"><div class="recs-cat-title">${cat}</div><div class="product-list">`;
      for (const p of items) {
        html += `<div class="product-item">
          <div class="product-swatch" style="background:${p.shade}"></div>
          <div class="product-info">
            <div class="product-brand">${x(p.brand)}</div>
            <div class="product-name">${x(p.name)}</div>
          </div>
          <div class="product-price">${x(p.price)}</div>
          ${cat==='Lipstick'?`<button class="try-btn" data-shade="${p.shade}">Try On</button>`:''}
        </div>`;
      }
      html += `</div></div>`;
    }
    recsEl.innerHTML = html;
    recsEl.querySelectorAll('.try-btn').forEach(btn => btn.addEventListener('click', () => {
      state.lipColor = btn.dataset.shade;
      document.querySelectorAll('#lipS .swatch').forEach(s =>
        s.classList.toggle('selected', s.dataset.color === state.lipColor));
      if (!state.lipstickOn) {
        lipstickToggle.checked = true;
        state.lipstickOn = true;
        updateRows();
      }
    }));
  }

  function x(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  updateRows();
})();
