// Secure Live Tracker - Transparent Consent & Voluntary Location Gate
// Strictly observes privacy requirements:
// 1. Never requests GPS/browser location automatically on page load.
// 2. Only invokes navigator.geolocation.getCurrentPosition() upon voluntary click of "Share My Location".
// 3. Captures single point-in-time coordinates; never uses watchPosition().
// 4. Gracefully continues to target URL if location is skipped, denied, or unavailable.

document.addEventListener('DOMContentLoaded', () => {
  const step1 = document.getElementById('consent-step-1');
  const step2 = document.getElementById('consent-step-2');

  const allowBtn = document.getElementById('btn-allow');
  const denyBtn = document.getElementById('btn-deny');
  const shareLocBtn = document.getElementById('btn-share-location');
  const skipLocBtn = document.getElementById('btn-skip-location');
  const locStatus = document.getElementById('location-status');
  const step2Actions = document.getElementById('step-2-actions');

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
      // Direct submission fallback if step 2 card is missing
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
    skipLocBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      skipLocBtn.disabled = true;
      if (shareLocBtn) shareLocBtn.disabled = true;
      skipLocBtn.innerHTML = '<span class="spinner"></span> Continuing...';

      const payload = Object.assign({}, cachedTelemetry || {}, {
        device_location_consent: 'not_requested'
      });
      await submitAndRedirect(payload);
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
        // Geolocation not supported in this browser
        const payload = Object.assign({}, cachedTelemetry || {}, {
          device_location_consent: 'unavailable'
        });
        submitAndRedirect(payload);
        return;
      }

      // Explicit single point-in-time query with standard options
      navigator.geolocation.getCurrentPosition(
        (position) => {
          // Success: user allowed location in native browser prompt
          if (locStatus) {
            locStatus.innerHTML = '✓ Location received. Redirecting to destination...';
          }
          const payload = Object.assign({}, cachedTelemetry || {}, {
            device_location_consent: 'granted',
            device_latitude: position.coords.latitude,
            device_longitude: position.coords.longitude,
            device_accuracy_meters: position.coords.accuracy
          });
          submitAndRedirect(payload);
        },
        (error) => {
          // Error or Denied in native browser prompt
          let consentStatus = 'unavailable';
          if (error.code === 1) { // PERMISSION_DENIED
            consentStatus = 'denied';
          }
          if (locStatus) {
            locStatus.innerHTML = 'Location not shared. Continuing to destination...';
          }
          const payload = Object.assign({}, cachedTelemetry || {}, {
            device_location_consent: consentStatus
          });
          submitAndRedirect(payload);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      );
    });
  }
});
