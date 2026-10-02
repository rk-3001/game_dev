/**
 * CRASH TO DESKTOP - Game Loop & Master State Controller
 */

class GameApp {
  constructor() {
    this.canvas = document.getElementById('gameCanvas');
    this.ctx = this.canvas.getContext('2d');
    this.ui = new UIManager();

    this.currentLevelIndex = 0;
    this.gameState = 'PLAYING'; // PLAYING, CRASHED, VICTORY
    this.draggedItem = null;
    this.dragOffset = new Vector2(0, 0);

    this.lastTime = performance.now();
    this.frameCount = 0;
    this.fps = 60;
    this.lastFpsUpdate = performance.now();

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

    this.level.init(this.canvas.width, this.canvas.height);
    this.ui.updateHUD(
      this.currentLevelIndex + 1,
      GameLevels.length,
      this.level.objective,
      100,
      60
    );
    this.ui.setInstructions(this.level.instructions);
    this.ui.hideCrashModal();
  }

  triggerGameComplete() {
    this.gameState = 'VICTORY';
    window.sfx.playVictory();
    this.ui.showCrashModal({
      isVictory: true,
      code: "0xFFFFFFFF",
      title: "🏆 TOTAL SYSTEM COLLAPSE: ALL EXPLOITS DISCOVERED",
      desc: "Incredible work! You have completely destabilized every safety invariant in the engine. The developer has conceded defeat.",
      dump: `Fault Summary: 4/4 Critical Vulnerabilities Triggered.<br>Status: CERTIFIED GAME BREAKING ARCHITECT.<br>BYOG Rating: ★★★★★ (Out of the Box)`
    }, () => {
      this.loadLevel(0); // Restart from level 1
    }, () => {
      this.loadLevel(0);
    });
  }

  initEventListeners() {
    this.canvas.addEventListener('mousedown', (e) => {
      if (this.gameState !== 'PLAYING') return;

      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      if (!this.level || !this.level.items) return;

      for (const item of this.level.items) {
        if (mx >= item.pos.x && mx <= item.pos.x + item.w &&
            my >= item.pos.y && my <= item.pos.y + item.h) {
          this.draggedItem = item;
          this.dragOffset = new Vector2(mx - item.pos.x, my - item.pos.y);
          window.sfx.playClick();
          break;
        }
      }
    });

    window.addEventListener('mousemove', (e) => {
      if (!this.draggedItem || this.gameState !== 'PLAYING') return;

      const rect = this.canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      const newX = Math.max(20, Math.min(this.canvas.width - this.draggedItem.w - 20, mx - this.dragOffset.x));
      const newY = Math.max(80, Math.min(this.canvas.height - this.draggedItem.h - 30, my - this.dragOffset.y));

      this.draggedItem.pos.x = newX;
      this.draggedItem.pos.y = newY;
    });

    window.addEventListener('mouseup', () => {
      if (this.draggedItem) {
        window.sfx.playSnap();
        this.draggedItem = null;
      }
    });
  }

  loop(currentTime) {
    const dt = (currentTime - this.lastTime) / 1000;
    this.lastTime = currentTime;

    // Calculate FPS
    this.frameCount++;
    if (currentTime - this.lastFpsUpdate >= 500) {
      this.fps = Math.round((this.frameCount * 1000) / (currentTime - this.lastFpsUpdate));
      this.frameCount = 0;
      this.lastFpsUpdate = currentTime;
    }

    this.update(dt);
    this.render();

    requestAnimationFrame(this.loop);
  }

  update(dt) {
    if (this.gameState !== 'PLAYING' || !this.level) return;

    const result = this.level.update(this, dt);
    if (result && result.crashed) {
      this.gameState = 'CRASHED';
      this.ui.updateHUD(
        this.currentLevelIndex + 1,
        GameLevels.length,
        this.level.objective,
        0,
        0
      );
      this.ui.showCrashModal(result, () => {
        this.loadLevel(this.currentLevelIndex + 1);
      }, () => {
        this.loadLevel(this.currentLevelIndex);
      });
    }
  }

  render() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw Subtle Grid
    this.ctx.strokeStyle = '#0e1620';
    this.ctx.lineWidth = 1;
    for (let x = 0; x < this.canvas.width; x += 40) {
      this.ctx.beginPath(); this.ctx.moveTo(x, 0); this.ctx.lineTo(x, this.canvas.height); this.ctx.stroke();
    }
    for (let y = 0; y < this.canvas.height; y += 40) {
      this.ctx.beginPath(); this.ctx.moveTo(0, y); this.ctx.lineTo(this.canvas.width, y); this.ctx.stroke();
    }

    if (this.level) {
      this.level.render(this.ctx);
    }
  }
}

// Boot application when DOM is ready
window.addEventListener('DOMContentLoaded', () => {
  window.app = new GameApp();
});
