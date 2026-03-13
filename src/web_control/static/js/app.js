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

      Joystick.init();

    }

  });

  const stopBtn = document.getElementById('stopBtn');

  stopBtn.addEventListener('click', async () => {

    const res = await fetch('/api/stop_node',{method:'POST'});

    const data = await res.json();

    alert(data.message || "Node stopped");

    joystickPanel.classList.add("hidden");

  });

}

return { initHome, initRun };

})();
