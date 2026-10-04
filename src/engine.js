/**
 * CRASH TO DESKTOP - High-Performance 2D Vector Physics & Particle Engine
 */

class Vector2 {
  constructor(x = 0, y = 0) {
    this.x = x;
    this.y = y;
  }

  add(v) { return new Vector2(this.x + v.x, this.y + v.y); }
  sub(v) { return new Vector2(this.x - v.x, this.y - v.y); }
  mul(s) { return new Vector2(this.x * s, this.y * s); }
  div(s) { return s !== 0 ? new Vector2(this.x / s, this.y / s) : new Vector2(0, 0); }
  length() { return Math.hypot(this.x, this.y); }
  normalize() {
    const l = this.length();
    return l > 0 ? this.div(l) : new Vector2(0, 0);
  }
  dot(v) { return this.x * v.x + this.y * v.y; }
  dist(v) { return Math.hypot(this.x - v.x, this.y - v.y); }
  lerp(target, t) {
    return new Vector2(
      this.x + (target.x - this.x) * t,
      this.y + (target.y - this.y) * t
    );
  }
  clone() { return new Vector2(this.x, this.y); }
}

class VisualParticle {
  constructor(x, y, vx, vy, color = '#00f0ff', life = 1.0, size = 3) {
    this.x = x;
    this.y = y;
    this.vx = vx;
    this.vy = vy;
    this.color = color;
    this.life = life;
    this.maxLife = life;
    this.size = size;
  }

  update(dt) {
    this.x += this.vx * dt * 60;
    this.y += this.vy * dt * 60;
    this.vx *= Math.pow(0.96, dt * 60);
    this.vy *= Math.pow(0.96, dt * 60);
    this.life -= dt;
  }

  draw(ctx) {
    if (this.life <= 0) return;
    const alpha = Math.max(0, this.life / this.maxLife);
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = this.color;
    ctx.shadowColor = this.color;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(this.x, this.y, Math.max(0.1, this.size * alpha), 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

class ParticleSystem {
  constructor() {
    this.particles = [];
  }

  emit(x, y, count = 8, color = '#00f0ff', speed = 3, size = 3) {
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const spd = (0.5 + Math.random() * 0.8) * speed;
      this.particles.push(new VisualParticle(
        x,
        y,
        Math.cos(angle) * spd,
        Math.sin(angle) * spd,
        color,
        0.3 + Math.random() * 0.4,
        size
      ));
    }
  }

  update(dt) {
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      p.update(dt);
      if (p.life <= 0) {
        this.particles.splice(i, 1);
      }
    }
  }

  draw(ctx) {
    for (const p of this.particles) {
      p.draw(ctx);
    }
  }

  clear() {
    this.particles = [];
  }

  get count() {
    return this.particles.length;
  }
}

class RaycastSolver {
  /**
   * Traces a laser ray through a room with interactive portals and barriers.
   */
  static traceWithPortals(origin, dir, portalA, portalB, obstacles = [], maxBounces = 500) {
    let currentOrigin = new Vector2(origin.x, origin.y);
    let currentDir = dir.normalize();
    let path = [currentOrigin];
    let bounces = 0;
    const maxSteps = 550;
    let hitSparkLocations = [];

    while (bounces < maxBounces && bounces < maxSteps) {
      let closestHit = null;
      let minDistance = Infinity;
      let hitType = null;

      // 1. Check Portal A
      if (portalA) {
        const hitA = this.intersectOrientedPortal(currentOrigin, currentDir, portalA);
        if (hitA && hitA.dist > 1.5 && hitA.dist < minDistance) {
          minDistance = hitA.dist;
          closestHit = hitA.point;
          hitType = 'PORTAL_A';
        }
      }

      // 2. Check Portal B
      if (portalB) {
        const hitB = this.intersectOrientedPortal(currentOrigin, currentDir, portalB);
        if (hitB && hitB.dist > 1.5 && hitB.dist < minDistance) {
          minDistance = hitB.dist;
          closestHit = hitB.point;
          hitType = 'PORTAL_B';
        }
      }

      // 3. Check Obstacles
      for (const obs of obstacles) {
        const hitObs = this.intersectBox(currentOrigin, currentDir, obs);
        if (hitObs && hitObs.dist > 1.5 && hitObs.dist < minDistance) {
          minDistance = hitObs.dist;
          closestHit = hitObs.point;
          hitType = 'OBSTACLE';
        }
      }

      // 4. Check Canvas Boundaries
      const hitBounds = this.intersectWorldBounds(currentOrigin, currentDir, 960, 600);
      if (hitBounds && hitBounds.dist > 0.1 && hitBounds.dist < minDistance) {
        minDistance = hitBounds.dist;
        closestHit = hitBounds.point;
        hitType = 'WALL';
      }

      if (!closestHit) break;

      path.push(closestHit);
      hitSparkLocations.push(closestHit);
      bounces++;

      // Handle Portal Teleportation
      if (hitType === 'PORTAL_A' && portalB) {
        // Enters Portal A -> Teleports to Portal B and fires in Portal B's exit direction
        currentOrigin = new Vector2(portalB.pos.x + portalB.w / 2, portalB.pos.y + portalB.h / 2);
        currentDir = portalB.exitDir.normalize();
        currentOrigin = currentOrigin.add(currentDir.mul(portalB.w / 2 + 8));
        path.push(currentOrigin);
      } else if (hitType === 'PORTAL_B' && portalA) {
        // Enters Portal B -> Teleports to Portal A and fires in Portal A's exit direction
        currentOrigin = new Vector2(portalA.pos.x + portalA.w / 2, portalA.pos.y + portalA.h / 2);
        currentDir = portalA.exitDir.normalize();
        currentOrigin = currentOrigin.add(currentDir.mul(portalA.w / 2 + 8));
        path.push(currentOrigin);
      } else {
        // Absorbed by wall or obstacle
        break;
      }
    }

    return {
      path,
      bounces,
      sparks: hitSparkLocations,
      crashed: bounces >= maxBounces
    };
  }

  static intersectOrientedPortal(origin, dir, portal) {
    const box = {
      x: portal.pos.x,
      y: portal.pos.y,
      w: portal.w,
      h: portal.h
    };
    const hit = this.intersectBox(origin, dir, box);
    if (!hit) return null;

    // Check if beam enters the portal aperture
    const dot = dir.dot(portal.entryNormal || new Vector2(-1, 0));
    if (dot > 0.05) {
      return hit;
    }
    return null;
  }

  static intersectBox(origin, dir, box) {
    const left = box.pos ? box.pos.x : box.x;
    const right = left + box.w;
    const top = box.pos ? box.pos.y : box.y;
    const bottom = top + box.h;

    let tmin = -Infinity, tmax = Infinity;

    if (dir.x !== 0) {
      const tx1 = (left - origin.x) / dir.x;
      const tx2 = (right - origin.x) / dir.x;
      tmin = Math.max(tmin, Math.min(tx1, tx2));
      tmax = Math.min(tmax, Math.max(tx1, tx2));
    } else if (origin.x < left || origin.x > right) {
      return null;
    }

    if (dir.y !== 0) {
      const ty1 = (top - origin.y) / dir.y;
      const ty2 = (bottom - origin.y) / dir.y;
      tmin = Math.max(tmin, Math.min(ty1, ty2));
      tmax = Math.min(tmax, Math.max(ty1, ty2));
    } else if (origin.y < top || origin.y > bottom) {
      return null;
    }

    if (tmax >= tmin && tmax > 0) {
      const t = tmin > 0 ? tmin : tmax;
      return {
        dist: t,
        point: origin.add(dir.mul(t))
      };
    }
    return null;
  }

  static intersectWorldBounds(origin, dir, w, h) {
    let t = Infinity;
    if (dir.x > 0) t = Math.min(t, (w - 20 - origin.x) / dir.x);
    if (dir.x < 0) t = Math.min(t, (20 - origin.x) / dir.x);
    if (dir.y > 0) t = Math.min(t, (h - 20 - origin.y) / dir.y);
    if (dir.y < 0) t = Math.min(t, (20 - origin.y) / dir.y);

    if (t > 0 && t < Infinity) {
      return {
        dist: t,
        point: origin.add(dir.mul(t))
      };
    }
    return null;
  }
}

class PhysicsParticle {
  constructor(x, y, vx, vy, radius = 7, color = '#38bdf8') {
    this.pos = new Vector2(x, y);
    this.vel = new Vector2(vx, vy);
    this.radius = radius;
    this.color = color;
    this.duplicated = false;
    this.pulse = Math.random() * Math.PI * 2;
  }

  update(bounds, restitution = 0.98, dt = 1 / 60) {
    const scale = dt * 60;
    this.pos.x += this.vel.x * scale;
    this.pos.y += this.vel.y * scale;
    this.pulse += 0.1 * scale;

    if (this.pos.x - this.radius < bounds.left) {
      this.pos.x = bounds.left + this.radius;
      this.vel.x = Math.abs(this.vel.x) * restitution;
    } else if (this.pos.x + this.radius > bounds.right) {
      this.pos.x = bounds.right - this.radius;
      this.vel.x = -Math.abs(this.vel.x) * restitution;
    }

    if (this.pos.y - this.radius < bounds.top) {
      this.pos.y = bounds.top + this.radius;
      this.vel.y = Math.abs(this.vel.y) * restitution;
    } else if (this.pos.y + this.radius > bounds.bottom) {
      this.pos.y = bounds.bottom - this.radius;
      this.vel.y = -Math.abs(this.vel.y) * restitution;
    }
  }

  draw(ctx) {
    ctx.save();
    ctx.fillStyle = this.color;
    ctx.shadowColor = this.color;
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.arc(this.pos.x, this.pos.y, this.radius + Math.sin(this.pulse) * 1.5, 0, Math.PI * 2);
    ctx.fill();

    // Hot center core
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(this.pos.x, this.pos.y, this.radius * 0.4, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  speed() {
    return this.vel.length();
  }
}

/**
 * ScreenShake - Manages camera shake offset for impact feedback
 */
class ScreenShake {
  constructor() {
    this.intensity = 0;
    this.duration = 0;
    this.elapsed = 0;
    this.offsetX = 0;
    this.offsetY = 0;
    this.decay = 0.9;
  }

  trigger(intensity = 8, duration = 0.3) {
    this.intensity = Math.max(this.intensity, intensity);
    this.duration = duration;
    this.elapsed = 0;
  }

  update(dt) {
    if (this.elapsed < this.duration) {
      this.elapsed += dt;
      const progress = this.elapsed / this.duration;
      const currentIntensity = this.intensity * (1 - progress);
      this.offsetX = (Math.random() * 2 - 1) * currentIntensity;
      this.offsetY = (Math.random() * 2 - 1) * currentIntensity;
    } else {
      this.offsetX = 0;
      this.offsetY = 0;
      this.intensity = 0;
    }
  }

  apply(ctx) {
    if (this.offsetX !== 0 || this.offsetY !== 0) {
      ctx.translate(this.offsetX, this.offsetY);
    }
  }

  get active() {
    return this.elapsed < this.duration;
  }
}

/**
 * Engine - Core canvas engine with high-DPI support, delta-time game loop,
 * screen shake, and integrated particle system.
 */
class Engine {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas ? canvas.getContext('2d') : null;
    this.options = Object.assign({
      width: 960,
      height: 600,
      background: '#0a0a1a',
      targetFPS: 60
    }, options);

    this.width = this.options.width;
    this.height = this.options.height;

    // Delta-time tracking
    this.lastTime = 0;
    this.dt = 0;
    this.fps = 0;
    this._fpsAccum = 0;
    this._fpsFrames = 0;
    this.running = false;
    this._rafId = null;

    // Subsystems
    this.particles = new ParticleSystem();
    this.shake = new ScreenShake();

    // Telemetry
    this.telemetry = {
      fps: 0,
      particleCount: 0,
      frameTime: 0,
      updateTime: 0,
      renderTime: 0
    };

    // Callbacks
    this.onUpdate = null;
    this.onRender = null;
    this.onResize = null;

    // High-DPI setup
    if (this.canvas) {
      this._setupHiDPI();
    }

    // Bind loop
    this._loop = this._loop.bind(this);
  }

  /**
   * Configure canvas for high-DPI / retina displays
   */
  _setupHiDPI() {
    const dpr = window.devicePixelRatio || 1;
    const w = this.options.width;
    const h = this.options.height;

    this.canvas.width = w * dpr;
    this.canvas.height = h * dpr;
    this.canvas.style.width = w + 'px';
    this.canvas.style.height = h + 'px';

    this.ctx.scale(dpr, dpr);
    this.dpr = dpr;
  }

  /**
   * Start the game loop
   */
  start() {
    if (this.running) return;
    this.running = true;
    this.lastTime = performance.now();
    this._rafId = requestAnimationFrame(this._loop);
  }

  /**
   * Stop the game loop
   */
  stop() {
    this.running = false;
    if (this._rafId !== null) {
      cancelAnimationFrame(this._rafId);
      this._rafId = null;
    }
  }

  /**
   * Core animation frame loop with delta-time
   */
  _loop(timestamp) {
    if (!this.running) return;

    const rawDt = (timestamp - this.lastTime) / 1000;
    this.lastTime = timestamp;

    // Clamp dt to prevent spiral of death on tab switch
    this.dt = Math.min(rawDt, 0.05);

    // FPS tracking
    this._fpsAccum += this.dt;
    this._fpsFrames++;
    if (this._fpsAccum >= 0.5) {
      this.fps = this._fpsFrames / this._fpsAccum;
      this.telemetry.fps = Math.round(this.fps);
      this._fpsAccum = 0;
      this._fpsFrames = 0;
    }

    const frameStart = performance.now();

    // Update phase
    const updateStart = performance.now();
    this._update(this.dt);
    this.telemetry.updateTime = performance.now() - updateStart;

    // Render phase
    const renderStart = performance.now();
    this._render();
    this.telemetry.renderTime = performance.now() - renderStart;

    this.telemetry.frameTime = performance.now() - frameStart;
    this.telemetry.particleCount = this.particles.count;

    this._rafId = requestAnimationFrame(this._loop);
  }

  /**
   * Internal update - subsystems + user callback
   */
  _update(dt) {
    this.shake.update(dt);
    this.particles.update(dt);

    if (typeof this.onUpdate === 'function') {
      this.onUpdate(dt);
    }
  }

  /**
   * Internal render - clear, shake, user callback, particles, HUD
   */
  _render() {
    const ctx = this.ctx;
    if (!ctx) return;

    ctx.save();

    // Clear
    ctx.fillStyle = this.options.background;
    ctx.fillRect(0, 0, this.width, this.height);

    // Apply screen shake
    this.shake.apply(ctx);

    // User render callback
    if (typeof this.onRender === 'function') {
      this.onRender(ctx, this.dt);
    }

    // Particles on top
    this.particles.draw(ctx);

    ctx.restore();
  }

  /**
   * Emit a burst of particles at (x, y)
   */
  emitParticles(x, y, count = 8, color = '#00f0ff', speed = 3, size = 3) {
    this.particles.emit(x, y, count, color, speed, size);
  }

  /**
   * Trigger screen shake
   */
  triggerShake(intensity = 8, duration = 0.3) {
    this.shake.trigger(intensity, duration);
  }

  /**
   * Draw a neon glowing line
   */
  drawNeonLine(ctx, x1, y1, x2, y2, color = '#00f0ff', lineWidth = 2, glowRadius = 12) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth + glowRadius * 0.5;
    ctx.shadowColor = color;
    ctx.shadowBlur = glowRadius;
    ctx.globalAlpha = 0.4;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();

    ctx.lineWidth = lineWidth;
    ctx.globalAlpha = 1.0;
    ctx.shadowBlur = glowRadius * 0.5;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    ctx.restore();
  }

  /**
   * Draw a neon glowing circle
   */
  drawNeonCircle(ctx, x, y, radius, color = '#00f0ff', lineWidth = 2, glowRadius = 12) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.shadowColor = color;
    ctx.shadowBlur = glowRadius;
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  /**
   * Draw a filled neon rect
   */
  drawNeonRect(ctx, x, y, w, h, color = '#00f0ff', glowRadius = 10, alpha = 0.15) {
    ctx.save();
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.shadowColor = color;
    ctx.shadowBlur = glowRadius;
    ctx.strokeRect(x, y, w, h);

    ctx.fillStyle = color;
    ctx.globalAlpha = alpha;
    ctx.fillRect(x, y, w, h);
    ctx.restore();
  }

  /**
   * Draw cyberpunk telemetry HUD overlay
   */
  drawTelemetry(ctx, x = 10, y = 20) {
    const t = this.telemetry;
    ctx.save();
    ctx.font = '11px monospace';
    ctx.fillStyle = '#00f0ff';
    ctx.globalAlpha = 0.7;
    ctx.shadowColor = '#00f0ff';
    ctx.shadowBlur = 4;
    ctx.fillText(`FPS: ${t.fps}`, x, y);
    ctx.fillText(`PARTICLES: ${t.particleCount}`, x, y + 14);
    ctx.fillText(`FRAME: ${t.frameTime.toFixed(2)}ms`, x, y + 28);
    ctx.restore();
  }

  /**
   * Resize canvas (e.g. on window resize)
   */
  resize(width, height) {
    this.width = width;
    this.height = height;
    this.options.width = width;
    this.options.height = height;
    if (this.canvas) {
      this._setupHiDPI();
    }
    if (typeof this.onResize === 'function') {
      this.onResize(width, height);
    }
  }

  /**
   * Get current delta time
   */
  getDeltaTime() {
    return this.dt;
  }

  /**
   * Get current FPS
   */
  getFPS() {
    return this.fps;
  }

  /**
   * Clear all particles
   */
  clearParticles() {
    this.particles.clear();
  }

  /**
   * One-shot manual step (useful for testing without RAF)
   */
  step(dt = 1 / 60) {
    this.dt = dt;
    this._update(dt);
    this._render();
  }
}

/**
 * AudioEngine - Procedural Web Audio API sound synthesis
 */
class AudioEngine {
  constructor() {
    this._ctx = null;
    this._masterGain = null;
    this._enabled = true;
    this._initialized = false;
  }

  _init() {
    if (this._initialized) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      this._ctx = new AudioContext();
      this._masterGain = this._ctx.createGain();
      this._masterGain.gain.value = 0.3;
      this._masterGain.connect(this._ctx.destination);
      this._initialized = true;
    } catch (e) {
      this._enabled = false;
    }
  }

  /**
   * Resume audio context (required after user gesture)
   */
  resume() {
    this._init();
    if (this._ctx && this._ctx.state === 'suspended') {
      this._ctx.resume();
    }
  }

  /**
   * Play a synthesized impact sound
   */
  playImpact(frequency = 220, duration = 0.15, type = 'sawtooth') {
    if (!this._enabled) return;
    this._init();
    if (!this._ctx) return;

    try {
      const osc = this._ctx.createOscillator();
      const gain = this._ctx.createGain();

      osc.type = type;
      osc.frequency.setValueAtTime(frequency, this._ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(frequency * 0.3, this._ctx.currentTime + duration);

      gain.gain.setValueAtTime(0.5, this._ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this._ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(this._masterGain);

      osc.start(this._ctx.currentTime);
      osc.stop(this._ctx.currentTime + duration);
    } catch (e) { /* silent fail */ }
  }

  /**
   * Play a synthesized laser/beam sound
   */
  playLaser(frequency = 880, duration = 0.08) {
    if (!this._enabled) return;
    this._init();
    if (!this._ctx) return;

    try {
      const osc = this._ctx.createOscillator();
      const gain = this._ctx.createGain();

      osc.type = 'square';
      osc.frequency.setValueAtTime(frequency, this._ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(frequency * 0.1, this._ctx.currentTime + duration);

      gain.gain.setValueAtTime(0.3, this._ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this._ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(this._masterGain);

      osc.start(this._ctx.currentTime);
      osc.stop(this._ctx.currentTime + duration);
    } catch (e) { /* silent fail */ }
  }

  /**
   * Play a portal teleport sound
   */
  playPortal() {
    if (!this._enabled) return;
    this._init();
    if (!this._ctx) return;

    try {
      const osc = this._ctx.createOscillator();
      const gain = this._ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(200, this._ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1200, this._ctx.currentTime + 0.1);
      osc.frequency.exponentialRampToValueAtTime(400, this._ctx.currentTime + 0.25);

      gain.gain.setValueAtTime(0.4, this._ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this._ctx.currentTime + 0.3);

      osc.connect(gain);
      gain.connect(this._masterGain);

      osc.start(this._ctx.currentTime);
      osc.stop(this._ctx.currentTime + 0.3);
    } catch (e) { /* silent fail */ }
  }

  /**
   * Play a collision/crash sound
   */
  playCrash(intensity = 1.0) {
    if (!this._enabled) return;
    this._init();
    if (!this._ctx) return;

    try {
      // Noise burst via buffer
      const bufferSize = this._ctx.sampleRate * 0.2;
      const buffer = this._ctx.createBuffer(1, bufferSize, this._ctx.sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * intensity;
      }

      const source = this._ctx.createBufferSource();
      source.buffer = buffer;

      const gain = this._ctx.createGain();
      gain.gain.setValueAtTime(0.6 * intensity, this._ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this._ctx.currentTime + 0.2);

      source.connect(gain);
      gain.connect(this._masterGain);
      source.start(this._ctx.currentTime);
    } catch (e) { /* silent fail */ }
  }

  setVolume(v) {
    if (this._masterGain) {
      this._masterGain.gain.value = Math.max(0, Math.min(1, v));
    }
  }

  setEnabled(enabled) {
    this._enabled = enabled;
  }
}

/**
 * KineticBody - A physics body with velocity, acceleration, friction, and
 * collision response for use in the game loop.
 */
class KineticBody {
  constructor(x, y, options = {}) {
    this.pos = new Vector2(x, y);
    this.vel = new Vector2(options.vx || 0, options.vy || 0);
    this.acc = new Vector2(0, 0);
    this.radius = options.radius || 10;
    this.mass = options.mass || 1;
    this.friction = options.friction !== undefined ? options.friction : 0.99;
    this.restitution = options.restitution !== undefined ? options.restitution : 0.85;
    this.color = options.color || '#00f0ff';
    this.active = true;
    this.onWallHit = null;
    this.onCollide = null;
    this._trail = [];
    this._trailMax = options.trailLength || 0;
  }

  applyForce(fx, fy) {
    this.acc.x += fx / this.mass;
    this.acc.y += fy / this.mass;
  }

  applyImpulse(ix, iy) {
    this.vel.x += ix / this.mass;
    this.vel.y