/* GlowAI — app.js */
(function () {
  'use strict';

  // ── STATE ──
  const state = {
    cameraActive: false,
    streaming: false,
    currentSkinTone: null,
    lipColor: '#FF0000',
    blushColor: '#FFB7C5',
    eyeColor: '#B46482',
    opacity: 0.5,
    lipstickOn: false,
    blushOn: false,
    eyeshadowOn: false,
    frameTimer: null,
    canvas: null,
    ctx: null,
  };

  // Skin tone → hex color for dot
  const TONE_COLORS = {
    'Very Fair': '#F5DEB3',
    'Fair': '#E8C99A',
    'Medium': '#C68642',
    'Olive': '#A0785A',
    'Tan/Brown': '#7A4B2A',
    'Dark': '#3D1F10',
  };

  // ── ELEMENTS ──
  const video = document.getElementById('video');
  const processedImg = document.getElementById('processedImg');
  const startBtn = document.getElementById('startBtn');
  const skinToneEl = document.getElementById('skinTone');
  const skinDot = document.getElementById('skinDot');
  const itaBadge = document.getElementById('itaBadge');
  const cameraPlaceholder = document.getElementById('cameraPlaceholder');
  const faceDot = document.getElementById('faceDot');
  const faceStatus = document.getElementById('faceStatus');
  const opacitySlider = document.getElementById('opacitySlider');
  const opacityValue = document.getElementById('opacityValue');
  const lipstickToggle = document.getElementById('lipstickToggle');
  const blushToggle = document.getElementById('blushToggle');
  const eyeshadowToggle = document.getElementById('eyeshadowToggle');
  const lipRow = document.getElementById('lipRow');
  const blushRow = document.getElementById('blushRow');
  const eyeRow = document.getElementById('eyeRow');
  const recsEl = document.getElementById('recommendations');
  const stepFace = document.getElementById('step-face');
  const stepLandmark = document.getElementById('step-landmark');
  const stepSkin = document.getElementById('step-skin');
  const stepMakeup = document.getElementById('step-makeup');
  const stepRecs = document.getElementById('step-recs');

  // ── CANVAS SETUP ──
  function initCanvas() {
    state.canvas = document.createElement('canvas');
    state.canvas.width = 320;
    state.canvas.height = 240;
    state.ctx = state.canvas.getContext('2d');
  }

  // ── TOGGLE HANDLERS ──
  lipstickToggle.addEventListener('change', () => {
    state.lipstickOn = lipstickToggle.checked;
    updateMakeupRowState();
  });
  blushToggle.addEventListener('change', () => {
    state.blushOn = blushToggle.checked;
    updateMakeupRowState();
  });
  eyeshadowToggle.addEventListener('change', () => {
    state.eyeshadowOn = eyeshadowToggle.checked;
    updateMakeupRowState();
  });

  function updateMakeupRowState() {
    // Rows are only interactive when camera is active
    // Swatches dim when toggle is off
    const setRowActive = (row, toggle, isActive) => {
      const swatches = row.querySelectorAll('.swatch');
      swatches.forEach(s => {
        s.style.opacity = isActive ? '1' : '0.4';
        s.style.pointerEvents = isActive ? 'auto' : 'none';
      });
    };
    setRowActive(lipRow, lipstickToggle, state.lipstickOn);
    setRowActive(blushRow, blushToggle, state.blushOn);
    setRowActive(eyeRow, eyeshadowToggle, state.eyeshadowOn);
  }

  // ── SWATCH SELECTION ──
  function setupSwatches(containerId, colorKey) {
    const container = document.getElementById(containerId);
    container.addEventListener('click', (e) => {
      const sw = e.target.closest('.swatch');
      if (!sw) return;
      container.querySelectorAll('.swatch').forEach(s => s.classList.remove('selected'));
      sw.classList.add('selected');
      state[colorKey] = sw.dataset.color;
    });
  }
  setupSwatches('lipS', 'lipColor');
  setupSwatches('blushS', 'blushColor');
  setupSwatches('eyeS', 'eyeColor');

  // ── OPACITY SLIDER ──
  opacitySlider.addEventListener('input', () => {
    const val = parseInt(opacitySlider.value);
    opacityValue.textContent = val + '%';
    state.opacity = val / 100;
  });

  // ── START CAMERA ──
  startBtn.addEventListener('click', async () => {
    if (state.cameraActive) {
      stopCamera();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      state.cameraActive = true;
      state.streaming = true;
      cameraPlaceholder.classList.add('hidden');
      startBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Stop Camera`;
      startBtn.classList.add('active');
      // Enable makeup rows
      lipRow.classList.remove('disabled');
      blushRow.classList.remove('disabled');
      eyeRow.classList.remove('disabled');
      initCanvas();
      scheduleNextFrame();
    } catch (err) {
      alert('Camera access denied or unavailable. Please allow camera access and use HTTPS.');
      console.error(err);
    }
  });

  function stopCamera() {
    state.cameraActive = false;
    state.streaming = false;
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
    itaBadge.textContent = 'ITA —°';
    skinDot.style.background = '#c68642';
    state.currentSkinTone = null;
    recsEl.innerHTML = '<div class="recs-placeholder">Start the camera to get personalized recommendations</div>';
  }

  // ── FRAME CAPTURE & SEND ──
  function scheduleNextFrame() {
    if (!state.cameraActive) return;
    state.frameTimer = setTimeout(captureAndSend, 150);
  }

  async function captureAndSend() {
    if (!state.cameraActive || !video.videoWidth) {
      scheduleNextFrame();
      return;
    }
    try {
      const ctx = state.ctx;
      // Mirror the image
      ctx.save();
      ctx.translate(320, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, 320, 240);
      ctx.restore();

      const imageData = state.canvas.toDataURL('image/jpeg', 0.4);
      const settings = {
        lip_color: state.lipColor,
        blush_color: state.blushColor,
        eye_color: state.eyeColor,
        opacity: state.opacity,
        lipstick: state.lipstickOn,
        blush: state.blushOn,
        eyeshadow: state.eyeshadowOn,
      };

      const res = await fetch('/process_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageData, settings }),
      });
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      handleFrameResponse(data);
    } catch (err) {
      console.warn('Frame error:', err);
    } finally {
      scheduleNextFrame();
    }
  }

  function handleFrameResponse(data) {
    if (data.processed_image) {
      processedImg.src = data.processed_image;
      processedImg.style.display = 'block';
      video.style.display = 'none';
    }

    // Face indicator
    if (data.face_detected) {
      faceDot.classList.add('active');
      faceStatus.textContent = 'Face Found';
    } else {
      faceDot.classList.remove('active');
      faceStatus.textContent = 'No Face';
    }

    // Skin tone
    if (data.skin_tone) {
      skinToneEl.textContent = data.skin_tone;
      const toneColor = TONE_COLORS[data.skin_tone] || '#c68642';
      skinDot.style.background = toneColor;
      skinDot.style.boxShadow = `0 0 12px ${toneColor}55`;
      if (data.ita_value !== null && data.ita_value !== undefined) {
        itaBadge.textContent = `ITA ${data.ita_value}°`;
      }
      if (data.skin_tone !== state.currentSkinTone) {
        state.currentSkinTone = data.skin_tone;
        loadRecommendations(data.skin_tone);
      }
    }

    // Pipeline
    updatePipeline(data.pipeline_steps || {});
  }

  // ── PIPELINE ──
  const STEP_MAP = {
    face_detection: 'step-face',
    landmark_extraction: 'step-landmark',
    skin_tone: 'step-skin',
    makeup_application: 'step-makeup',
    recommendations: 'step-recs',
  };

  function updatePipeline(steps) {
    for (const [key, elId] of Object.entries(STEP_MAP)) {
      const el = document.getElementById(elId);
      if (!el) continue;
      if (steps[key]) {
        el.classList.add('done');
      } else {
        el.classList.remove('done');
      }
    }
  }

  function resetPipeline() {
    Object.values(STEP_MAP).forEach(elId => {
      const el = document.getElementById(elId);
      if (el) el.classList.remove('done');
    });
  }

  // ── RECOMMENDATIONS ──
  async function loadRecommendations(skinTone) {
    try {
      const res = await fetch(`/recommendations?skin_tone=${encodeURIComponent(skinTone)}`);
      const data = await res.json();
      renderRecommendations(data);
    } catch (err) {
      console.warn('Recs error:', err);
    }
  }

  function renderRecommendations(data) {
    const products = data.products || {};
    const keys = Object.keys(products);
    if (keys.length === 0) {
      recsEl.innerHTML = '<div class="recs-placeholder">No products found for this skin tone.</div>';
      return;
    }
    let html = '';
    for (const category of keys) {
      const items = products[category];
      if (!items || items.length === 0) continue;
      html += `<div class="recs-category">
        <div class="recs-cat-title">${category}</div>
        <div class="product-list">`;
      for (const p of items) {
        html += `<div class="product-item">
          <div class="product-swatch" style="background:${p.shade}"></div>
          <div class="product-info">
            <div class="product-brand">${escHtml(p.brand)}</div>
            <div class="product-name">${escHtml(p.name)}</div>
          </div>
          <div class="product-price">${escHtml(p.price)}</div>
          ${category === 'Lipstick'
            ? `<button class="try-btn" data-shade="${p.shade}" data-type="lip">Try On</button>`
            : ''}
        </div>`;
      }
      html += `</div></div>`;
    }
    recsEl.innerHTML = html;

    // Wire up Try On buttons
    recsEl.querySelectorAll('.try-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const shade = btn.dataset.shade;
        // Apply shade to lip color
        state.lipColor = shade;
        // Highlight swatch in lip panel
        document.querySelectorAll('#lipS .swatch').forEach(sw => {
          sw.classList.toggle('selected', sw.dataset.color === shade);
        });
        // Optionally enable lipstick
        if (!state.lipstickOn) {
          lipstickToggle.checked = true;
          state.lipstickOn = true;
          updateMakeupRowState();
        }
      });
    });
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // ── INITIAL MAKEUP ROW STATE ──
  updateMakeupRowState();

})();
