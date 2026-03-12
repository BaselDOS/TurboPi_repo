const App = (() => {

async function fetchStatus() {
  const res = await fetch('/api/status', { cache: 'no-store' });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function setCardState(cardId, ok) {
  const el = document.getElementById(cardId);
  if (!el) return;
  el.style.borderColor = ok ? 'rgba(45,255,143,.45)' : 'rgba(255,59,92,.35)';
  el.style.boxShadow = ok
    ? '0 0 18px rgba(45,255,143,.08)'
    : '0 0 18px rgba(255,59,92,.06)';
}

function showError(msg) {
  const banner = document.getElementById('errorBanner');
  const txt = document.getElementById('errorText');
  if (txt) txt.textContent = msg;
  if (banner) banner.classList.remove('hidden');
}

function hideError() {
  const banner = document.getElementById('errorBanner');
  if (banner) banner.classList.add('hidden');
}

async function refreshStatus() {
  try {
    const s = await fetchStatus();
    hideError();

    setText('wifiVal', s.wifi ?? 'N/A');
    setText('ipVal', s.ip ?? 'N/A');
    setText('rosVal', s.ros ?? 'N/A');
    setText('batVal', s.battery ?? 'N/A');
    setText('camVal', s.camera ?? 'N/A');

    setCardState('wifiCard', s.wifi_ok === true);
    setCardState('rosCard', s.ros_ok === true);
    setCardState('batCard', s.battery_ok === true);
    setCardState('camCard', s.camera_ok === true);

  } catch (e) {

    showError(`Unable to fetch system status (${e.message}).`);

    setText('wifiVal', 'N/A');
    setText('ipVal', 'N/A');
    setText('rosVal', 'N/A');
    setText('batVal', 'N/A');
    setText('camVal', 'N/A');

    setCardState('wifiCard', false);
    setCardState('rosCard', false);
    setCardState('batCard', false);
    setCardState('camCard', false);
  }
}

function wireCommonButtons() {

  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) refreshBtn.addEventListener('click', refreshStatus);

  const reloadBtn = document.getElementById('reloadBtn');
  if (reloadBtn) reloadBtn.addEventListener('click', () => window.location.reload());
}

function initHome() {

  wireCommonButtons();
  refreshStatus();

  // auto refresh every 3 seconds
  setInterval(refreshStatus, 3000);
}

function initRun() {

  wireCommonButtons();
  refreshStatus();
  setInterval(refreshStatus, 3000);

  let selected = null;

  const modelLabel = document.getElementById('selectedMode');
  const joystickPanel = document.getElementById('joystickPanel');

  const cwBtn = document.getElementById("rotateCW");
  const ccwBtn = document.getElementById("rotateCCW");

  if (cwBtn) {

    cwBtn.addEventListener("mousedown", () => {
      console.log("rotate CW");
    });

    cwBtn.addEventListener("mouseup", () => {
      console.log("stop rotate");
    });
  }

  if (ccwBtn) {

    ccwBtn.addEventListener("mousedown", () => {
      console.log("rotate CCW");
    });

    ccwBtn.addEventListener("mouseup", () => {
      console.log("stop rotate");
    });
  }

  document.querySelectorAll('.mode-card').forEach(btn => {

    btn.addEventListener('click', () => {

      document.querySelectorAll('.mode-card').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');

      selected = btn.dataset.mode || null;

      if (modelLabel) modelLabel.textContent = selected ?? 'none';
    });

  });

  const startBtn = document.getElementById('startBtn');

  if (startBtn) {

    startBtn.addEventListener('click', async () => {

      if (!selected) {
        alert("Select a mode first");
        return;
      }

      try {

        const res = await fetch('/api/run_node', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ node: selected })
        });

        const data = await res.json();

        alert(data.message || "Node started");

        if (selected === "joystick") {

          if (joystickPanel) joystickPanel.classList.remove("hidden");

          initJoystick();
        }

      } catch (err) {

        alert("Failed to start node");
      }

    });

  }

  const stopBtn = document.getElementById('stopBtn');

  if (stopBtn) {

    stopBtn.addEventListener('click', async () => {

      try {

        const res = await fetch('/api/stop_node', {
          method: 'POST'
        });

        const data = await res.json();

        alert(data.message || "Node stopped");

        if (joystickPanel) joystickPanel.classList.add("hidden");

      } catch (err) {

        alert("Failed to stop node");
      }

    });

  }

}

function initJoystick() {

  const zone = document.getElementById('moveJoystick');

  const joyX = document.getElementById('joyX');
  const joyY = document.getElementById('joyY');
  const rotateCW = document.getElementById('rotateCW');
  const rotateCCW = document.getElementById('rotateCCW');
  const rotateStatus = document.getElementById('rotateStatus');
  const manager = nipplejs.create({
    zone: zone,
    mode: 'static',
    position: { left: '50%', top: '50%' },
    color: 'green',
    size: 140
  });

  let lastSend = 0;  
  manager.on('move', function(evt, data) {

  if (!data.vector) return;

  let x = data.vector.x;
  let y = data.vector.y;

  const deadzone = 0.15;

  if (Math.abs(x) < deadzone) x = 0;
  if (Math.abs(y) < deadzone) y = 0;

  x = x.toFixed(2);
  y = y.toFixed(2);

  if (joyX) joyX.textContent = x;
  if (joyY) joyY.textContent = y;

  console.log("Joystick:", x, y);

});
manager.on('end', function() {

  if (joyX) joyX.textContent = "0.00";
  if (joyY) joyY.textContent = "0.00";

  console.log("Joystick released");

});

// CAMERA JOYSTICK
const camZone = document.getElementById('camJoystick');
const camX = document.getElementById('camX');
const camY = document.getElementById('camY');
const camManager = nipplejs.create({
  zone: camZone,
  mode: 'static',
  position: { left: '50%', top: '50%' },
  color: 'blue',
  size: 140
});

let lastCamSend = 0;

camManager.on('move', function(evt, data) {

    if (!data.vector) return;

    let pan = -data.vector.x;
    let tilt = -data.vector.y;

    const deadzone = 0.15;

    if (Math.abs(pan) < deadzone) pan = 0;
    if (Math.abs(tilt) < deadzone) tilt = 0;

    pan = parseFloat(pan.toFixed(2));
    tilt = parseFloat(tilt.toFixed(2));

    if (camX) camX.textContent = pan;
    if (camY) camY.textContent = tilt;

    console.log("Camera joystick:", pan, tilt);

    const now = Date.now();
    if (now - lastCamSend > 100) {

        fetch('/api/camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                x: pan,
                y: tilt
            })
        });

        lastCamSend = now;
    }

});

camManager.on('end', function() {

    if (camX) camX.textContent = "0.00";
    if (camY) camY.textContent = "0.00";

    fetch('/api/camera', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            x: 0,
            y: 0
        })
    });

    console.log("Camera joystick released");

});
rotateCW.addEventListener('mousedown', () => {
    rotateStatus.textContent = "CW";
});

rotateCCW.addEventListener('mousedown', () => {
    rotateStatus.textContent = "CCW";
});

rotateCW.addEventListener('mouseup', () => {
    rotateStatus.textContent = "";
});

rotateCCW.addEventListener('mouseup', () => {
    rotateStatus.textContent = "";
});

rotateCW.addEventListener('touchstart', (e) => {
    e.preventDefault();
    rotateStatus.textContent = "CW";
});

rotateCW.addEventListener('touchend', () => {
    rotateStatus.textContent = "";
});

rotateCCW.addEventListener('touchstart', (e) => {
    e.preventDefault();
    rotateStatus.textContent = "CCW";
});

rotateCCW.addEventListener('touchend', () => {
    rotateStatus.textContent = "";
});
}
return { initHome, initRun };

})();
