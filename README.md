# 💥 CRASH TO DESKTOP: Fatal Exception

> **A reverse-engineering puzzle game where stability is the enemy and crashes are the victory condition.**  
> *Developed for the BYOG (Build Your Own Game) Hackathon (24-Hour Jam Edition).*

---

## 🎮 The Premise

In 99.9% of games, developers fight for 60 FPS, defensive boundary checks, and zero bugs.

In **CRASH TO DESKTOP**, you play as a rogue automated Quality Assurance entity trapped inside a sterile, indestructible physics testing chamber overseen by an arrogant engine supervisor:

> *"Our engine is mathematically uncrashable. Try me."*

Your only objective is to break the engine's laws of computation, provoke unhandled hardware traps, and force a simulated fatal exception modal.

---

## 🧠 Forensic DNA from Past BYOG Winners

* **Meta-UI Subversion** (*inspired by Press Start to Play - BYOG 2022*): The win condition is not reaching a flagpole; it's triggering an authentic retro OS crash modal dialog complete with hex dump addresses and faulting threads.
* **Deductive Exploitation** (*inspired by Xenolingo - BYOG 2022*): You are not told how to win; you must deduce how to exploit the underlying physics math.
* **Visual Systems Thinking** (*inspired by Nodesmith - BYOG 2024*): Manipulate mirrors, balance scales, and particle splitters in real-time.
* **Mechanic by Subtraction** (*inspired by Timeless Space*): Zero health bars, zero coins, zero enemies. Pure mechanical elegance.

---

## 🧩 The Puzzle Levels

| Level | Exploit Name | Computer Science Vulnerability | Winning Condition |
| :---: | :--- | :--- | :--- |
| **01** | `STACK_OVERFLOW` | Infinite Raycast Recursion | Align opposing portal mirrors so the laser bounces endlessly ($> 500$ recursive raycast steps). |
| **02** | `FLOAT_DIVIDE_BY_ZERO` | Arithmetic Logic Unit Singularity | Drop the Ghost Mass ($0\text{ kg}$) into the Divisor Slot of the scale to compute $\text{Mass} / 0 = \text{NaN}$. |
| **03** | `HEAP_BUFFER_OVERFLOW` | Dynamic Entity Array Exhaustion | Route particle streams into a closed feedback loop through the Duplication Gate until entity count exceeds 128. |
| **04** | `NULL_POINTER_EXCEPTION` | Free-After-Use Race Condition | Align the target block so the scanner laser reads its memory address on the exact frame the disintegrator laser purges it. |

---

## 🚀 How to Play Locally

The entire game is **100% self-contained**:
* Zero build steps.
* Zero external npm packages.
* Zero external audio files (all sound effects are synthesized via procedural Web Audio API in real time).
* Loads in under 100 milliseconds.

### Quick Start
1. Clone this repository:
   ```bash
   git clone https://github.com/rk-3001/game_dev.git
   cd game_dev
   ```
2. Open `index.html` in any web browser (Chrome, Firefox, Safari, Edge):
   ```bash
   # On macOS
   open index.html

   # Or via Python local server:
   python3 -m http.server 8000
   # Then visit http://localhost:8000
   ```

---

## 📦 Itch.io WebGL / HTML5 Deployment

To publish this game to [itch.io](https://itch.io):
1. Zip the repository contents (`index.html`, `css/`, `src/`).
2. On your itch.io project dashboard, choose:
   - **Kind of project**: `HTML`
   - Check **"This file will be played in the browser"**
   - Embed viewport: `960` x `640`
3. Upload the `.zip` file and publish!

---

## 🛠️ Tech Stack

* **Language**: Vanilla JavaScript (ES6+)
* **Rendering**: HTML5 Canvas 2D with phosphor CRT scanlines & post-processing
* **Audio**: Web Audio API (procedural frequency modulation, saw/square wave buffers, chiptune arpeggios)
* **Styling**: Retro Windows 98 / 2000 OS Window Manager with draggable modals and CRT screen shake