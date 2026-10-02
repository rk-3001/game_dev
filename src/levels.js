/**
 * CRASH TO DESKTOP - Puzzle Levels Definition
 * Five handcrafted, visually striking, interactive computer science exploits.
 */

const GameLevels = [
  // -------------------------------------------------------------
  // LEVEL 1: STACK OVERFLOW (Portal Raycast Feedback)
  // -------------------------------------------------------------
  {
    id: 1,
    name: "STACK OVERFLOW",
    code: "0x00FF4B22",
    objective: "TRAP LASER IN INFINITE PORTAL LOOP (> 500 BOUNCES)",
    instructions: "Drag Portal Alpha (Cyan) into the laser path, and align Portal Beta (Magenta) facing straight back into Alpha.",
    hint: "Place Cyan Portal in the laser path. Move Magenta Portal to the right, aiming its arrow back into Cyan's aperture.",
    init: function(width, height) {
      this.emitter = { pos: new Vector2(70, 300), dir: new Vector2(1, 0) };
      this.items = [
        {
          id: 'portalA',
          type: 'portal',
          label: 'PORTAL ALPHA',
          color: '#00f0ff',
          pos: new Vector2(280, 240),
          w: 48,
          h: 120,
          entryNormal: new Vector2(1, 0), // accepts beam coming from left
          exitDir: new Vector2(1, 0),      // shoots right
          angle: 0
        },
        {
          id: 'portalB',
          type: 'portal',
          label: 'PORTAL BETA',
          color: '#ec4899',
          pos: new Vector2(620, 240),
          w: 48,
          h: 120,
          entryNormal: new Vector2(-1, 0), // accepts beam coming from right
          exitDir: new Vector2(-1, 0),     // shoots left back into Alpha
          angle: Math.PI
        }
      ];
      this.obstacles = [
        { pos: new Vector2(450, 80), w: 60, h: 100, label: 'Baffle Wall' }
      ];
      this.currentBounces = 0;
      this.lastSparks = [];
    },
    update: function(engine, dt) {
      const portalA = this.items[0];
      const portalB = this.items[1];

      const trace = RaycastSolver.traceWithPortals(
        this.emitter.pos,
        this.emitter.dir,
        portalA,
        portalB,
        this.obstacles,
        500
      );

      this.lastTrace = trace;
      this.currentBounces = trace.bounces;

      // Spawn sparks at bounce locations
      if (trace.sparks && trace.sparks.length > 0 && Math.random() < 0.4) {
        const spark = trace.sparks[Math.floor(Math.random() * trace.sparks.length)];
        engine.particles.emit(spark.x, spark.y, 4, '#00f0ff', 2.5);
      }

      if (trace.bounces > 10 && trace.bounces % 20 === 0) {
        window.sfx.playRayBounce(trace.bounces);
      }

      if (trace.bounces >= 500) {
        return {
          crashed: true,
          code: this.code,
          title: "💥 FATAL EXCEPTION: STACK_OVERFLOW",
          desc: "Raycast function recursion depth exceeded 500 nested calls without termination.",
          dump: `Faulting Thread: 0x8A4 (Renderer_Raytracer)<br>Call Stack: 512 frames allocated, 0 returned.<br>Vector: Portal Alpha ⇄ Portal Beta feedback loop.`
        };
      }
      return { crashed: false };
    },
    render: function(ctx, engine) {
      // Draw Laser Emitter Unit
      ctx.save();
      ctx.fillStyle = '#0f172a';
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 2;
      ctx.strokeRect(this.emitter.pos.x - 40, this.emitter.pos.y - 25, 40, 50);
      ctx.fillRect(this.emitter.pos.x - 40, this.emitter.pos.y - 25, 40, 50);

      // Core glow
      ctx.fillStyle = '#00f0ff';
      ctx.shadowColor = '#00f0ff';
      ctx.shadowBlur = 15;
      ctx.beginPath();
      ctx.arc(this.emitter.pos.x - 15, this.emitter.pos.y, 10, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.fillStyle = '#38bdf8';
      ctx.font = 'bold 11px monospace';
      ctx.fillText("LASER_SRC", this.emitter.pos.x - 55, this.emitter.pos.y - 32);

      // Draw Obstacles
      for (const obs of this.obstacles) {
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(obs.pos.x, obs.pos.y, obs.w, obs.h);
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 2;
        ctx.strokeRect(obs.pos.x, obs.pos.y, obs.w, obs.h);
        ctx.fillStyle = '#64748b';
        ctx.font = '10px monospace';
        ctx.fillText(obs.label, obs.pos.x + 4, obs.pos.y + obs.h / 2);
      }

      // Draw Portals
      for (const portal of this.items) {
        ctx.save();
        const isHovered = engine.hoveredItem === portal;
        const isDragged = engine.draggedItem === portal;

        // Outer Glow Frame
        ctx.fillStyle = isDragged ? 'rgba(255,255,255,0.1)' : 'rgba(15,23,42,0.85)';
        ctx.strokeStyle = isHovered ? '#ffffff' : portal.color;
        ctx.lineWidth = isHovered ? 3 : 2;
        ctx.shadowColor = portal.color;
        ctx.shadowBlur = isDragged ? 25 : 15;
        ctx.strokeRect(portal.pos.x, portal.pos.y, portal.w, portal.h);
        ctx.fillRect(portal.pos.x, portal.pos.y, portal.w, portal.h);

        // Animated Portal Swirl Center
        ctx.fillStyle = portal.color;
        ctx.beginPath();
        ctx.ellipse(
          portal.pos.x + portal.w / 2,
          portal.pos.y + portal.h / 2,
          portal.w / 3,
          portal.h / 2.5,
          0, 0, Math.PI * 2
        );
        ctx.fill();

        // Directional Arrow
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 16px monospace';
        const arrow = portal.exitDir.x > 0 ? "➔" : "⬅";
        ctx.fillText(arrow, portal.pos.x + 16, portal.pos.y + portal.h / 2 + 6);

        // Label
        ctx.fillStyle = portal.color;
        ctx.font = 'bold 11px monospace';
        ctx.fillText(portal.label, portal.pos.x - 12, portal.pos.y - 12);
        ctx.restore();
      }

      // Draw Laser Beam
      if (this.lastTrace && this.lastTrace.path.length > 1) {
        ctx.save();
        ctx.strokeStyle = '#ff0055';
        ctx.lineWidth = 3.5;
        ctx.shadowColor = '#ff0055';
        ctx.shadowBlur = 18;
        ctx.beginPath();
        ctx.moveTo(this.lastTrace.path[0].x, this.lastTrace.path[0].y);
        for (let i = 1; i < this.lastTrace.path.length; i++) {
          ctx.lineTo(this.lastTrace.path[i].x, this.lastTrace.path[i].y);
        }
        ctx.stroke();

        // White core laser beam
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.2;
        ctx.stroke();
        ctx.restore();
      }
    }
  },

  // -------------------------------------------------------------
  // LEVEL 2: FLOAT DIVIDE BY ZERO (Math Singularity)
  // -------------------------------------------------------------
  {
    id: 2,
    name: "FLOAT DIVIDE BY ZERO",
    code: "0xC0000094",
    objective: "PROVOKE ARITHMETIC SINGULARITY (10 KG ÷ 0 KG = NaN)",
    instructions: "Place a mass in the Numerator Slot, and place the 0 kg Ghost Singularity into the Divisor Slot.",
    hint: "Drag the 10 kg Tungsten Core into the left slot, and the 0 kg Ghost Void into the right slot.",
    init: function(width, height) {
      this.items = [
        { id: 'w10', type: 'weight', mass: 10, pos: new Vector2(100, 430), w: 65, h: 65, label: '10 kg [Tungsten]', color: '#38bdf8' },
        { id: 'w4',  type: 'weight', mass: 4,  pos: new Vector2(210, 430), w: 55, h: 55, label: '4 kg [Carbon]',    color: '#818cf8' },
        { id: 'w0',  type: 'weight', mass: 0,  pos: new Vector2(320, 430), w: 50, h: 50, label: '0 kg [GHOST VOID]', color: '#f43f5e', special: true }
      ];

      this.slots = {
        dividend: { x: 500, y: 210, w: 120, h: 100, label: 'NUMERATOR [MASS]', held: null },
        divisor:  { x: 740, y: 210, w: 120, h: 100, label: 'DIVISOR [/ ACCEL]', held: null }
      };
      this.currentCalc = null;
    },
    update: function(engine, dt) {
      for (const slotKey in this.slots) {
        const slot = this.slots[slotKey];
        slot.held = null;
        for (const item of this.items) {
          const itemCenter = new Vector2(item.pos.x + item.w / 2, item.pos.y + item.h / 2);
          const slotCenter = new Vector2(slot.x + slot.w / 2, slot.y + slot.h / 2);
          if (itemCenter.dist(slotCenter) < 55) {
            slot.held = item;
          }
        }
      }

      const num = this.slots.dividend.held ? this.slots.dividend.held.mass : null;
      const den = this.slots.divisor.held ? this.slots.divisor.held.mass : null;

      if (num !== null && den !== null) {
        if (den === 0) {
          this.currentCalc = 'NaN';
          engine.particles.emit(800, 260, 12, '#ff0055', 4);
          return {
            crashed: true,
            code: this.code,
            title: "💥 HARDWARE TRAP: FLOAT_DIVIDE_BY_ZERO",
            desc: "Physics Solver evaluated momentum using unhandled divisor of 0. ALU threw NaN exception.",
            dump: `Formula: ${num} kg ÷ 0 kg = NaN (Infinity)<br>Register EAX: 0x7FFFFFFF (Invalid Floating Point State)<br>Vector Collapse: Gravity inverted to NaN.`
          };
        } else {
          this.currentCalc = (num / den).toFixed(2);
        }
      } else {
        this.currentCalc = null;
      }
      return { crashed: false };
    },
    render: function(ctx, engine) {
      // Draw Scale Pedestals
      for (const key in this.slots) {
        const slot = this.slots[key];
        const isOccupied = slot.held !== null;

        ctx.save();
        ctx.fillStyle = isOccupied ? 'rgba(56, 189, 248, 0.12)' : 'rgba(15, 23, 42, 0.7)';
        ctx.strokeStyle = isOccupied ? '#38bdf8' : '#eab308';
        ctx.lineWidth = 2;
        ctx.shadowColor = isOccupied ? '#38bdf8' : '#eab308';
        ctx.shadowBlur = 12;
        ctx.strokeRect(slot.x, slot.y, slot.w, slot.h);
        ctx.fillRect(slot.x, slot.y, slot.w, slot.h);

        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 11px monospace';
        ctx.fillText(slot.label, slot.x + 8, slot.y - 12);
        ctx.restore();
      }

      // Draw Equation Operators
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 44px monospace';
      ctx.fillText("÷", 655, 275);
      ctx.fillText("=", 885, 275);

      // Result Box
      ctx.save();
      ctx.fillStyle = '#0f172a';
      ctx.strokeStyle = '#38bdf8';
      ctx.strokeRect(930, 220, 100, 80);
      ctx.fillRect(930, 220, 100, 80);

      ctx.fillStyle = this.currentCalc === 'NaN' ? '#f43f5e' : '#33ff33';
      ctx.font = 'bold 22px monospace';
      ctx.fillText(this.currentCalc !== null ? this.currentCalc : "...", 945, 268);
      ctx.restore();

      // Draw Draggable Weights
      for (const item of this.items) {
        ctx.save();
        const isHovered = engine.hoveredItem === item;
        const isDragged = engine.draggedItem === item;

        ctx.fillStyle = isDragged ? '#ffffff' : item.color;
        ctx.shadowColor = item.color;
        ctx.shadowBlur = isHovered ? 20 : 10;
        ctx.fillRect(item.pos.x, item.pos.y, item.w, item.h);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.strokeRect(item.pos.x, item.pos.y, item.w, item.h);

        ctx.fillStyle = '#000000';
        ctx.font = 'bold 10px monospace';
        ctx.fillText(item.label, item.pos.x + 4, item.pos.y + item.h / 2 + 4);
        ctx.restore();
      }
    }
  },

  // -------------------------------------------------------------
  // LEVEL 3: HEAP BUFFER OVERFLOW (Particle Fission)
  // -------------------------------------------------------------
  {
    id: 3,
    name: "HEAP BUFFER OVERFLOW",
    code: "0xC0000005",
    objective: "OVERLOAD ENTITY CONTAINER (> 128 QUANTUM PARTICLES)",
    instructions: "Drag the Fission Gate [x2] into the particle bounce path to create an exponential entity explosion.",
    hint: "Move the Fission Gate to the center and position the Bouncer pad to reflect particles back through the gate.",
    init: function(width, height) {
      this.particles = [];
      this.spawner = { pos: new Vector2(100, 200), timer: 0, rate: 30 };
      this.items = [
        {
          id: 'gate',
          type: 'gate',
          pos: new Vector2(380, 260),
          w: 180,
          h: 36,
          label: 'FISSION GATE [x2 SPLITTER]',
          color: '#eab308'
        },
        {
          id: 'bouncer',
          type: 'bouncer',
          pos: new Vector2(680, 360),
          w: 24,
          h: 150,
          label: 'REFLECTOR',
          color: '#38bdf8'
        }
      ];
      this.bounds = { left: 40, right: 920, top: 90, bottom: 570 };
    },
    update: function(engine, dt) {
      this.spawner.timer++;
      if (this.spawner.timer > this.spawner.rate && this.particles.length < 160) {
        this.spawner.timer = 0;
        this.particles.push(new PhysicsParticle(
          this.spawner.pos.x,
          this.spawner.pos.y,
          4.5,
          (Math.random() - 0.5) * 3,
          7,
          '#38bdf8'
        ));
      }

      const gate = this.items[0];
      const bouncer = this.items[1];
      const newParticles = [];

      for (const p of this.particles) {
        p.update(this.bounds);

        // Check Bouncer collision
        if (p.pos.x > bouncer.pos.x && p.pos.x < bouncer.pos.x + bouncer.w &&
            p.pos.y > bouncer.pos.y && p.pos.y < bouncer.pos.y + bouncer.h) {
          p.vel.x = -Math.abs(p.vel.x) * 1.05;
          engine.particles.emit(p.pos.x, p.pos.y, 6, '#38bdf8', 3);
          window.sfx.playClick();
        }

        // Check Fission Gate collision
        if (p.pos.x > gate.pos.x && p.pos.x < gate.pos.x + gate.w &&
            p.pos.y > gate.pos.y && p.pos.y < gate.pos.y + gate.h) {
          if (!p.duplicated && this.particles.length < 160) {
            p.duplicated = true;
            newParticles.push(new PhysicsParticle(
              p.pos.x,
              p.pos.y - 15,
              -p.vel.x * 1.02,
              -p.vel.y + (Math.random() - 0.5) * 2,
              7,
              '#f43f5e'
            ));
            engine.particles.emit(p.pos.x, p.pos.y, 8, '#eab308', 3);
            window.sfx.playSplitParticle();
          }
        }
      }

      this.particles.push(...newParticles);

      if (this.particles.length >= 128) {
        return {
          crashed: true,
          code: this.code,
          title: "💥 FATAL: HEAP_BUFFER_OVERFLOW",
          desc: "Dynamic Entity Container exceeded 128 active references. Memory allocator threw unhandled OOM error.",
          dump: `Allocated: ParticleList[128]<br>Attempted write at index 129.<br>Status: SEGMENTATION_FAULT at 0xDEADBEEF`
        };
      }
      return { crashed: false };
    },
    render: function(ctx, engine) {
      // Draw Spawner
      ctx.save();
      ctx.fillStyle = '#10b981';
      ctx.shadowColor = '#10b981';
      ctx.shadowBlur = 15;
      ctx.fillRect(this.spawner.pos.x - 25, this.spawner.pos.y - 25, 50, 50);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px monospace';
      ctx.fillText("PARTICLE_CANNON", this.spawner.pos.x - 45, this.spawner.pos.y - 32);
      ctx.restore();

      // Draw Fission Gate & Bouncer
      for (const item of this.items) {
        ctx.save();
        const isHovered = engine.hoveredItem === item;
        const isDragged = engine.draggedItem === item;

        ctx.fillStyle = isDragged ? 'rgba(255,255,255,0.2)' : 'rgba(15,23,42,0.85)';
        ctx.strokeStyle = item.color;
        ctx.lineWidth = isHovered ? 3 : 2;
        ctx.shadowColor = item.color;
        ctx.shadowBlur = isHovered ? 20 : 12;
        ctx.strokeRect(item.pos.x, item.pos.y, item.w, item.h);
        ctx.fillRect(item.pos.x, item.pos.y, item.w, item.h);

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px monospace';
        ctx.fillText(item.label, item.pos.x + 8, item.pos.y + item.h / 2 + 4);
        ctx.restore();
      }

      // Draw Particles
      for (const p of this.particles) {
        p.draw(ctx);
      }

      // Live Heap Bar
      ctx.save();
      ctx.fillStyle = '#1e293b';
      ctx.fillRect(40, 560, 300, 20);
      const ratio = Math.min(1.0, this.particles.length / 128);
      ctx.fillStyle = ratio > 0.8 ? '#f43f5e' : '#38bdf8';
      ctx.fillRect(40, 560, 300 * ratio, 20);
      ctx.strokeStyle = '#64748b';
      ctx.strokeRect(40, 560, 300, 20);

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px monospace';
      ctx.fillText(`HEAP: ${this.particles.length} / 128 ENTITIES (${Math.round(ratio * 100)}%)`, 50, 575);
      ctx.restore();
    }
  },

  // -------------------------------------------------------------
  // LEVEL 4: NULL POINTER ACCESS VIOLATION (Destructor Collision)
  // -------------------------------------------------------------
  {
    id: 4,
    name: "NULL POINTER DEREFERENCE",
    code: "0x00000000",
    objective: "PURGE OBJECT EXACTLY AS MEMORY SENSOR READS ADDRESS",
    instructions: "Drag Memory Node 0x8F into the intersection point where the Scanner and Disintegrator beams cross.",
    hint: "Both beams intersect near the center. Drag the Memory Node right onto that crossing point!",
    init: function(width, height) {
      this.scanner = { pos: new Vector2(360, 140), target: new Vector2(360, 500) };
      this.disintegrator = { pos: new Vector2(600, 140), target: new Vector2(600, 500) };
      this.items = [
        {
          id: 'node',
          type: 'node',
          pos: new Vector2(460, 280),
          w: 80,
          h: 80,
          label: 'PTR [0x8F002B]',
          color: '#38bdf8'
        }
      ];
    },
    update: function(engine, dt) {
      const node = this.items[0];
      const scanHit = (node.pos.x <= this.scanner.pos.x && node.pos.x + node.w >= this.scanner.pos.x);
      const disHit = (node.pos.x <= this.disintegrator.pos.x && node.pos.x + node.w >= this.disintegrator.pos.x);

      if (scanHit && disHit) {
        engine.particles.emit(node.pos.x + node.w / 2, node.pos.y + node.h / 2, 20, '#f43f5e', 5);
        return {
          crashed: true,
          code: this.code,
          title: "💥 CRITICAL: ACCESS_VIOLATION_NULL_POINTER",
          desc: "Sensor Thread attempted to read memory address 0x00000000 while Disintegrator Thread purged it from the heap.",
          dump: `Race Condition: Thread 1 (Read) clashed with Thread 2 (Free).<br>Address: [0x00000000] -> Kernel Memory Protection Triggered.<br>Status: EXECUTION_ABORTED.`
        };
      }
      return { crashed: false };
    },
    render: function(ctx, engine) {
      // Draw Scanner Beam
      ctx.save();
      ctx.strokeStyle = '#00f0ff';
      ctx.lineWidth = 3;
      ctx.shadowColor = '#00f0ff';
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.moveTo(this.scanner.pos.x, this.scanner.pos.y);
      ctx.lineTo(this.scanner.target.x, this.scanner.target.y);
      ctx.stroke();

      ctx.fillStyle = '#00f0ff';
      ctx.font = 'bold 11px monospace';
      ctx.fillText("READ_SENSOR [ADDR]", this.scanner.pos.x - 65, this.scanner.pos.y - 16);
      ctx.restore();

      // Draw Disintegrator Beam
      ctx.save();
      ctx.strokeStyle = '#f43f5e';
      ctx.lineWidth = 3;
      ctx.shadowColor = '#f43f5e';
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.moveTo(this.disintegrator.pos.x, this.disintegrator.pos.y);
      ctx.lineTo(this.disintegrator.target.x, this.disintegrator.target.y);
      ctx.stroke();

      ctx.fillStyle = '#f43f5e';
      ctx.font = 'bold 11px monospace';
      ctx.fillText("FREE_DESTRUCTOR", this.disintegrator.pos.x - 55, this.disintegrator.pos.y - 16);
      ctx.restore();

      // Draw Memory Node
      const node = this.items[0];
      ctx.save();
      const isHovered = engine.hoveredItem === node;
      const isDragged = engine.draggedItem === node;

      ctx.fillStyle = isDragged ? '#ffffff' : '#0f172a';
      ctx.strokeStyle = node.color;
      ctx.lineWidth = isHovered ? 3 : 2;
      ctx.shadowColor = node.color;
      ctx.shadowBlur = isHovered ? 20 : 10;
      ctx.fillRect(node.pos.x, node.pos.y, node.w, node.h);
      ctx.strokeRect(node.pos.x, node.pos.y, node.w, node.h);

      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px monospace';
      ctx.fillText(node.label, node.pos.x + 6, node.pos.y + node.h / 2 + 4);
      ctx.restore();
    }
  }
];

window.GameLevels = GameLevels;
