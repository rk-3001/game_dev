/**
 * CRASH TO DESKTOP - Puzzle Levels Definition
 * Each level represents a fundamental computer science / game engine crash exploit.
 */

const GameLevels = [
  // -------------------------------------------------------------
  // LEVEL 1: STACK OVERFLOW (Infinite Raycast Recursion)
  // -------------------------------------------------------------
  {
    id: 1,
    name: "STACK OVERFLOW",
    code: "0x00FF4B22",
    objective: "FORCE INFINITE RECURSION (> 500 BOUNCES)",
    instructions: "Drag and align the portal reflectors facing each other to trap the laser in an infinite loop.",
    init: function(width, height) {
      this.emitter = { pos: new Vector2(80, height / 2), dir: new Vector2(1, 0) };
      this.items = [
        {
          id: 'm1',
          type: 'mirror',
          pos: new Vector2(280, height / 2 - 70),
          w: 20,
          h: 140,
          label: 'Portal Alpha',
          normal: new Vector2(1, 0)
        },
        {
          id: 'm2',
          type: 'mirror',
          pos: new Vector2(620, height / 2 - 70),
          w: 20,
          h: 140,
          label: 'Portal Beta',
          normal: new Vector2(-1, 0)
        }
      ];
      this.obstacles = [
        { pos: new Vector2(440, 120), w: 60, h: 90, label: 'Safety Baffle' }
      ];
    },
    update: function(engine, dt) {
      // Build reflective surfaces from mirror segments
      const surfaces = [];
      for (const m of this.items) {
        surfaces.push({
          p1: new Vector2(m.pos.x + m.w / 2, m.pos.y),
          p2: new Vector2(m.pos.x + m.w / 2, m.pos.y + m.h),
          normal: m.normal
        });
      }

      // Add canvas boundary walls (absorbing/reflecting)
      surfaces.push(
        { p1: new Vector2(0, 70), p2: new Vector2(960, 70), normal: new Vector2(0, 1) },
        { p1: new Vector2(960, 70), p2: new Vector2(960, 600), normal: new Vector2(-1, 0) },
        { p1: new Vector2(960, 600), p2: new Vector2(0, 600), normal: new Vector2(0, -1) },
        { p1: new Vector2(0, 600), p2: new Vector2(0, 70), normal: new Vector2(1, 0) }
      );

      const trace = RaycastSolver.trace(this.emitter.pos, this.emitter.dir, surfaces, 520);
      this.lastTrace = trace;

      if (trace.bounces >= 500) {
        return {
          crashed: true,
          code: this.code,
          title: "💥 FATAL EXCEPTION: STACK_OVERFLOW",
          desc: "Raycast function recursion depth exceeded 500 nested calls without exiting.",
          dump: `Faulting Thread: 0x8A4 (Renderer_Raytracer)<br>Call Stack: 512 frames allocated, 0 returned.<br>Vector: Portal Alpha ⇄ Portal Beta loop.`
        };
      }
      return { crashed: false };
    },
    render: function(ctx) {
      // Draw Laser Emitter
      ctx.fillStyle = '#00f0ff';
      ctx.fillRect(this.emitter.pos.x - 20, this.emitter.pos.y - 15, 20, 30);
      ctx.fillStyle = '#fff';
      ctx.font = '10px Courier New';
      ctx.fillText("RAY_GEN", this.emitter.pos.x - 55, this.emitter.pos.y + 4);

      // Draw Obstacles
      for (const obs of this.obstacles) {
        ctx.fillStyle = '#334155';
        ctx.fillRect(obs.pos.x, obs.pos.y, obs.w, obs.h);
        ctx.strokeStyle = '#64748b';
        ctx.strokeRect(obs.pos.x, obs.pos.y, obs.w, obs.h);
      }

      // Draw Mirrors
      for (const m of this.items) {
        ctx.fillStyle = '#38bdf8';
        ctx.fillRect(m.pos.x, m.pos.y, m.w, m.h);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.strokeRect(m.pos.x, m.pos.y, m.w, m.h);

        ctx.fillStyle = '#ffb000';
        ctx.font = '11px monospace';
        ctx.fillText(m.label, m.pos.x - 14, m.pos.y - 8);
      }

      // Draw Laser Path
      if (this.lastTrace && this.lastTrace.path.length > 1) {
        ctx.strokeStyle = '#ff0055';
        ctx.lineWidth = 2.5;
        ctx.shadowColor = '#ff0055';
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.moveTo(this.lastTrace.path[0].x, this.lastTrace.path[0].y);
        for (let i = 1; i < this.lastTrace.path.length; i++) {
          ctx.lineTo(this.lastTrace.path[i].x, this.lastTrace.path[i].y);
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
      }

      // Metrics display
      const bounces = this.lastTrace ? this.lastTrace.bounces : 0;
      ctx.fillStyle = '#ffb000';
      ctx.font = '13px Courier New';
      ctx.fillText(`RECURSION DEPTH: ${bounces} / 500 CALLS`, 40, 580);
    }
  },

  // -------------------------------------------------------------
  // LEVEL 2: FLOAT_DIVIDE_BY_ZERO (Math Logic Singularity)
  // -------------------------------------------------------------
  {
    id: 2,
    name: "FLOAT DIVIDE BY ZERO",
    code: "0xC0000094",
    objective: "TRIGGER MATH SINGULARITY (MASS / 0 = NaN)",
    instructions: "Drag the Ghost Cube (0 kg) into the Divisor Slot of the physics scale.",
    init: function(width, height) {
      this.items = [
        { id: 'w10', type: 'weight', mass: 10, pos: new Vector2(140, 420), w: 60, h: 60, label: '10 kg', special: false },
        { id: 'w5',  type: 'weight', mass: 5,  pos: new Vector2(240, 420), w: 50, h: 50, label: '5 kg', special: false },
        { id: 'w0',  type: 'weight', mass: 0,  pos: new Vector2(340, 420), w: 40, h: 40, label: 'Ghost (0 kg)', special: true }
      ];

      this.slots = {
        dividend: { x: 530, y: 220, w: 110, h: 90, label: 'Numerator Slot', held: null },
        divisor:  { x: 730, y: 220, w: 110, h: 90, label: 'Divisor Slot [/]', held: null }
      };
    },
    update: function(engine, dt) {
      // Check if both slots are filled
      for (const slotKey in this.slots) {
        const slot = this.slots[slotKey];
        slot.held = null;
        for (const item of this.items) {
          const itemCenter = new Vector2(item.pos.x + item.w / 2, item.pos.y + item.h / 2);
          const slotCenter = new Vector2(slot.x + slot.w / 2, slot.y + slot.h / 2);
          if (itemCenter.dist(slotCenter) < 45) {
            slot.held = item;
          }
        }
      }

      if (this.slots.dividend.held && this.slots.divisor.held) {
        const num = this.slots.dividend.held.mass;
        const den = this.slots.divisor.held.mass;

        if (den === 0) {
          return {
            crashed: true,
            code: this.code,
            title: "💥 HARDWARE TRAP: FLOAT_DIVIDE_BY_ZERO",
            desc: "Physics Solver evaluated momentum using unhandled divisor of 0. ALU threw NaN exception.",
            dump: `Formula: ${num} kg ÷ 0 kg = NaN (Infinity)<br>Register EAX: 0x7FFFFFFF (Invalid Floating Point State)<br>Vector Collapse: Gravity inverted to NaN.`
          };
        }
      }
      return { crashed: false };
    },
    render: function(ctx) {
      // Draw Slots
      for (const key in this.slots) {
        const slot = this.slots[key];
        ctx.strokeStyle = '#ffb000';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(slot.x, slot.y, slot.w, slot.h);
        ctx.fillStyle = 'rgba(255, 176, 0, 0.08)';
        ctx.fillRect(slot.x, slot.y, slot.w, slot.h);

        ctx.fillStyle = '#ffb000';
        ctx.font = '11px monospace';
        ctx.fillText(slot.label, slot.x + 8, slot.y - 10);
      }

      // Draw Equation symbols
      ctx.fillStyle = '#ffffff';
      ctx.font = '40px monospace';
      ctx.fillText("÷", 670, 275);
      ctx.fillText("=", 865, 275);

      // Draw Result Indicator
      const num = this.slots.dividend.held ? this.slots.dividend.held.mass : null;
      const den = this.slots.divisor.held ? this.slots.divisor.held.mass : null;

      ctx.fillStyle = '#33ff33';
      ctx.font = '20px Courier New';
      if (num !== null && den !== null) {
        if (den === 0) {
          ctx.fillStyle = '#ff0055';
          ctx.fillText("NaN", 895, 275);
        } else {
          ctx.fillText((num / den).toFixed(2), 895, 275);
        }
      } else {
        ctx.fillStyle = '#666';
        ctx.fillText("...", 895, 275);
      }

      // Draw draggable weights
      for (const item of this.items) {
        ctx.fillStyle = item.special ? '#ff0055' : '#3b82f6';
        ctx.fillRect(item.pos.x, item.pos.y, item.w, item.h);
        ctx.strokeStyle = '#ffffff';
        ctx.strokeRect(item.pos.x, item.pos.y, item.w, item.h);

        ctx.fillStyle = '#ffffff';
        ctx.font = '11px monospace';
        ctx.fillText(item.label, item.pos.x + 4, item.pos.y + item.h / 2 + 4);
      }
    }
  },

  // -------------------------------------------------------------
  // LEVEL 3: HEAP BUFFER OVERFLOW (Entity Array Exhaustion)
  // -------------------------------------------------------------
  {
    id: 3,
    name: "HEAP BUFFER OVERFLOW",
    code: "0xC0000005",
    objective: "OVERLOAD ENTITY CONTAINER (> 128 ENTITIES)",
    instructions: "Drag the Duplication Gate into the particle bounce path to create an exponential entity explosion.",
    init: function(width, height) {
      this.particles = [];
      this.emitter = { pos: new Vector2(100, 180), timer: 0, interval: 35 };
      this.items = [
        {
          id: 'gate',
          type: 'gate',
          pos: new Vector2(400, 260),
          w: 160,
          h: 30,
          label: 'Duplication Gate [x2]'
        }
      ];
      this.bounds = { left: 40, right: 920, top: 90, bottom: 580 };
    },
    update: function(engine, dt) {
      // Emit initial particles
      this.emitter.timer++;
      if (this.emitter.timer > this.emitter.interval && this.particles.length < 160) {
        this.emitter.timer = 0;
        this.particles.push(new Particle(
          this.emitter.pos.x,
          this.emitter.pos.y,
          4.0,
          (Math.random() - 0.5) * 3,
          6
        ));
      }

      const gate = this.items[0];
      const newParticles = [];

      // Update particles
      for (const p of this.particles) {
        p.update(this.bounds);

        // Check Duplication Gate intersection
        if (p.pos.x > gate.pos.x && p.pos.x < gate.pos.x + gate.w &&
            p.pos.y > gate.pos.y && p.pos.y < gate.pos.y + gate.h) {
          if (!p.duplicated && this.particles.length < 160) {
            p.duplicated = true;
            newParticles.push(new Particle(
              p.pos.x,
              p.pos.y - 12,
              -p.vel.x,
              -p.vel.y + (Math.random() - 0.5) * 2,
              p.radius
            ));
            window.sfx.playRayBounce(900);
          }
        }
      }

      this.particles.push(...newParticles);

      if (this.particles.length >= 128) {
        return {
          crashed: true,
          code: this.code,
          title: "💥 FATAL: HEAP_BUFFER_OVERFLOW",
          desc: "Entity array buffer exceeded 128 elements. Memory allocation threw unhandled OOM error.",
          dump: `Buffer: ParticleList[128]<br>Attempted write at index 129.<br>Status: SEGMENTATION_FAULT at 0xDEADBEEF`
        };
      }
      return { crashed: false };
    },
    render: function(ctx) {
      // Draw Emitter
      ctx.fillStyle = '#10b981';
      ctx.fillRect(this.emitter.pos.x - 20, this.emitter.pos.y - 20, 40, 40);
      ctx.fillStyle = '#fff';
      ctx.font = '10px monospace';
      ctx.fillText("PARTICLE_SRC", this.emitter.pos.x - 40, this.emitter.pos.y - 26);

      // Draw Duplication Gate
      const gate = this.items[0];
      ctx.fillStyle = 'rgba(234, 179, 8, 0.35)';
      ctx.fillRect(gate.pos.x, gate.pos.y, gate.w, gate.h);
      ctx.strokeStyle = '#eab308';
      ctx.lineWidth = 2;
      ctx.strokeRect(gate.pos.x, gate.pos.y, gate.w, gate.h);

      ctx.fillStyle = '#fff';
      ctx.font = '11px monospace';
      ctx.fillText(gate.label, gate.pos.x + 8, gate.pos.y + 20);

      // Draw Particles
      for (const p of this.particles) {
        ctx.fillStyle = p.duplicated ? '#f43f5e' : '#38bdf8';
        ctx.beginPath();
        ctx.arc(p.pos.x, p.pos.y, p.radius, 0, Math.PI * 2);
        ctx.fill();
      }

      // Memory monitor
      ctx.fillStyle = '#ffb000';
      ctx.font = '13px Courier New';
      ctx.fillText(`HEAP UTILIZATION: ${this.particles.length} / 128 ENTITIES`, 40, 580);
    }
  },

  // -------------------------------------------------------------
  // LEVEL 4: NULL_POINTER_DEREFERENCE (Destructor Race Condition)
  // -------------------------------------------------------------
  {
    id: 4,
    name: "NULL POINTER DEREFERENCE",
    code: "0x00000000",
    objective: "DESTROY OBJECT WHILE SENSOR READS ITS ADDRESS",
    instructions: "Align the target block so it is scanned and vaporized simultaneously by both lasers.",
    init: function(width, height) {
      this.scanner = { pos: new Vector2(300, 160), targetY: 480 };
      this.disintegrator = { pos: new Vector2(600, 160), targetY: 480 };
      this.items = [
        {
          id: 'block',
          type: 'block',
          pos: new Vector2(420, 280),
          w: 70,
          h: 70,
          label: 'Object_0x8F'
        }
      ];
    },
    update: function(engine, dt) {
      const block = this.items[0];
      const scanHit = (block.pos.x <= this.scanner.pos.x && block.pos.x + block.w >= this.scanner.pos.x);
      const disHit = (block.pos.x <= this.disintegrator.pos.x && block.pos.x + block.w >= this.disintegrator.pos.x);

      // If both lasers touch the block simultaneously:
      if (scanHit && disHit) {
        return {
          crashed: true,
          code: this.code,
          title: "💥 CRITICAL: NULL_POINTER_EXCEPTION",
          desc: "Scanner laser attempted to read memory address 0x00000000 while Disintegrator purged it from the heap.",
          dump: `Race Condition: Thread 1 (Read) clashed with Thread 2 (Free).<br>Address: [0x00000000] -> Access Violation.<br>Status: KERNEL PANIC.`
        };
      }
      return { crashed: false };
    },
    render: function(ctx) {
      // Draw Scanner Laser
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(this.scanner.pos.x, this.scanner.pos.y);
      ctx.lineTo(this.scanner.pos.x, this.scanner.targetY);
      ctx.stroke();

      ctx.fillStyle = '#00f0ff';
      ctx.font = '10px monospace';
      ctx.fillText("READ_SENSOR [ADDR]", this.scanner.pos.x - 55, this.scanner.pos.y - 12);

      // Draw Disintegrator Laser
      ctx.strokeStyle = '#f43f5e';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(this.disintegrator.pos.x, this.disintegrator.pos.y);
      ctx.lineTo(this.disintegrator.pos.x, this.disintegrator.targetY);
      ctx.stroke();

      ctx.fillStyle = '#f43f5e';
      ctx.font = '10px monospace';
      ctx.fillText("DISINTEGRATOR [FREE]", this.disintegrator.pos.x - 55, this.disintegrator.pos.y - 12);

      // Draw Block
      const block = this.items[0];
      ctx.fillStyle = '#e2e8f0';
      ctx.fillRect(block.pos.x, block.pos.y, block.w, block.h);
      ctx.strokeStyle = '#475569';
      ctx.strokeRect(block.pos.x, block.pos.y, block.w, block.h);

      ctx.fillStyle = '#0f172a';
      ctx.font = '11px monospace';
      ctx.fillText(block.label, block.pos.x + 6, block.pos.y + 38);
    }
  }
];

window.GameLevels = GameLevels;
