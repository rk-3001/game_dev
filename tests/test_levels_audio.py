import unittest
import json
import math
import time
import sys
import os
import re
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_AUDIO = BASE_DIR / "src" / "audio.js"
SRC_LEVELS = BASE_DIR / "src" / "levels.js"

# ---------------------------------------------------------------------------
# Kinetic Vector2 & Particle Shims
# ---------------------------------------------------------------------------

class Vector2:
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def add(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def sub(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def scale(self, s: float) -> "Vector2":
        return Vector2(self.x * s, self.y * s)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def normalize(self) -> "Vector2":
        mag = self.length()
        return Vector2(self.x / mag, self.y / mag) if mag > 0 else Vector2(0, 0)


@dataclass
class Particle:
    position: Vector2
    velocity: Vector2
    lifetime: float = 1.0
    age: float = 0.0
    color: str = "#00f0ff"

    @property
    def alive(self) -> bool:
        return self.age < self.lifetime

    def update(self, dt: float) -> None:
        self.position = self.position.add(self.velocity.scale(dt))
        self.velocity = self.velocity.scale(0.95)
        self.age += dt


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit(self, position: Vector2, count: int = 12, speed: float = 200.0, color: str = "#00f0ff") -> None:
        for i in range(count):
            angle = (2 * math.pi / count) * i
            vel = Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
            self.particles.append(Particle(position=Vector2(position.x, position.y), velocity=vel, color=color))

    def update(self, dt: float) -> None:
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]


class ScreenShake:
    def __init__(self):
        self.intensity: float = 0.0
        self.offset: Vector2 = Vector2(0, 0)

    def trigger(self, amount: float) -> None:
        self.intensity = max(self.intensity, amount)

    def update(self, dt: float) -> None:
        if self.intensity > 0.05:
            self.intensity *= 0.85 ** (dt * 60)
        else:
            self.intensity = 0.0


# ---------------------------------------------------------------------------
# Level Mechanics Verification Suite
# ---------------------------------------------------------------------------

class TestLevelsConfig(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SRC_LEVELS.read_text(encoding="utf-8")

    def test_levels_file_exists(self):
        self.assertTrue(SRC_LEVELS.exists(), "src/levels.js must exist")

    def test_game_levels_array_defined(self):
        self.assertRegex(self.raw, r"const\s+GameLevels\s*=", "GameLevels array must be declared")

    def test_at_least_four_levels(self):
        matches = re.findall(r"name\s*:\s*[\"']([^\"']+)[\"']", self.raw)
        self.assertGreaterEqual(len(matches), 4, f"Expected at least 4 levels, found {len(matches)}: {matches}")

    def test_level_stack_overflow_present(self):
        self.assertIn("STACK OVERFLOW", self.raw, "Level 1: Stack Overflow exploit must be defined")

    def test_level_divide_by_zero_present(self):
        self.assertIn("DIVIDE BY ZERO", self.raw, "Level 2: Divide by Zero exploit must be defined")

    def test_level_heap_exhaustion_present(self):
        self.assertIn("HEAP BUFFER OVERFLOW", self.raw, "Level 3: Heap Buffer Overflow exploit must be defined")

    def test_level_kernel_panic_present(self):
        self.assertIn("NULL POINTER DEREFERENCE", self.raw, "Level 4: Null Pointer Dereference exploit must be defined")

    def test_level_objectives_and_hints_specified(self):
        objectives = re.findall(r"objective\s*:\s*[\"']([^\"']+)[\"']", self.raw)
        hints = re.findall(r"hint\s*:\s*[\"']([^\"']+)[\"']", self.raw)
        self.assertGreaterEqual(len(objectives), 4, "Every level must define a clear directive objective")
        self.assertGreaterEqual(len(hints), 4, "Every level must provide troubleshooting hints")


# ---------------------------------------------------------------------------
# Procedural Web Audio Verification Suite
# ---------------------------------------------------------------------------

class TestProceduralAudioEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = SRC_AUDIO.read_text(encoding="utf-8")

    def test_audio_file_exists(self):
        self.assertTrue(SRC_AUDIO.exists(), "src/audio.js must exist")

    def test_soundfx_class_present(self):
        self.assertRegex(self.raw, r"class\s+SoundFX", "SoundFX class must be declared")

    def test_audio_context_referenced(self):
        self.assertRegex(self.raw, r"AudioContext", "Web Audio API AudioContext must be referenced")

    def test_oscillator_and_gain_synthesis(self):
        self.assertIn("createOscillator", self.raw, "Zero-dependency procedural audio requires createOscillator")
        self.assertIn("createGain", self.raw, "Zero-dependency procedural audio requires createGain envelopes")

    def test_audio_feedback_methods(self):
        expected_methods = ["playClick", "playSnap", "playRayBounce", "playCrashBuzzer", "playVictory", "toggleMute"]
        for m in expected_methods:
            self.assertIn(m, self.raw, f"SoundFX must implement {m}() for responsive player feedback")

    def test_zero_external_audio_assets(self):
        # Must not load external mp3, ogg, or wav files
        external_files = re.findall(r"[\"'][^\"']+\.(?:mp3|ogg|wav)[\"']", self.raw, re.IGNORECASE)
        self.assertEqual(len(external_files), 0, f"Found external audio asset references: {external_files}")


# ---------------------------------------------------------------------------
# Particle System & Screen Shake Kinetics
# ---------------------------------------------------------------------------

class TestParticleSystemAndJuice(unittest.TestCase):
    def test_particle_burst_emission(self):
        ps = ParticleSystem()
        ps.emit(Vector2(100, 100), count=16, speed=150.0, color="#00f0ff")
        self.assertEqual(len(ps.particles), 16)

    def test_particles_decay_and_prune(self):
        ps = ParticleSystem()
        ps.emit(Vector2(50, 50), count=8, speed=100.0)
        ps.update(0.5)
        self.assertEqual(len(ps.particles), 8)
        ps.update(0.6)  # Exceeds lifetime (1.0s)
        self.assertEqual(len(ps.particles), 0)

    def test_screen_shake_decay(self):
        shake = ScreenShake()
        shake.trigger(15.0)
        self.assertEqual(shake.intensity, 15.0)
        shake.update(0.1)
        self.assertLess(shake.intensity, 15.0)
        shake.update(3.0)
        self.assertLessEqual(shake.intensity, 0.05)



if __name__ == "__main__":
    unittest.main()