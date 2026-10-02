/**
 * CRASH TO DESKTOP - Cyber-Dashboard & Modal UI Manager
 */

class UIManager {
  constructor() {
    this.wrapper = document.getElementById('crt-wrapper');
    this.modal = document.getElementById('crash-modal');
    this.modalTitle = document.getElementById('modal-title');
    this.crashTitle = document.getElementById('crash-title');
    this.crashDesc = document.getElementById('crash-desc');
    this.crashDump = document.getElementById('crash-dump');
    this.btnNext = document.getElementById('btn-next');
    this.btnRetry = document.getElementById('btn-retry');

    // Telemetry Dashboard Elements
    this.gaugeStack = document.getElementById('telemetry-stack');
    this.gaugeMemory = document.getElementById('telemetry-memory');
    this.gaugeAlu = document.getElementById('telemetry-alu');
    this.gaugeStability = document.getElementById('telemetry-stability');

    this.txtLevel = document.getElementById('hud-level-title');
    this.txtObjective = document.getElementById('hud-objective-text');
    this.txtInstructions = document.getElementById('hud-instructions-text');
    this.hintPanel = document.getElementById('hint-panel');
    this.txtHint = document.getElementById('txt-hint');

    this.initDraggable(this.modal);
  }

  updateDashboard(levelNum, levelName, objective, instructions, hint) {
    if (this.txtLevel) this.txtLevel.innerText = `SYS::ZONE 0${levelNum} — ${levelName}`;
    if (this.txtObjective) this.txtObjective.innerText = objective;
    if (this.txtInstructions) this.txtInstructions.innerText = instructions;
    if (this.txtHint) this.txtHint.innerText = hint;

    // Highlight active level tab
    document.querySelectorAll('.level-pill').forEach((btn, idx) => {
      if (idx === levelNum - 1) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  updateGauges(stackDepth = 0, heapUtil = 0, aluStatus = "NORMAL", stability = 100) {
    if (this.gaugeStack) {
      this.gaugeStack.style.width = `${Math.min(100, (stackDepth / 500) * 100)}%`;
      this.gaugeStack.innerText = `${stackDepth} / 500`;
    }
    if (this.gaugeMemory) {
      this.gaugeMemory.style.width = `${Math.min(100, (heapUtil / 128) * 100)}%`;
      this.gaugeMemory.innerText = `${heapUtil} / 128 MB`;
    }
    if (this.gaugeAlu) {
      this.gaugeAlu.innerText = aluStatus;
      if (aluStatus === "NaN (DIV/0)") {
        this.gaugeAlu.style.color = '#f43f5e';
      } else {
        this.gaugeAlu.style.color = '#38bdf8';
      }
    }
    if (this.gaugeStability) {
      this.gaugeStability.style.width = `${Math.max(0, stability)}%`;
      this.gaugeStability.innerText = `${Math.round(stability)}%`;
      if (stability <= 20) {
        this.gaugeStability.style.backgroundColor = '#f43f5e';
      } else if (stability <= 60) {
        this.gaugeStability.style.backgroundColor = '#eab308';
      } else {
        this.gaugeStability.style.backgroundColor = '#10b981';
      }
    }
  }

  toggleHint() {
    if (!this.hintPanel) return;
    const isHidden = this.hintPanel.style.display === 'none' || !this.hintPanel.style.display;
    this.hintPanel.style.display = isHidden ? 'block' : 'none';
    window.sfx.playClick();
  }

  showCrashModal(data, onNext, onRetry) {
    if (!this.modal) return;

    window.sfx.playCrashBuzzer();
    this.triggerScreenShake(true);

    this.modalTitle.innerText = `⚠️ SYSTEM FAULT INTERCEPTED: ${data.code || '0x00FF'}`;
    this.crashTitle.innerText = data.title || 'UNHANDLED COMPUTATIONAL SINGULARITY';
    this.crashDesc.innerText = data.desc || 'The game engine encountered an unrecoverable logic paradox.';
    this.crashDump.innerHTML = data.dump || 'Status: EXECUTION_HALTED<br>Address: 0x00000000';

    this.btnNext.onclick = () => {
      window.sfx.playClick();
      this.hideCrashModal();
      if (onNext) onNext();
    };

    this.btnRetry.onclick = () => {
      window.sfx.playClick();
      this.hideCrashModal();
      if (onRetry) onRetry();
    };

    this.modal.style.left = '250px';
    this.modal.style.top = '170px';
    this.modal.style.display = 'block';

    if (data.isVictory) {
      this.btnNext.innerText = '🏆 Restart Jam Run';
      this.btnNext.style.background = '#facc15';
    } else {
      this.btnNext.innerText = 'Next Exploit ➔';
      this.btnNext.style.background = '#86efac';
    }
  }

  hideCrashModal() {
    if (this.modal) this.modal.style.display = 'none';
    this.triggerScreenShake(false);
  }

  triggerScreenShake(active = true) {
    if (this.wrapper) {
      if (active) this.wrapper.classList.add('screen-shake');
      else this.wrapper.classList.remove('screen-shake');
    }
  }

  initDraggable(win) {
    if (!win) return;
    const titleBar = win.querySelector('.title-bar');
    if (!titleBar) return;

    let isDragging = false;
    let startX = 0, startY = 0;
    let initialLeft = 0, initialTop = 0;

    titleBar.addEventListener('mousedown', (e) => {
      isDragging = true;
      startX = e.clientX;
      startY = e.clientY;
      initialLeft = win.offsetLeft;
      initialTop = win.offsetTop;
      window.sfx.playClick();
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      const dx = e.clientX - startX;
      const dy = e.clientY - startY;
      win.style.left = `${Math.max(10, Math.min(window.innerWidth - win.offsetWidth - 10, initialLeft + dx))}px`;
      win.style.top = `${Math.max(10, Math.min(window.innerHeight - win.offsetHeight - 10, initialTop + dy))}px`;
    });

    window.addEventListener('mouseup', () => {
      isDragging = false;
    });
  }
}

window.UIManager = UIManager;
