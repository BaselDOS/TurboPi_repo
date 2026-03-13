const Status = (() => {

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

  el.style.borderColor = ok
    ? 'rgba(45,255,143,.45)'
    : 'rgba(255,59,92,.35)';

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

async function refresh() {

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

    setText('wifiVal','N/A');
    setText('ipVal','N/A');
    setText('rosVal','N/A');
    setText('batVal','N/A');
    setText('camVal','N/A');

    setCardState('wifiCard', false);
    setCardState('rosCard', false);
    setCardState('batCard', false);
    setCardState('camCard', false);

  }

}

function startAutoRefresh() {

  refresh();

  setInterval(refresh, 3000);
}

return { refresh, startAutoRefresh };

})();
