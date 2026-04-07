const App = (() => {

function wireCommonButtons() {

  const refreshBtn = document.getElementById('refreshBtn');
  if (refreshBtn) refreshBtn.addEventListener('click', Status.refresh);

  const reloadBtn = document.getElementById('reloadBtn');
  if (reloadBtn) reloadBtn.addEventListener('click', () => window.location.reload());

}

function initHome() {

  wireCommonButtons();
  Status.startAutoRefresh();

}

function initRun() {

  wireCommonButtons();
  Status.startAutoRefresh();

  let selected = null;

  const modelLabel = document.getElementById('selectedMode');
  const joystickPanel = document.getElementById('joystickPanel');
  const cameraPanel = document.getElementById('cameraPanel');
  const aiPanel = document.getElementById("aiPanel");

  document.querySelectorAll('.mode-card').forEach(btn => {

    btn.addEventListener('click', () => {

      document.querySelectorAll('.mode-card')
        .forEach(b => b.classList.remove('selected'));

      btn.classList.add('selected');

      selected = btn.dataset.mode || null;

      if (modelLabel)
        modelLabel.textContent = selected ?? 'none';

    });

  });

  const startBtn = document.getElementById('startBtn');

  startBtn.addEventListener('click', async () => {

    if (!selected) {
      alert("Select a mode first");
      return;
    }

    const res = await fetch('/api/run_node',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({node:selected})
    });

    const data = await res.json();

    alert(data.message || "Node started");

    if (selected === "joystick") {

    joystickPanel.classList.remove("hidden");
    cameraPanel.classList.remove("hidden");

    const img = document.getElementById("cameraFeed");
    if (img) {
        img.src = "/stream?" + new Date().getTime();
    }
    
    const voiceControl = document.getElementById("voiceControl");
    if (voiceControl) {
        voiceControl.classList.add("hidden");
    }
    Joystick.init();

}
else if (selected === "avoidance") {

    joystickPanel.classList.add("hidden");
    cameraPanel.classList.remove("hidden");

    const img = document.getElementById("cameraFeed");
    if (img && !img.src.includes("/stream")) {
        img.src = "/stream";
    }
    const voiceControl = document.getElementById("voiceControl");
    if (voiceControl) {
        voiceControl.classList.add("hidden");
    }

}
else if (selected === "ai") {

    joystickPanel.classList.add("hidden");
    cameraPanel.classList.remove("hidden");

    // FIX: only use aiPanel if it exists
    if (aiPanel) {
        aiPanel.classList.remove("hidden");
    }

    const img = document.getElementById("cameraFeed");
    if (img && !img.src.includes("/stream")) {
        img.src = "/stream";
    }
    const voiceControl = document.getElementById("voiceControl");
    if (voiceControl) {
        voiceControl.classList.remove("hidden");
    }
}

else if (selected === "scan_and_find") {

    joystickPanel.classList.add("hidden");
    cameraPanel.classList.remove("hidden");

    const img = document.getElementById("cameraFeed");
    if (img && !img.src.includes("/stream")) {
        img.src = "/stream";
    }
    const voiceControl = document.getElementById("voiceControl");
    if (voiceControl) {
        voiceControl.classList.add("hidden");
    }
}

  });

  const stopBtn = document.getElementById('stopBtn');

  stopBtn.addEventListener('click', async () => {

    const res = await fetch('/api/stop_node',{method:'POST'});

    const data = await res.json();

    alert(data.message || "Node stopped");

    joystickPanel.classList.add("hidden");
    cameraPanel.classList.add("hidden");
    if (aiPanel) aiPanel.classList.add("hidden");
    const img = document.getElementById("cameraFeed");
    if (img) {
        img.src = "";
    }
    const voiceControl = document.getElementById("voiceControl");
    if (voiceControl) voiceControl.classList.add("hidden");
  });

// =====================
// VOICE RECORDING
// =====================
let mediaRecorder;
let audioChunks = [];

const recordBtn = document.getElementById("recordBtn");
const voiceText = document.getElementById("voiceText");

if (recordBtn) {

  recordBtn.onclick = async () => {

    if (!mediaRecorder || mediaRecorder.state === "inactive") {

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = e => {
        audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {

        const blob = new Blob(audioChunks, { type: "audio/webm" });

        const formData = new FormData();
        formData.append("audio", blob);

        const res = await fetch("/api/voice_command", {
          method: "POST",
          body: formData
        });

        const data = await res.json();

        if (voiceText) {
          voiceText.innerText = "Text: " + (data.text || "—");
        }

      };

      mediaRecorder.start();
      recordBtn.innerText = "⏹ Stop";

    } else {

      mediaRecorder.stop();
      recordBtn.innerText = "🎤 Record";

    }

  };

}

}

return { initHome, initRun };

})();

