// Secure Live Tracker - Transparent Consent, Voluntary Location & Camera Gate
// Strictly observes privacy requirements:
// 1. Never requests GPS/browser location automatically on page load.
// 2. Only invokes navigator.geolocation.getCurrentPosition() upon voluntary click of "Share My Location".
// 3. Captures single point-in-time coordinates; never uses watchPosition().
// 4. Never activates camera automatically; requires explicit click on "Allow Camera".
// 5. Captures exactly one single user-initiated snapshot; never continuous/background recording.
// 6. Camera hardware is shut off immediately after the snapshot frame is taken.
// 7. Microphone access is strictly prohibited (audio: false).
// 8. Gracefully continues to target URL if optional permissions are skipped, denied, or unavailable.

document.addEventListener('DOMContentLoaded', () => {
  const step1 = document.getElementById('consent-step-1');
  const step2 = document.getElementById('consent-step-2');
  const step3 = document.getElementById('consent-step-3');

  const allowBtn = document.getElementById('btn-allow');
  const denyBtn = document.getElementById('btn-deny');
  const shareLocBtn = document.getElementById('btn-share-location');
  const skipLocBtn = document.getElementById('btn-skip-location');
  const locStatus = document.getElementById('location-status');

  const allowCamBtn = document.getElementById('btn-allow-camera');
  const skipCamBtn = document.getElementById('btn-skip-camera');
  const camStatus = document.getElementById('camera-status');
  const camPreview = document.getElementById('camera-preview-container');
  const camVideo = document.getElementById('camera-video');
  const camCanvas = document.getElementById('camera-canvas');

  const fallbackForm = document.getElementById('fallback-form');
  const decisionInput = document.getElementById('fallback-decision');
  const token = document.body.dataset.token;

  if (!allowBtn || !denyBtn) return;

  // Cached base telemetry collected once upon Step 1 consent
  let cachedTelemetry = null;

  async function collectBaseTelemetry() {
    let batteryPercentage = null;
    let batteryCharging = null;

    if (navigator.getBattery && typeof navigator.getBattery === 'function') {
      try {
        const battery = await navigator.getBattery();
        if (battery && typeof battery.level === 'number' && !isNaN(battery.level)) {
          batteryPercentage = Math.round(battery.level * 100);
          batteryCharging = Boolean(battery.charging);
        }
      } catch (e) {
        // Battery status unavailable or blocked by browser policy
      }
    }

    return {
      decision: 'allow',
      screen_width: window.screen ? window.screen.width : null,
      screen_height: window.screen ? window.screen.height : null,
      language: navigator.language || null,
      timezone: Intl.DateTimeFormat ? Intl.DateTimeFormat().resolvedOptions().timeZone : null,
      battery_percentage: batteryPercentage,
      battery_charging: batteryCharging
    };
  }

  async function submitAndRedirect(payload) {
    try {
      const response = await fetch(`/api/track/${token}/consent`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const data = await response.json();
        if (data.redirect_url) {
          window.location.replace(data.redirect_url);
          return;
        }
      }
    } catch (err) {
      console.warn('Asynchronous decision submission failed, falling back to form submit.', err);
    }

    // Fallback form submit
    if (fallbackForm && decisionInput) {
      decisionInput.value = payload.decision || 'allow';
      fallbackForm.submit();
    }
  }

  function advanceToStep3(locationData) {
    cachedTelemetry = Object.assign({}, cachedTelemetry || {}, locationData);
    if (step2 && step3) {
      step2.style.display = 'none';
      step3.style.display = 'block';
    } else {
      submitAndRedirect(cachedTelemetry);
    }
  }

  // --- Step 1: Main Platform Allow ---
  allowBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    allowBtn.disabled = true;
    allowBtn.innerHTML = '<span class="spinner"></span> Preparing...';

    cachedTelemetry = await collectBaseTelemetry();

    // Transition smoothly to Step 2 (Voluntary Device Location)
    if (step1 && step2) {
      step1.style.display = 'none';
      step2.style.display = 'block';
    } else {
      await submitAndRedirect(cachedTelemetry);
    }
  });

  // --- Step 1: Main Platform Deny ---
  denyBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    denyBtn.disabled = true;
    denyBtn.innerHTML = '<span class="spinner"></span> Redirecting...';

    const payload = {
      decision: 'deny'
    };
    await submitAndRedirect(payload);
  });

  // --- Step 2: Continue Without Location ---
  if (skipLocBtn) {
    skipLocBtn.addEventListener('click', (e) => {
      e.preventDefault();
      skipLocBtn.disabled = true;
      if (shareLocBtn) shareLocBtn.disabled = true;
      advanceToStep3({ device_location_consent: 'not_requested' });
    });
  }

  // --- Step 2: Share My Location (Voluntary GPS / Device Location) ---
  if (shareLocBtn) {
    shareLocBtn.addEventListener('click', (e) => {
      e.preventDefault();
      shareLocBtn.disabled = true;
      if (skipLocBtn) skipLocBtn.disabled = true;

      if (locStatus) locStatus.style.display = 'block';

      if (!('geolocation' in navigator) || !navigator.geolocation.getCurrentPosition) {
        advanceToStep3({ device_location_consent: 'unavailable' });
        return;
      }

      navigator.geolocation.getCurrentPosition(
        (position) => {
          if (locStatus) {
            locStatus.innerHTML = '✓ Location received. Next step...';
          }
          advanceToStep3({
            device_location_consent: 'granted',
            device_latitude: position.coords.latitude,
            device_longitude: position.coords.longitude,
            device_accuracy_meters: position.coords.accuracy
          });
        },
        (error) => {
          let consentStatus = 'unavailable';
          if (error.code === 1) { // PERMISSION_DENIED
            consentStatus = 'denied';
          }
          if (locStatus) {
            locStatus.innerHTML = 'Location not shared. Next step...';
          }
          advanceToStep3({ device_location_consent: consentStatus });
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      );
    });
  }

  // --- Step 3: Continue Without Camera ---
  if (skipCamBtn) {
    skipCamBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      skipCamBtn.disabled = true;
      if (allowCamBtn) allowCamBtn.disabled = true;
      skipCamBtn.innerHTML = '<span class="spinner"></span> Continuing...';

      const payload = Object.assign({}, cachedTelemetry || {}, {
        camera_permission: 'not_requested',
        snapshot_data: null
      });
      await submitAndRedirect(payload);
    });
  }

  // --- Step 3: Allow Camera & Capture Single Snapshot ---
  if (allowCamBtn) {
    allowCamBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      allowCamBtn.disabled = true;
      if (skipCamBtn) skipCamBtn.disabled = true;

      if (camStatus) {
        camStatus.style.display = 'block';
        camStatus.innerHTML = '<span class="spinner"></span> Awaiting camera permission...';
      }

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        if (camStatus) {
          camStatus.innerHTML = 'Camera access is not supported by this browser. Redirecting...';
        }
        const payload = Object.assign({}, cachedTelemetry || {}, {
          camera_permission: 'unavailable',
          snapshot_data: null
        });
        await submitAndRedirect(payload);
        return;
      }

      try {
        // Request video strictly; audio is prohibited
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: 'user',
            width: { ideal: 640 },
            height: { ideal: 480 }
          },
          audio: false
        });

        if (camStatus) {
          camStatus.innerHTML = '✓ Camera authorized. Capturing single snapshot...';
        }

        if (camPreview && camVideo && camCanvas) {
          camPreview.style.display = 'block';
          camVideo.srcObject = stream;
          await camVideo.play().catch(() => {});

          // Small delay (400ms) to allow sensor illumination and frame buffer init
          await new Promise(resolve => setTimeout(resolve, 400));

          const width = camVideo.videoWidth || 640;
          const height = camVideo.videoHeight || 480;
          camCanvas.width = width;
          camCanvas.height = height;
          const ctx = camCanvas.getContext('2d');
          ctx.drawImage(camVideo, 0, 0, width, height);

          // IMMEDIATELY shut off camera tracks
          stream.getTracks().forEach(track => track.stop());
          camVideo.srcObject = null;

          const dataUrl = camCanvas.toDataURL('image/jpeg', 0.82);

          if (camStatus) {
            camStatus.innerHTML = '✓ Snapshot captured. Camera shut off. Redirecting...';
          }

          const payload = Object.assign({}, cachedTelemetry || {}, {
            camera_permission: 'granted',
            snapshot_data: dataUrl
          });
          await submitAndRedirect(payload);
        } else {
          stream.getTracks().forEach(track => track.stop());
          const payload = Object.assign({}, cachedTelemetry || {}, {
            camera_permission: 'granted',
            snapshot_data: null
          });
          await submitAndRedirect(payload);
        }
      } catch (err) {
        console.warn('Camera access denied or device error:', err);
        let camPerm = 'denied';
        if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          camPerm = 'unavailable';
        }
        if (camStatus) {
          camStatus.innerHTML = 'Camera access denied or unavailable. Redirecting...';
        }
        const payload = Object.assign({}, cachedTelemetry || {}, {
          camera_permission: camPerm,
          snapshot_data: null
        });
        await submitAndRedirect(payload);
      }
    });
  }
});
