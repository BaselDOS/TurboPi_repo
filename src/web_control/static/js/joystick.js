const Joystick = (() => {

function init() {

  initMoveJoystick();
  initCameraJoystick();
  initRotationButtons();

}

function initMoveJoystick() {

  const zone = document.getElementById('moveJoystick');
  const joyX = document.getElementById('joyX');
  const joyY = document.getElementById('joyY');

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

    x = parseFloat(x.toFixed(2));
    y = parseFloat(y.toFixed(2));

    if (joyX) joyX.textContent = x;
    if (joyY) joyY.textContent = y;

    const now = Date.now();

    if (now - lastSend > 100) {

      fetch('/api/move', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({x,y})
      });

      lastSend = now;

    }

  });

  manager.on('end', function() {

    if (joyX) joyX.textContent="0.00";
    if (joyY) joyY.textContent="0.00";

    fetch('/api/move',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({x:0,y:0})
    });

  });

}

function initCameraJoystick() {

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

    const now = Date.now();

    if (now - lastCamSend > 100) {

      fetch('/api/camera',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({x:pan,y:tilt})
      });

      lastCamSend = now;

    }

  });

  // FIX: stop camera when joystick released
  camManager.on('end', function() {

    if (camX) camX.textContent = "0.00";
    if (camY) camY.textContent = "0.00";

    fetch('/api/camera',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({x:0,y:0})
    });

  });

}

function initRotationButtons() {

  const rotateCW = document.getElementById('rotateCW');
  const rotateCCW = document.getElementById('rotateCCW');
  const rotateStatus = document.getElementById('rotateStatus');

  function send(dir){

    fetch('/api/rotate',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({direction:dir})
    });

  }

  rotateCW.addEventListener('mousedown',()=>{
    rotateStatus.textContent="CW";
    send("cw");
  });

  rotateCW.addEventListener('mouseup',()=>{
    rotateStatus.textContent="";
    send("stop");
  });

  rotateCCW.addEventListener('mousedown',()=>{
    rotateStatus.textContent="CCW";
    send("ccw");
  });

  rotateCCW.addEventListener('mouseup',()=>{
    rotateStatus.textContent="";
    send("stop");
  });

}

return { init };

})();
