import unittest
import json
import math
import time
import re
import os
import sys
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

# ---------------------------------------------------------------------------
# Minimal JavaScript-runtime shims so we can exercise JS logic from Python
# ---------------------------------------------------------------------------

class Vector2:
    """2-D vector matching the JS engine's Vec2 semantics."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    def add(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def sub(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def scale(self, s: float) -> "Vector2":
        return Vector2(self.x * s, self.y * s)

    def dot(self, other: "Vector2") -> float:
        return self.x * other.x + self.y * other.y

    def length(self) -> float:
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalize(self) -> "Vector2":
        mag = self.length()
        if mag == 0:
            return Vector2(0, 0)
        return Vector2(self.x / mag, self.y / mag)

    def lerp(self, other: "Vector2", t: float) -> "Vector2":
        return Vector2(
            self.x + (other.x - self.x) * t,
            self.y + (other.y - self.y) * t,
        )

    def reflect(self, normal: "Vector2") -> "Vector2":
        d = 2 * self.dot(normal)
        return Vector2(self.x - d * normal.x, self.y - d * normal.y)

    def distance_to(self, other: "Vector2") -> float:
        return self.sub(other).length()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return math.isclose(self.x, other.x, abs_tol=1e-9) and math.isclose(
            self.y, other.y, abs_tol=1e-9
        )

    def __repr__(self) -> str:
        return f"Vector2({self.x:.4f}, {self.y:.4f})"

# ---------------------------------------------------------------------------
# Physics / Engine shims (mirrors src/engine.js logic)
# ---------------------------------------------------------------------------

GRAVITY = 980.0          # px / s²
FRICTION = 0.85          # ground friction coefficient
AIR_RESISTANCE = 0.99    # per-frame air drag multiplier
MAX_VELOCITY = 1200.0    # px / s  (terminal velocity cap)
FIXED_TIMESTEP = 1 / 60  # seconds

@dataclass
class RigidBody:
    position: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    acceleration: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    mass: float = 1.0
    restitution: float = 0.6   # bounciness
    is_grounded: bool = False
    is_static: bool = False
    width: float = 32.0
    height: float = 32.0

    def apply_force(self, force: Vector2) -> None:
        if self.is_static:
            return
        ax = force.x / self.mass
        ay = force.y / self.mass
        self.acceleration = Vector2(
            self.acceleration.x + ax, self.acceleration.y + ay
        )

    def integrate(self, dt: float) -> None:
        """Semi-implicit Euler integration matching engine.js."""
        if self.is_static:
            return
        # Gravity
        gravity_force = Vector2(0, GRAVITY * self.mass)
        self.apply_force(gravity_force)

        # Velocity update
        self.velocity = Vector2(
            (self.velocity.x + self.acceleration.x * dt) * AIR_RESISTANCE,
            self.velocity.y + self.acceleration.y * dt,
        )

        # Terminal velocity clamp
        speed = self.velocity.length()
        if speed > MAX_VELOCITY:
            self.velocity = self.velocity.normalize().scale(MAX_VELOCITY)

        # Position update
        self.position = Vector2(
            self.position.x + self.velocity.x * dt,
            self.position.y + self.velocity.y * dt,
        )

        # Reset per-frame acceleration
        self.acceleration = Vector2(0, 0)

    def aabb(self) -> Tuple[float, float, float, float]:
        """Return (left, top, right, bottom)."""
        return (
            self.position.x,
            self.position.y,
            self.position.x + self.width,
            self.position.y + self.height,
        )

def aabb_overlap(a: RigidBody, b: RigidBody) -> bool:
    al, at, ar, ab = a.aabb()
    bl, bt, br, bb = b.aabb()
    return ar > bl and al < br and ab > bt and at < bb

def resolve_collision(a: RigidBody, b: RigidBody) -> Optional[Vector2]:
    """Returns MTV (minimum translation vector) or None if no overlap."""
    if not aabb_overlap(a, b):
        return None
    al, at, ar, ab = a.aabb()
    bl, bt, br, bb = b.aabb()

    overlap_x = min(ar, br) - max(al, bl)
    overlap_y = min(ab, bb) - max(at, bt)

    if overlap_x < overlap_y:
        mtv_x = overlap_x if a.position.x < b.position.x else -overlap_x
        return Vector2(mtv_x, 0)
    else:
        mtv_y = overlap_y if a.position.y < b.position.y else -overlap_y
        return Vector2(0, mtv_y)

# ---------------------------------------------------------------------------
# Particle system shim (mirrors engine.js ParticleSystem)
# ---------------------------------------------------------------------------

@dataclass
class Particle:
    position: Vector2
    velocity: Vector2
    life: float          # seconds remaining
    max_life: float
    size: float
    color: str
    alpha: float = 1.0

    @property
    def normalized_life(self) -> float:
        return self.life / self.max_life if self.max_life > 0 else 0

class ParticleSystem:
    def __init__(self, max_particles: int = 500):
        self.particles: List[Particle] = []
        self.max_particles = max_particles
        self.emit_count = 0

    def emit(
        self,
        origin: Vector2,
        count: int,
        speed_range: Tuple[float, float] = (50, 200),
        life_range: Tuple[float, float] = (0.3, 1.0),
        size_range: Tuple[float, float] = (2, 8),
        color: str = "#00ffff",
    ) -> int:
        import random
        spawned = 0
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(*speed_range)
            life = random.uniform(*life_range)
            size = random.uniform(*size_range)
            self.particles.append(
                Particle(
                    position=Vector2(origin.x, origin.y),
                    velocity=Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                    life=life,
                    max_life=life,
                    size=size,
                    color=color,
                )
            )
            spawned += 1
        self.emit_count += spawned
        return spawned

    def update(self, dt: float) -> None:
        alive = []
        for p in self.particles:
            p.life -= dt
            if p.life > 0:
                p.position = p.position.add(p.velocity.scale(dt))
                p.velocity = p.velocity.scale(0.95)  # drag
                p.alpha = p.normalized_life
                alive.append(p)
        self.particles = alive

    @property
    def active_count(self) -> int:
        return len(self.particles)

# ---------------------------------------------------------------------------
# Screen-shake shim
# ---------------------------------------------------------------------------

class ScreenShake:
    def __init__(self):
        self.trauma: float = 0.0   # 0..1
        self.decay: float = 1.5    # trauma/s
        self.max_offset: float = 30.0
        self.offset: Vector2 = Vector2(0, 0)

    def add_trauma(self, amount: float) -> None:
        self.trauma = min(1.0, self.trauma + amount)

    def update(self, dt: float) -> None:
        import random
        self.trauma = max(0.0, self.trauma - self.decay * dt)
        shake = self.trauma ** 2
        self.offset = Vector2(
            random.uniform(-1, 1) * self.max_offset * shake,
            random.uniform(-1, 1) * self.max_offset * shake,
        )

    @property
    def is_active(self) -> bool:
        return self.trauma > 0.001

# ---------------------------------------------------------------------------
# Level system shim (mirrors src/levels.js)
# ---------------------------------------------------------------------------

@dataclass
class Platform:
    x: float
    y: float
    width: float
    height: float = 16.0
    is_moving: bool = False
    move_range: float = 0.0
    move_speed: float = 0.0
    _phase: float = 0.0

    def update(self, dt: float) -> None:
        if self.is_moving:
            self._phase += self.move_speed * dt
            self.x += math.sin(self._phase) * self.move_range * dt

    def to_rigid_body(self) -> RigidBody:
        rb = RigidBody(
            position=Vector2(self.x, self.y),
            width=self.width,
            height=self.height,
            is_static=True,
        )
        return rb

@dataclass
class LevelConfig:
    level_id: int
    name: str
    platforms: List[Platform]
    spawn_point: Vector2
    exit_point: Vector2
    gravity_multiplier: float = 1.0
    time_limit: Optional[float] = None
    collectibles: int = 0
    enemy_count: int = 0
    background_color: str = "#0a0a1a"
    neon_accent: str = "#00ffff"

LEVEL_REGISTRY: Dict[int, LevelConfig] = {
    1: LevelConfig(
        level_id=1,
        name="Neon Descent",
        platforms=[
            Platform(0, 550, 800),
            Platform(100, 420, 200),
            Platform(400, 320, 150),
            Platform(600, 200, 120),
        ],
        spawn_point=Vector2(50, 480),
        exit_point=Vector2(660, 160),
        collectibles=5,
        enemy_count=2,
    ),
    2: LevelConfig(
        level_id=2,
        name="Kinetic Grid",
        platforms=[
            Platform(0, 550, 300),
            Platform(350, 450, 100, is_moving=True, move_range=80, move_speed=1.2),
            Platform(500, 350, 120),
            Platform(200, 250, 80, is_moving=True, move_range=60, move_speed=0.9),
            Platform(650, 150, 100),
        ],
        spawn_point=Vector2(30, 480),
        exit_point=Vector2(700, 110),
        gravity_multiplier=1.2,
        time_limit=90.0,
        collectibles=8,
        enemy_count=4,
    ),
    3: LevelConfig(
        level_id=3,
        name="Void Cascade",
        platforms=[
            Platform(0, 580, 150),
            Platform(200, 500, 80),
            Platform(350, 420, 60),
            Platform(480, 340, 80),
            Platform(600, 260, 100),
            Platform(700, 180, 80),
        ],
        spawn_point=Vector2(20, 520),
        exit_point=Vector2(740, 140),
        gravity_multiplier=0.8,
        time_limit=120.0,
        collectibles=12,
        enemy_count=6,
    ),
}

class LevelManager:
    def __init__(self):
        self.current_level: Optional[LevelConfig] = None
        self.current_level_id: int = 0
        self.score: int = 0
        self.lives: int = 3
        self.collectibles_gathered: int = 0
        self.elapsed_time: float = 0.0
        self.level_complete: bool = False
        self.on_level_complete_callbacks: List[Any] = []

    def load_level(self, level_id: int) -> bool:
        if level_id not in LEVEL_REGISTRY:
            return False
        self.current_level = LEVEL_REGISTRY[level_id]
        self.current_level_id = level_id
        self.collectibles_gathered = 0
        self.elapsed_time = 0.0
        self.level_complete = False
        return True

    def update(self, dt: float) -> None:
        if self.current_level is None:
            return
        self.elapsed_time += dt
        for platform in self.current_level.platforms:
            platform.update(dt)

    def collect_item(self) -> int:
        self.collectibles_gathered += 1
        points = 100 * self.current_level_id
        self.score += points
        return points

    def check_exit(self, player_pos: Vector2) -> bool:
        if self.current_level is None:
            return False
        exit_pos = self.current_level.exit_point
        dist = player_pos.distance_to(exit_pos)
        if dist < 40:
            self.level_complete = True
            for cb in self.on_level_complete_callbacks:
                cb(self.current_level_id)
            return True
        return False

    def is_time_expired(self) -> bool:
        if self.current_level and self.current_level.time_limit:
            return self.elapsed_time >= self.current_level.time_limit
        return False

    def next_level(self) -> bool:
        return self.load_level(self.current_level_id + 1)

# ---------------------------------------------------------------------------
# Audio engine shim (mirrors src/audio.js)
# ---------------------------------------------------------------------------

@dataclass
class OscillatorConfig:
    type: str          # sine | square | sawtooth | triangle
    frequency: float   # Hz
    detune: float = 0.0

@dataclass
class EnvelopeConfig:
    attack: float   # seconds
    decay: float
    sustain: float  # 0..1 gain
    release: float

@dataclass
class AudioEvent:
    name: str
    timestamp: float
    frequency: float
    duration: float
    oscillator_type: str
    gain_peak: float

class ProceduralAudioEngine:
    """Python shim mirroring src/audio.js Web Audio API synthesis."""

    SOUND_PRESETS: Dict[str, Dict] = {
        "jump": {
            "osc": OscillatorConfig("square", 220, 0),
            "env": EnvelopeConfig(0.01, 0.1, 0.0, 0.05),
            "freq_sweep": (220, 440),
            "gain_peak": 0.4,
        },
        "land": {
            "osc": OscillatorConfig("sine", 80, 0),
            "env": EnvelopeConfig(0.005, 0.15, 0.0, 0.05),
            "freq_sweep": (80, 40),
            "gain_peak": 0.6,
        },
        "collect": {
            "osc": OscillatorConfig("sine", 880, 0),
            "env": EnvelopeConfig(0.01, 0.05, 0.3, 0.1),
            "freq_sweep": (880, 1320),
            "gain_peak": 0.5,
        },
        "impact": {
            "osc": OscillatorConfig("sawtooth", 60, 0),
            "env": EnvelopeConfig(0.001, 0.2, 0.0, 0.1),
            "freq_sweep": (60, 30),
            "gain_peak": 0.8,
        },
        "level_complete": {
            "osc": OscillatorConfig("sine", 523, 0),
            "env": EnvelopeConfig(0.05, 0.1, 0.7, 0.5),
            "freq_sweep": (523, 1046),
            "gain_peak": 0.7,
        },
        "death": {
            "osc": OscillatorConfig("sawtooth", 440, 0),
            "env": EnvelopeConfig(0.01, 0.3, 0.0, 0.2),
            "freq_sweep": (440, 55),
            "gain_peak": 0.9,
        },
        "menu_blip": {
            "osc": OscillatorConfig("square", 660, 0),
            "env": EnvelopeConfig(0.005, 0.05, 0.0, 0.02),
            "freq_sweep": (660, 660),
            "gain_peak": 0.3,
        },
    }

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self.master_gain: float = 0.8
        self.muted: bool = False
        self.event_log: List[AudioEvent] = []
        self._clock: float = 0.0
        self._enabled: bool = True

    def _current_time(self) -> float:
        return self._clock

    def advance_clock(self, dt: float) -> None:
        self._clock += dt

    def play(self, sound_name: str) -> Optional[AudioEvent]:
        if self.muted or not self._enabled:
            return None
        if sound_name not in self.SOUND_PRESETS:
            return None
        preset = self.SOUND_PRESETS[sound_name]
        osc: OscillatorConfig = preset["osc"]
        env: EnvelopeConfig = preset["env"]
        freq_start, freq_end = preset["freq_sweep"]
        duration = env.attack + env.decay + env.release
        event = AudioEvent(
            name=sound_name,
            timestamp=self._current_time(),
            frequency=freq_start,
            duration=duration,
            oscillator_type=osc.type,
            gain_peak=preset["gain_peak"] * self.master_gain,
        )
        self.event_log.append(event)
        return event

    def generate_samples(self, sound_name: str, num_samples: int) -> List[float]:
        """Synthesise PCM samples for a given sound preset."""
        if sound_name not in self.SOUND_PRESETS:
            return []
        preset = self.SOUND_PRESETS[sound_name]
        osc: OscillatorConfig = preset["osc"]
        env: EnvelopeConfig = preset["env"]
        freq_start, freq_end = preset["freq_sweep"]
        gain_peak: float = preset["gain_peak"]

        total_duration = env.attack + env.decay + env.release
        samples = []
        for i in range(num_samples):
            t = i / self.sample_rate
            if t > total_duration:
                break
            # Frequency sweep (linear)
            freq = freq_start + (freq_end - freq_start) * (t / total_duration)
            # Oscillator
            phase = 2 * math.pi * freq * t
            if osc.type == "sine":
                raw = math.sin(phase)
            elif osc.type == "square":
                raw = 1.0 if math.sin(phase) >= 0 else -1.0
            elif osc.type == "sawtooth":
                raw = 2 * ((freq * t) % 1.0) - 1.0
            elif osc.type == "triangle":
                raw = 2 * abs(2 * ((freq * t) % 1.0) - 1.0) - 1.0
            else:
                raw = 0.0
            # ADSR envelope
            if t < env.attack:
                gain = (t / env.attack) * gain_peak
            elif t < env.attack + env.decay:
                decay_t = (t - env.attack) / env.decay
                gain = gain_peak - (gain_peak - env.sustain * gain_peak) * decay_t
            elif t < total_duration - env.release:
                gain = env.sustain * gain_peak
            else:
                release_t = (t - (total_duration - env.release)) / env.release
                gain = env.sustain * gain_peak * (1 - release_t)
            samples.append(raw * gain * self.master_gain)
        return samples

    def set_master_gain(self, gain: float) -> None:
        self.master_gain = max(0.0, min(1.0, gain))

    def mute(self) -> None:
        self.muted = True

    def unmute(self) -> None:
        self.muted = False

    def clear_log(self) -> None:
        self.event_log.clear()

    def events_since(self, timestamp: float) -> List[AudioEvent]:
        return [e for e in self.event_log if e.timestamp >= timestamp]

# ---------------------------------------------------------------------------
# Game loop shim
# ---------------------------------------------------------------------------

class GameLoop:
    """Deterministic fixed-timestep game loop for testing."""

    def __init__(self, target_fps: int = 60):
        self.target_fps = target_fps
        self.fixed_dt = 1.0 / target_fps
        self.frame_count: int = 0
        self.total_time: float = 0.0
        self.update_times: List[float] = []
        self.render_times: List[float] = []
        self._running: bool = False
        self.on_update = None
        self.on_render = None

    def run_frames(self, n: int) -> None:
        for _ in range(n):
            t0 = time.perf_counter()
            if self.on_update:
                self.on_update(self.fixed_dt)
            t1 = time.perf_counter()
            if self.on_render:
                self.on_render()
            t2 = time.perf_counter()
            self.update_times.append(t1 - t0)
            self.render_times.append(t2 - t1)
            self.frame_count += 1
            self.total_time += self.fixed_dt

    @property
    def average_update_ms(self) -> float:
        if not self.update_times:
            return 0.0
        return (sum(self.update_times) / len(self.update_times)) * 1000

    @property
    def average_render_ms(self) -> float:
        if not self.render_times:
            return 0.0
        return (sum(self.render_times) / len(self.render_times)) * 1000

# ===========================================================================
# TEST SUITES
# ===========================================================================

class TestVector2(unittest.TestCase):
    """Unit tests for 2-D vector math used throughout the engine."""

    def test_add(self):
        a = Vector2(1, 2)
        b = Vector2(3, 4)
        result = a.add(b)
        self.assertAlmostEqual(result.x, 4)
        self.assertAlmostEqual(result.y, 6)

    def test_sub(self):
        a = Vector2(5, 7)
        b = Vector2(2, 3)
        result = a.sub(b)
        self.assertAlmostEqual(result.x, 3)
        self.assertAlmostEqual(result.y, 4)

    def test_scale(self):
        v = Vector2(3, 4)
        result = v.scale(2)
        self.assertAlmostEqual(result.x, 6)
        self.assertAlmostEqual(result.y, 8)

    def test_length(self):
        v = Vector2(3, 4)
        self.assertAlmostEqual(v.length(), 5.0)

    def test_normalize(self):
        v = Vector2(3, 4)
        n = v.normalize()
        self.assertAlmostEqual(n.length(), 1.0, places=9)
        self.assertAlmostEqual(n.x, 0.6)
        self.assertAlmostEqual(n.y, 0.8)

    def test_normalize_zero_vector(self):
        v = Vector2(0, 0)
        n = v.normalize()
        self.assertAlmostEqual(n.x, 0)
        self.assertAlmostEqual(n.y, 0)

    def test_dot_product(self):
        a = Vector2(1, 0)
        b = Vector2(0, 1)
        self.assertAlmostEqual(a.dot(b), 0.0)
        c = Vector2(1, 0)
        self.assertAlmostEqual(a.dot(c), 1.0)

    def test_lerp_at_zero(self):
        a = Vector2(0, 0)
        b = Vector2(10, 20)
        result = a.lerp(b, 0.0)
        self.assertEqual(result, a)

    def test_lerp_at_one(self):
        a = Vector2(0, 0)
        b = Vector2(10, 20)
        result = a.lerp(b, 1.0)
        self.assertEqual(result, b)

    def test_lerp_midpoint(self):
        a = Vector2(0, 0)
        b = Vector2(10, 20)
        result = a.lerp(b, 0.5)
        self.assertAlmostEqual(result.x, 5.0)
        self.assertAlmostEqual(result.y, 10.0)

    def test_reflect_off_floor(self):
        velocity = Vector2(0, 5)   # moving down
        normal = Vector2(0, -1)    # floor normal points up
        reflected = velocity.reflect(normal)
        self.assertAlmostEqual(reflected.x, 0)
        self.assertAlmostEqual(reflected.y, -5)

    def test_reflect_off_wall(self):
        velocity = Vector2(-3, 0)
        normal = Vector2(1, 0)
        reflected = velocity.reflect(normal)
        self.assertAlmostEqual(reflected.x, 3)
        self.assertAlmostEqual(reflected.y, 0)

    def test_distance_to(self):
        a = Vector2(0, 0)
        b = Vector2(3, 4)
        self.assertAlmostEqual(a.distance_to(b), 5.0)

    def test_equality(self):
        a = Vector2(1.0, 2.0)
        b = Vector2(1.0, 2.0)
        self.assertEqual(a, b)

    def test_inequality(self):
        a = Vector2(1.0, 2.0)
        b = Vector2(1.0, 2.1)
        self.assertNotEqual(a, b)

class TestRigidBodyPhysics(unittest.TestCase):
    """Tests for the RigidBody integration and force application."""

    def _make_body(self, **kwargs) -> RigidBody:
        return RigidBody(**kwargs)

    def test_gravity_accelerates_body_downward(self):
        body = self._make_body(position=Vector2(0, 0))
        body.integrate(FIXED_TIMESTEP)
        self.assertGreater(body.velocity.y, 0, "Gravity should pull body downward")

    def test_static_body_unaffected_by_gravity(self):
        body = self._make_body(position=Vector2(0, 0), is_static=True)
        body.integrate(FIXED_TIMESTEP)
        self.assertAlmostEqual(body.velocity.y, 0)
        self.assertAlmostEqual(body.position.y, 0)

    def test_apply_force_changes_acceleration(self):
        body = self._make_body(mass=2.0)
        force = Vector2(20, 0)
        body.apply_force(force)
        self.assertAlmostEqual(body.acceleration.x, 10.0)  # F/m = 20/2

    def test_apply_force_static_body_no_effect(self):
        body = self._make_body(is_static=True)
        body.apply_force(Vector2(1000, 1000))
        self.assertAlmostEqual(body.acceleration.x, 0)
        self.assertAlmostEqual(body.acceleration.y, 0)

    def test_terminal_velocity_capped(self):
        body = self._make_body(position=Vector2(0, 0))
        # Simulate many frames of free fall
        for _ in range(600):
            body.integrate(FIXED_TIMESTEP)
        speed = body.velocity.length()
        self.assertLessEqual(speed, MAX_VELOCITY + 1e-6)

    def test_position_updates_with_velocity(self):
        body = self._make_body(
            position=Vector2(0, 0),
            velocity=Vector2(100, 0),
            is_static=False,
        )
        # Override gravity by making it static temporarily — use a trick:
        # We'll just check that x moves in the right direction
        body.integrate(FIXED_TIMESTEP)
        self.assertGreater(body.position.x, 0)

    def test_air_resistance_reduces_horizontal_velocity(self):
        body = self._make_body(velocity=Vector2(500, 0))
        initial_vx = body.velocity.x
        body.integrate(FIXED_TIMESTEP)
        self.assertLess(body.velocity.x, initial_vx)

    def test_acceleration_reset_after_integrate(self):
        body = self._make_body()
        body.apply_force(Vector2(100, 0))
        body.integrate(FIXED_TIMESTEP)
        self.assertAlmostEqual(body.acceleration.x, 0)
        self.assertAlmostEqual(body.acceleration.y, 0)

    def test_aabb_correct(self):
        body = self._make_body(
            position=Vector2(10, 20), width=50, height=30
        )
        l, t, r, b = body.aabb()
        self.assertEqual(l, 10)
        self.assertEqual(t, 20)
        self.assertEqual(r, 60)
        self.assertEqual(b, 50)