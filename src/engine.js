/**
 * CRASH TO DESKTOP - 2D Physics & Raycasting Primitives
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
}

class RaycastSolver {
  /**
   * Raycast through a scene with reflective surfaces
   * @param {Vector2} origin 
   * @param {Vector2} dir 
   * @param {Array} surfaces 
   * @param {number} maxBounces 
   * @returns {{ path: Array<Vector2>, bounces: number, crashed: boolean }}
   */
  static trace(origin, dir, surfaces, maxBounces = 500) {
    let currentOrigin = new Vector2(origin.x, origin.y);
    let currentDir = dir.normalize();
    let path = [currentOrigin];
    let bounces = 0;
    const maxDistance = 25000;
    let totalTraveled = 0;

    while (bounces < maxBounces && totalTraveled < maxDistance) {
      let closestHit = null;
      let minT = Infinity;
      let hitSurface = null;

      // Check intersection against all active surfaces
      for (const surf of surfaces) {
        const hit = this.intersectRaySegment(currentOrigin, currentDir, surf.p1, surf.p2);
        if (hit && hit.t > 0.001 && hit.t < minT) {
          minT = hit.t;
          closestHit = hit;
          hitSurface = surf;
        }
      }

      if (!closestHit) {
        // Traveled off-screen or into void
        const endpoint = currentOrigin.add(currentDir.mul(1200));
        path.push(endpoint);
        break;
      }

      path.push(closestHit.point);
      totalTraveled += minT;
      bounces++;

      // Reflect direction along surface normal
      const normal = hitSurface.normal;
      const dot = currentDir.dot(normal);
      currentDir = currentDir.sub(normal.mul(2 * dot)).normalize();
      currentOrigin = closestHit.point.add(currentDir.mul(0.01)); // Offset to avoid self-intersection
    }

    return {
      path,
      bounces,
      crashed: bounces >= maxBounces
    };
  }

  static intersectRaySegment(rayOrigin, rayDir, p1, p2) {
    const v1 = rayOrigin.sub(p1);
    const v2 = p2.sub(p1);
    const v3 = new Vector2(-rayDir.y, rayDir.x);

    const dot = v2.dot(v3);
    if (Math.abs(dot) < 0.000001) return null;

    const t1 = (v2.x * v1.y - v2.y * v1.x) / dot;
    const t2 = v1.dot(v3) / dot;

    if (t1 >= 0 && (t2 >= 0 && t2 <= 1)) {
      return {
        t: t1,
        point: rayOrigin.add(rayDir.mul(t1))
      };
    }
    return null;
  }
}

class Particle {
  constructor(x, y, vx, vy, radius = 6, mass = 1) {
    this.pos = new Vector2(x, y);
    this.vel = new Vector2(vx, vy);
    this.acc = new Vector2(0, 0);
    this.radius = radius;
    this.mass = mass;
    this.duplicated = false;
    this.color = '#ff3366';
  }

  update(bounds, restitution = 0.98) {
    this.vel = this.vel.add(this.acc);
    this.pos = this.pos.add(this.vel);
    this.acc = new Vector2(0, 0);

    // Wall collision
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

  applyForce(f) {
    if (this.mass > 0) {
      this.acc = this.acc.add(f.div(this.mass));
    }
  }
}

window.Vector2 = Vector2;
window.RaycastSolver = RaycastSolver;
window.Particle = Particle;
