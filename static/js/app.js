/* GlowAI — app.js v2 — Premium Camera & Smooth Experience */
(function () {
  'use strict';

  // ── STATE ──
  const state = {
    cameraActive: false,
    currentSkinTone: null,
    lipColor: '#FF0000',
    blushColor: '#FFB7C5',
    eyeColor: '#B46482',
    opacity: 0.5,
    lipstickOn: false,
    blushOn: false,
    eyeshadowOn: false,
    frameTimer: null,
    sendCanvas: null,   // low-res canvas sent to server
    sendCtx: null,
    displayCanvas: null, // full-res display canvas
    displayCtx: null,
    isSending: false,    // prevent overlapping requests
    lastProcessed: null, // last processed image src
    animFrame: null,
    videoWidth: 0,
    videoHeight: 0,
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
  const video           = document.getElementById('video');
  const processedImg    = document.getElementById('processedImg');
  const startBtn        = document.getElementById('startBtn');
  const skinToneEl      = document.getElementById('skinTone');
  const skinDot         = document.getElementById('skinDot');
  const itaBadge        = document.getElementById('itaBadge');
  const cameraPlaceholder = document.getElementById('cameraPlaceholder');
  const faceDot         = document.getElementById('faceDot');
  const faceStatus      = document.getElementById('faceStatus');
  const opacitySlider   = document.getElementById('opacitySlider');
  const opacityValue    = document.getElementById('opacityValue');
  const lipstickToggle  = document.getElementById('lipstickToggle');
  const blushToggle     = document.getElementById('blushToggle');
  const eyeshadowToggle = document.getElementById('eyeshadowToggle');
  const lipRow          = document.getElementById('lipRow');
  const blushRow        = document.getElementById('blushRow');
  const eyeRow          = document.getElementById('eyeRow');
  const recsEl          = document.getElementById('recommendations');

  const STEP_MAP = {
    face_detection:      'step-face',
    landmark_extraction: 'step-landmark',
    skin_tone:           'step-skin',
    makeup_application:  'step-makeup',
    recommendations:     'step-recs',
  };

  // ── CANVAS INIT ──
  function initCanvases() {
    // Send canvas: 480x360 — good balance of quality vs speed
    state.sendCanvas = document.createElement('canvas');
    state.sendCanvas.width  = 480;
    state.sendCanvas.height = 360;
    state.sendCtx = state.sendCanvas.getContext('2d');

    // Display canvas: full resolution overlay for smooth live preview
    state.displayCanvas = document.createElement('canvas');
    state.displayCanvas.style.cssText = `
      position:absolute;inset:0;width:100%;height:100%;
      object-fit:cover;border-radius:inherit;z-index:2;
    `;
    document.getElementById('cameraWrap').appendChild(state.displayCanvas);
    state.displayCtx = state.displayCanvas.getContext('2d');
  }

  // ── LIVE VIDEO RENDER LOOP ──
  // Draws the raw video to displayCanvas every frame for ultra-smooth preview
  // The processed overlay is blended on top when available
  let lastProcessedImage = null;
  let overlayOpacity = 0; // animate in smoothly

  function renderLoop() {
    if (!state.cameraActive) return;
    state.animFrame = requestAnimationFrame(renderLoop);

    const dCtx = state.displayCtx;
    const dCanvas = state.displayCanvas;
    if (!video.videoWidth) return;

    // Match canvas to video native size for crisp output
    if (dCanvas.width !== video.videoWidth || dCanvas.height !== video.videoHeight) {
      dCanvas.width  = video.videoWidth;
      dCanvas.height = video.videoHeight;
    }

    // Draw live video (mirrored) — always smooth
    dCtx.save();
    dCtx.translate(dCanvas.width, 0);
    dCtx.scale(-1, 1);
    dCtx.drawImage(video, 0, 0, dCanvas.width, dCanvas.height);
    dCtx.restore();

    // Blend processed overlay smoothly
    if (lastProcessedImage) {
      overlayOpacity = Math.min(1, overlayOpacity + 0.08); // fade in
      dCtx.globalAlpha = overlayOpacity;
      dCtx.drawImage(lastProcessedImage, 0, 0, dCanvas.width, dCanvas.height);
      dCtx.globalAlpha = 1;
    }
  }

  // ── FRAME SEND LOOP ── (separate from render — no blocking)
  function startSendLoop() {
    if (!state.cameraActive) return;
    state.frameTimer = setTimeout(async () => {
      if (state.cameraActive) {
        await captureAndSend();
        startSendLoop();
      }
    }, 200); // send every 200ms — fast enough, not overwhelming
  }

  async function captureAndSend() {
    if (state.isSending || !video.videoWidth) return;
    state.isSending = true;
    try {
      const sCtx = state.sendCtx;
      const sCanvas = state.sendCanvas;
      // Mirror for server processing
      sCtx.save();
      sCtx.translate(sCanvas.width, 0);
      sCtx.scale(-1, 1);
      sCtx.drawImage(video, 0, 0, sCanvas.width, sCanvas.height);
      sCtx.restore();

      // JPEG quality 0.75 — much better than 0.4, still fast enough
      const imageData = sCanvas.toDataURL('image/jpeg', 0.75);

      const settings = {
        lip_color:  state.lipColor,
        blush_color: state.blushColor,
        eye_color:  state.eyeColor,
        opacity:    state.opacity,
        lipstick:   state.lipstickOn,
        blush:      state.blushOn,
        eyeshadow:  state.eyeshadowOn,
      };

      const res = await fetch('/process_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData, settings }),
      });
      if (!res.ok) return;
      const data = await res.json();
      handleFrameResponse(data);
    } catch (e) {
      console.warn('Frame error:', e);
    } finally {
      state.isSending = false;
    }
  }

  function handleFrameResponse(data) {
    // Load processed image into an offscreen Image object
    if (data.processed_image) {
      const img = new Image();
      img.onload = () => {
        lastProcessedImage = img;
        overlayOpacity = 0; // trigger smooth fade-in
      };
      img.src = data.processed_image;
    }

    // Face indicator
    if (data.face_detected) {
      faceDot.classList.add('active');
      faceStatus.textContent = 'Face Found';
    } else {
      faceDot.classList.remove('active');
      faceStatus.textContent = 'Scanning...';
      lastProcessedImage = null; // clear overlay when no face
    }

    // Skin tone
    if (data.skin_tone) {
      skinToneEl.textContent = data.skin_tone;
      const toneColor = TONE_COLORS[data.skin_tone] || '#c68642';
      skinDot.style.background = toneColor;
      skinDot.style.boxShadow  = `0 0 12px ${toneColor}88`;
      if (data.ita_value != null) {
        itaBadge.textContent = `ITA ${data.ita_value}°`;
      }
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
      // Request highest possible quality
      const constraints = {
        video: {
          width:     { ideal: 1280, min: 640 },
          height:    { ideal: 720,  min: 480 },
          frameRate: { ideal: 30,   min: 15 },
          facingMode: 'user',
          // Advanced: disable noise reduction for clarity
          advanced: [{ torch: false }],
        },
        audio: false,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      video.srcObject = stream;
      video.style.display = 'none'; // hide raw video, we use canvas instead
      await video.play();

      state.cameraActive = true;
      cameraPlaceholder.classList.add('hidden');
      startBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Stop Camera`;
      startBtn.classList.add('active');
      lipRow.classList.remove('disabled');
      blushRow.classList.remove('disabled');
      eyeRow.classList.remove('disabled');

      initCanvases();
      renderLoop();     // starts smooth 60fps canvas preview
      startSendLoop();  // starts server processing at 200ms intervals
    } catch (err) {
      alert('Camera error: ' + err.message + '\n\nMake sure you are on HTTPS and have allowed camera access.');
    }
  });

  function stopCamera() {
    state.cameraActive = false;
    clearTimeout(state.frameTimer);
    cancelAnimationFrame(state.animFrame);
    lastProcessedImage = null;
    overlayOpacity = 0;

    if (video.srcObject) {
      video.srcObject.getTracks().forEach(t => t.stop());
      video.srcObject = null;
    }

    // Remove display canvas
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
  lipstickToggle.addEventListener('change', () => {
    state.lipstickOn = lipstickToggle.checked;
    updateMakeupRowState();
    // Reset overlay so change is visible immediately
    lastProcessedImage = null;
  });
  blushToggle.addEventListener('change', () => {
    state.blushOn = blushToggle.checked;
    updateMakeupRowState();
    lastProcessedImage = null;
  });
  eyeshadowToggle.addEventListener('change', () => {
    state.eyeshadowOn = eyeshadowToggle.checked;
    updateMakeupRowState();
    lastProcessedImage = null;
  });

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
  function setupSwatches(containerId, colorKey) {
    document.getElementById(containerId).addEventListener('click', (e) => {
      const sw = e.target.closest('.swatch');
      if (!sw) return;
      document.querySelectorAll(`#${containerId} .swatch`).forEach(s => s.classList.remove('selected'));
      sw.classList.add('selected');
      state[colorKey] = sw.dataset.color;
      lastProcessedImage = null; // force refresh
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
    lastProcessedImage = null;
  });

  // ── RECOMMENDATIONS ──
  async function loadRecommendations(skinTone) {
    recsEl.innerHTML = '<div class="recs-placeholder" style="color:var(--pink)">Loading recommendations…</div>';
    try {
      const res  = await fetch(`/recommendations?skin_tone=${encodeURIComponent(skinTone)}`);
      const data = await res.json();
      renderRecommendations(data);
    } catch (e) { console.warn('Recs error:', e); }
  }

  function renderRecommendations(data) {
    const products = data.products || {};
    const keys = Object.keys(products);
    if (!keys.length) {
      recsEl.innerHTML = '<div class="recs-placeholder">No products found.</div>';
      return;
    }
    let html = '';
    for (const cat of keys) {
      const items = products[cat];
      if (!items?.length) continue;
      html += `<div class="recs-category">
        <div class="recs-cat-title">${cat}</div>
        <div class="product-list">`;
      for (const p of items) {
        html += `<div class="product-item">
          <div class="product-swatch" style="background:${p.shade}"></div>
          <div class="product-info">
            <div class="product-brand">${esc(p.brand)}</div>
            <div class="product-name">${esc(p.name)}</div>
          </div>
          <div class="product-price">${esc(p.price)}</div>
          ${cat === 'Lipstick'
            ? `<button class="try-btn" data-shade="${p.shade}">Try On</button>`
            : ''}
        </div>`;
      }
      html += `</div></div>`;
    }
    recsEl.innerHTML = html;

    recsEl.querySelectorAll('.try-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.lipColor = btn.dataset.shade;
        document.querySelectorAll('#lipS .swatch').forEach(sw => {
          sw.classList.toggle('selected', sw.dataset.color === state.lipColor);
        });
        if (!state.lipstickOn) {
          lipstickToggle.checked = true;
          state.lipstickOn = true;
          updateMakeupRowState();
        }
        lastProcessedImage = null;
      });
    });
  }

  function esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  updateMakeupRowState();
})();
      
