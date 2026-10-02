/**
 * CRASH TO DESKTOP - Game Engine & Master Controller
 */

class GameApp {
  constructor() {
    this.canvas = document.getElementById('gameCanvas');
    this.ctx = this.canvas.getContext('2d');
    this.ui = new UIManager();
    this.particles = new ParticleSystem();

    this.currentLevelIndex = 0;
    this.gameState = 'PLAYING';
    this.draggedItem = null;
    this.hoveredItem = null;
    this.dragOffset = new Vector2(0, 0);

    this.lastTime = performance.now();
    this.stability = 100;
    this.mousePos = new Vector2(0, 0);

    this.initEventListeners();
    this.loadLevel(this.currentLevelIndex);

    this.loop = this.loop.bind(this);
    requestAnimationFrame(this.loop);
  }

  loadLevel(index) {
    if (index >= GameLevels.length) {
      this.triggerGameComplete();
      return;
    }

    this.currentLevelIndex = index;
    this.level = GameLevels[this.currentLevelIndex];
    this.gameState = 'PLAYING';
    this.draggedItem = null;
    this.hoveredItem = null;
    this.stability = 100;

    this.level.init(this.canvas.width, this.canvas.height);
    this.ui.updateDashboard(
      this.currentLevelIndex + 1,
      this.level.name,
      this.level.objective,
      this.level.instructions,
      this.level.hint
    );
    this.ui.hideCrashModal();
  }

  triggerGameComplete() {
    this.gameState = 'VICTORY';
    window.sfx.playVictory();
    this.ui.showCrashModal({
      isVictory: true,
      code: "0xFFFFFFFF",
      title: "🏆 TOTAL SYSTEM COLLAPSE: ALL VULNERABILITIES EXPLOITED",
      desc: "Incredible work! You have completely destabilized every safety invariant in the engine. The developer has conceded defeat.",
      dump: `Fault Summary: 4/4 Critical Exploits Triggered.<br>Status: CERTIFIED GAME BREAKING ARCHITECT.<br>BYOG Rating: ★★★★★ (Out of the Box Award Winner)`
    }, () => {
      this.loadLevel(0);
    }, () => {
      this.loadLevel(0);
    });
  }

  initEventListeners() {
    // Audio unlock on first user gesture
    const unlockAudio = () => {
      window.sfx.init();
      window.sfx.startAmbientHum();
      window.removeEventListener('click', unlockAudio);
    };
    window.addEventListener('click', unlockAudio);

    // Canvas Mouse Down
    this.canvas.addEventListener('mousedown', (e) => {
      if (this.gameState !== 'PLAYING') return;

      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;
      const mx = (e.clientX - rect.left) * scaleX;
      const my = (e.clientY - rect.top) * scaleY;

      if (!this.level || !this.level.items) return;

      // Generous 18px padding for easy clicking
      for (const item of this.level.items) {
        if (mx >= item.pos.x - 18 && mx <= item.pos.x + item.w + 18 &&
            my >= item.pos.y - 18 && my <= item.pos.y + item.h + 18) {
          this.draggedItem = item;
          this.dragOffset = new Vector2(mx - item.pos.x, my - item.pos.y);
          this.canvas.style.cursor = 'grabbing';
          window.sfx.playClick();
          this.particles.emit(item.pos.x + item.w / 2, item.pos.y + item.h / 2, 8, item.color || '#00f0ff', 3);
          break;
        }
      }
    });

    // Window Mouse Move (Smooth dragging + Hover detection)
    window.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width / rect.width;
      const scaleY = this.canvas.height / rect.height;
      const mx = (e.clientX - rect.left) * scaleX;
      const my = (e.clientY - rect.top) * scaleY;
      this.mousePos = new Vector2(mx, my);

      if (this.draggedItem && this.gameState === 'PLAYING') {
        const targetX = Math.max(20, Math.min(this.canvas.width - this.draggedItem.w - 20, mx - this.dragOffset.x));
        const targetY = Math.max(30, Math.min(this.canvas.height - this.draggedItem.h - 30, my - this.dragOffset.y));

        this.draggedItem.pos.x = targetX;
        this.draggedItem.pos.y = targetY;

        // Spark trail while dragging
        if (Math.random() < 0.3) {
          this.particles.emit(
            this.draggedItem.pos.x + this.draggedItem.w / 2,
            this.draggedItem.pos.y + this.draggedItem.h / 2,
            2,
            this.draggedItem.color || '#00f0ff',
            1.5
          );
        }
      } else {
        // Detect Hover
        this.hoveredItem = null;
        if (this.level && this.level.items) {
          for (const item of this.level.items) {
            if (mx >= item.pos.x - 15 && mx <= item.pos.x + item.w + 15 &&
                my >= item.pos.y - 15 && my <= item.pos.y + item.h + 15) {
              this.hoveredItem = item;
              break;
            }
          }
        }
        this.canvas.style.cursor = this.hoveredItem ? 'grab' : 'crosshair';
      }
    });

    window.addEventListener('mouseup', () => {
      if (this.draggedItem) {
        window.sfx.playSnap();
        this.canvas.style.cursor = this.hoveredItem ? 'grab' : 'crosshair';
        this.draggedItem = null;
      }
    });

    // Level Pills Navigation
    document.querySelectorAll('.level-pill').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        const lvlNum = parseInt(e.target.dataset.level, 10);
        window.sfx.playClick();
        this.loadLevel(lvlNum - 1);
      });
    });

    // Reset Level Button
    const btnReset = document.getElementById('btn-reset-level');
    if (btnReset) {
      btnReset.addEventListener('click', () => {
        window.sfx.playClick();
        this.loadLevel(this.currentLevelIndex);
      });
    }

    // Toggle Audio Button
    const btnMute = document.getElementById('btn-toggle-audio');
    if (btnMute) {
      btnMute.addEventListener('click', () => {
        const isMuted = window.sfx.toggleMute();
        btnMute.innerHTML = isMuted ? '🔇 Audio OFF' : '🔊 Audio ON';
      });
    }

    // Hint Button
    const btnHint = document.getElementById('btn-toggle-hint');
    if (btnHint) {
      btnHint.addEventListener('click', () => {
        this.ui.toggleHint();
      });
    }
  }

  loop(currentTime) {
    const dt = Math.min(0.05, (currentTime - this.lastTime) / 1000);
    this.lastTime = currentTime;

    this.update(dt);
    this.render();

    requestAnimationFrame(this.loop);
  }

  update(dt) {
    this.particles.update(dt);

    if (this.gameState !== 'PLAYING' || !this.level) return;

    const result = this.level.update(this, dt);

    // Update telemetry gauges
    const stackDepth = this.level.currentBounces || (this.level.lastTrace ? this.level.lastTrace.bounces : 0);
    const heapUtil = this.level.particles ? this.level.particles.length : 0;
    const aluStatus = this.level.currentCalc ? (this.level.currentCalc === 'NaN' ? 'NaN (DIV/0)' : 'OK') : 'NORMAL';

    if (result && result.crashed) {
      this.stability = 0;
      this.gameState = 'CRASHED';
      this.ui.updateGauges(stackDepth, heapUtil, aluStatus, 0);
      this.ui.showCrashModal(result, () => {
        this.loadLevel(this.currentLevelIndex + 1);
      }, () => {
        this.loadLevel(this.currentLevelIndex);
      });
    } else {
      // Calculate dynamic stability based on proximity to crash
      let targetStability = 100;
      if (stackDepth > 0) targetStability -= (stackDepth / 500) * 90;
      if (heapUtil > 0) targetStability -= (heapUtil / 128) * 90;
      this.stability = Math.max(5, targetStability);
      this.ui.updateGauges(stackDepth, heapUtil, aluStatus, this.stability);
    }
  }

  render() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Subtle Sci-Fi Grid Lines
    this.ctx.save();
    this.ctx.strokeStyle = '#0b1322';
    this.ctx.lineWidth = 1;
    for (let x = 0; x < this.canvas.width; x += 40) {
      this.ctx.beginPath(); this.ctx.moveTo(x, 0); this.ctx.lineTo(x, this.canvas.height); this.ctx.stroke();
    }
    for (let y = 0; y < this.canvas.height; y += 40) {
      this.ctx.beginPath(); this.ctx.moveTo(0, y); this.ctx.lineTo(this.canvas.width, y); this.ctx.stroke();
    }
    this.ctx.restore();

    // Render active level content
    if (this.level) {
      this.level.render(this.ctx, this);
    }

    // Render Particle System
    this.particles.draw(this.ctx);
  }
}

// Robust Launch: Run immediately whether loaded synchronously or asynchronously
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { window.app = new GameApp(); });
} else {
  window.app = new GameApp();
}
