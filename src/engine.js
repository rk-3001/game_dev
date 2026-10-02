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
    this.x += this.vx;
    this.y += this.vy;
    this.vx *= 0.96;
    this.vy *= 0.96;
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
    ctx.arc(this.x, this.y, this.size * alpha, 0, Math.PI * 2);
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

  update(bounds, restitution = 0.98) {
    this.pos = this.pos.add(this.vel);
    this.pulse += 0.1;

    if (this.pos.x - this.radius < bounds.left) {
      this.pos.x = bounds.left + this.radius;
      this.vel.x = -this.vel.x * restitution;
    } else if (this.pos.x + this.radius > bounds.right) {
      this.pos.x = bounds.right - this.radius;
      this.vel.x = -this.vel.x * restitution;
    }

    if (this.pos.y - this.radius < bounds.top) {
      this.pos.y = bounds.top + this.radius;
      this.vel.y = -this.vel.y * restitution;
    } else if (this.pos.y + this.radius > bounds.bottom) {
      this.pos.y = bounds.bottom - this.radius;
      this.vel.y = -this.vel.y * restitution;
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
}

window.Vector2 = Vector2;
window.ParticleSystem = ParticleSystem;
window.RaycastSolver = RaycastSolver;
window.PhysicsParticle = PhysicsParticle;
