/**
 * CRASH TO DESKTOP - Meta-OS Window Manager & Crash Reporting UI
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

    this.hudLevel = document.getElementById('hud-level');
    this.hudTarget = document.getElementById('hud-target');
    this.hudFps = document.getElementById('hud-fps');
    this.instructions = document.getElementById('instructions');

    this.initDraggable(this.modal);
  }

  updateHUD(levelNum, totalLevels, objective, stabilityPercent, fps = 60) {
    if (this.hudLevel) this.hudLevel.innerText = `SYS::LEVEL ${levelNum}/${totalLevels}`;
    if (this.hudTarget) this.hudTarget.innerText = `OBJECTIVE: ${objective}`;
    if (this.hudFps) {
      this.hudFps.innerText = `STABILITY: ${stabilityPercent}% (${fps} FPS)`;
      if (stabilityPercent < 30) {
        this.hudFps.style.color = '#ff3333';
        this.hudFps.style.borderColor = '#ff3333';
      } else {
        this.hudFps.style.color = 'var(--term-amber)';
        this.hudFps.style.borderColor = 'var(--term-amber)';
      }
    }
  }

  setInstructions(text) {
    if (this.instructions) this.instructions.innerText = text;
  }

  showCrashModal(data, onNext, onRetry) {
    if (!this.modal) return;

    window.sfx.playCrashBuzzer();
    this.triggerScreenShake(true);

    this.modalTitle.innerText = `⚠️ SYSTEM EXCEPTION CAUGHT: ${data.code || '0x00FF'}`;
    this.crashTitle.innerText = data.title || 'FATAL ENGINE ANOMALY';
    this.crashDesc.innerText = data.desc || 'An unhandled computational exception violated runtime stability guarantees.';
    this.crashDump.innerHTML = data.dump || 'Fault Address: 0x00000000<br>Status: EXECUTION_HALTED';

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

    // Center window
    this.modal.style.left = '260px';
    this.modal.style.top = '170px';
    this.modal.style.display = 'block';

    if (data.isVictory) {
      this.btnNext.innerText = '🏆 Complete Jam';
      this.btnNext.style.background = '#ffd700';
    } else {
      this.btnNext.innerText = 'Next Bug ➔';
      this.btnNext.style.background = '#dfffd8';
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
      if (isDragging) {
        isDragging = false;
      }
    });
  }
}

window.UIManager = UIManager;
