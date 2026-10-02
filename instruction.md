# Instruction Blueprint: CRASH TO DESKTOP (BYOG Edition)

## 1. Project Overview & Design Philosophy

**CRASH TO DESKTOP: Fatal Exception** is an out-of-the-box physics/logic puzzle game designed for the **BYOG (Build Your Own Game)** game jam. 

### The Core Subversion
Most games strive for 60 FPS stability and zero bugs. In this game, you play as a rogue automated QA entity trapped in an arrogant game engine's test suite. **Your only objective is to break the engine's laws of computation and cause simulated fatal exceptions.**

### The Winning DNA
* **Meta-UI Subversion** (*inspired by Press Start to Play*): Classic retro OS windows, interactive crash dump modals, draggable title bars, Task Manager monitors.
* **Deductive Puzzle Mechanics** (*inspired by Xenolingo*): Deciphering how to force computational singularities (recursion limits, division by zero, heap exhaustion).
* **Tactile Systems Thinking** (*inspired by Nodesmith*): Manipulating mirrors, mass scales, and particle splitters in real-time.
* **Browser-First Architecture**: 100% self-contained HTML5 Canvas + Web Audio API. Zero runtime bloat, instant 100ms load time, zero install dependencies, runs on any browser and itch.io WebGL container.

---

## 2. Step-by-Step Execution Plan

### Step 1: Repository Foundation & File Structure
- [ ] Initialize repository structure with clean modular separation:
  - `index.html`: Master entry point, retro CRT frame, retro OS styling.
  - `css/style.css`: CRT scanlines, vignette, retro window styling, CRT flicker.
  - `src/audio.js`: Web Audio API procedural sound synthesizer (no external MP3/WAV files needed).
  - `src/engine.js`: 2D vector math, physics simulation, raycaster, collision detector.
  - `src/ui.js`: Draggable retro OS windows, fake BSOD, error dump generator, HUD.
  - `src/levels.js`: Distinct puzzle levels with unique crash triggers.
  - `src/main.js`: Game loop orchestrator and state machine.

### Step 2: Procedural Web Audio Engine (`src/audio.js`)
- [ ] Implement zero-asset audio synthesizer using Web Audio API:
  - Mechanical UI clicks and relay switches.
  - Laser/raycast frequency pitches (escalating pitch as recursion increases).
  - Harsh 120Hz buffer-stutter square/saw crash buzzer.
  - Cheerful 8-bit victory arpeggio on level clear.
  - Low-frequency hum for active emitters.

### Step 3: Core Physics & Raycasting Engine (`src/engine.js`)
- [ ] Implement 2D physics primitives:
  - Vector arithmetic (add, sub, dot, reflect, length).
  - Raycaster with iterative step calculations and recursion counters.
  - Rigid bodies with mass, velocity, acceleration, and bounce restitution.
  - Drag-and-drop interactables with coordinate transforms.

### Step 4: Meta-OS Interface & Crash Dialog System (`src/ui.js`)
- [ ] Implement authentic Windows 98 / 2000 style window manager:
  - Draggable modal dialogs with title bar controls.
  - Real-time Task Manager showing simulated CPU/Memory/Stability meters.
  - Interactive Crash Dialog: Fault address, stack trace preview, retry & advance buttons.
  - Screen-shake and chromatic aberration triggers on fatal exception.

### Step 5: Puzzle Level Implementations (`src/levels.js`)
- [ ] **Level 1: STACK_OVERFLOW** (Infinite Raycast Recursion)
  - Laser emitter + two movable portal reflectors. Placing them face-to-face exceeds max recursion depth (> 500 bounces).
- [ ] **Level 2: FLOAT_DIVIDE_BY_ZERO** (Arithmetic Logic Failure)
  - Inertial scale machine. Placing a 0 kg ghost mass into the divisor slot creates `NaN` acceleration, flinging objects into the void.
- [ ] **Level 3: HEAP_BUFFER_OVERFLOW** (Entity Array Exhaustion)
  - Particle duplicator chamber. Routing particles in an endless feedback loop explodes the entity count (> 128 items), degrading simulated FPS to 0.
- [ ] **Level 4: NULL_POINTER_DEREFERENCE** (Destructor Race Condition)
  - Optical property sensor + laser disintegrator. Destroying an object on the exact frame the sensor reads its memory address throws a null pointer exception.
- [ ] **Level 5: TOTAL_SYSTEM_ANNIHILATION** (Grand Finale)
  - Combine multiple computational hazards simultaneously to bring down the kernel.

### Step 6: Master Assembly & CRT Visual Styling (`index.html`, `css/style.css`, `src/main.js`)
- [ ] Bind all components into the master game loop.
- [ ] Add retro phosphor glow, scanline overlay, and status HUD.
- [ ] Ensure full keyboard/mouse responsiveness.

### Step 7: Local Verification & Automated Testing
- [ ] Verify no JavaScript syntax errors or unhandled console exceptions.
- [ ] Test every level win condition and crash trigger.
- [ ] Verify Web Audio initializes properly on first user interaction.
- [ ] Launch local HTTP server to verify in browser.

### Step 8: Git Commit & Documentation
- [ ] Update `README.md` with gameplay instructions, controls, game jam design lore, and itch.io deployment steps.
- [ ] Stage and commit all code cleanly to the repository.
- [ ] Push to `https://github.com/rk-3001/game_dev.git`.
