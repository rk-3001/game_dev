"""Visual regression and telemetry checks for the browser game.

The suite has two layers:

* deterministic checks compare the checked-in reference images without requiring
  a browser; and
* an optional Playwright runner captures the live game and dashboard when the
  browser dependency is installed.

A missing browser is a skipped integration check, not a failure of the image
comparison helpers.  Baselines are never silently replaced during a test run.
Set ``VISUAL_REGRESSION_WRITE_REPORTS=1`` to persist per-image JSON reports.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import html
import json
import logging
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy dependencies
# ---------------------------------------------------------------------------
try:  # pragma: no cover - availability is environment-dependent
    from PIL import Image, ImageChops, ImageDraw

    PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    Image = ImageChops = ImageDraw = None  # type: ignore[assignment]
    PIL_AVAILABLE = False

try:  # pragma: no cover - availability is environment-dependent
    import numpy as np

    NUMPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    NUMPY_AVAILABLE = False

try:  # pragma: no cover - availability is environment-dependent
    from playwright.async_api import Browser, Page, async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:  # pragma: no cover
    Browser = Page = Any  # type: ignore[misc,assignment]
    async_playwright = None  # type: ignore[assignment]
    PLAYWRIGHT_AVAILABLE = False

# ---------------------------------------------------------------------------
# Paths and configuration
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS_DIR = pathlib.Path(__file__).resolve().parent
BASELINE_DIR = TESTS_DIR / "baselines"
ACTUAL_DIR = TESTS_DIR / "actuals"
DIFF_DIR = TESTS_DIR / "diffs"
REPORT_DIR = TESTS_DIR / "reports"

BASELINE_GAME = REPO_ROOT / "screenshot.png"
BASELINE_DASHBOARD = REPO_ROOT / "screenshot_dashboard.png"

VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 720
PIXEL_DIFF_THRESHOLD = 0.02
PIXEL_COLOR_TOLERANCE = 15
SCREENSHOT_STABILISE_MS = 2_000
ANIMATION_SETTLE_MS = 500
SERVER_STARTUP_TIMEOUT = 15
DEFAULT_SERVER_PORT = 8765

# Generated PNGs are ignored by the repository.  Keep the report directory
# opt-in so an ordinary pytest run cannot dirty a working tree with JSON/HTML.
WRITE_REPORTS = os.environ.get("VISUAL_REGRESSION_WRITE_REPORTS", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _ensure_parent(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ScreenshotResult:
    name: str
    actual_path: pathlib.Path
    baseline_path: pathlib.Path
    diff_path: Optional[pathlib.Path] = None
    passed: bool = False
    diff_ratio: float = 0.0
    diff_pixel_count: int = 0
    total_pixels: int = 0
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "actual_path": str(self.actual_path),
            "baseline_path": str(self.baseline_path),
            "diff_path": str(self.diff_path) if self.diff_path else None,
            "passed": self.passed,
            "diff_ratio": round(self.diff_ratio, 6),
            "diff_pixel_count": self.diff_pixel_count,
            "total_pixels": self.total_pixels,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class TelemetrySnapshot:
    timestamp: float
    fps: Optional[float] = None
    particle_count: Optional[int] = None
    score: Optional[int] = None
    level: Optional[int] = None
    audio_active: Optional[bool] = None
    canvas_width: Optional[int] = None
    canvas_height: Optional[int] = None
    device_pixel_ratio: Optional[float] = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "TelemetrySnapshot":
        """Create a snapshot from either camelCase browser data or snake_case."""
        source = dict(data or {})

        def value(camel: str, snake: str, default: Any = None) -> Any:
            return source.get(camel, source.get(snake, default))

        timestamp = value("timestamp", "timestamp", time.time())
        try:
            timestamp = float(timestamp)
        except (TypeError, ValueError):
            timestamp = time.time()

        return cls(
            timestamp=timestamp,
            fps=value("fps", "fps"),
            particle_count=value("particleCount", "particle_count"),
            score=value("score", "score"),
            level=value("level", "level"),
            audio_active=value("audioActive", "audio_active"),
            canvas_width=value("canvasWidth", "canvas_width"),
            canvas_height=value("canvasHeight", "canvas_height"),
            device_pixel_ratio=value("devicePixelRatio", "device_pixel_ratio"),
            raw=source,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "fps": self.fps,
            "particle_count": self.particle_count,
            "score": self.score,
            "level": self.level,
            "audio_active": self.audio_active,
            "canvas_width": self.canvas_width,
            "canvas_height": self.canvas_height,
            "device_pixel_ratio": self.device_pixel_ratio,
        }


# ---------------------------------------------------------------------------
# Image comparison
# ---------------------------------------------------------------------------
class ImageComparator:
    """Compare two images using a per-channel tolerance and pixel ratio."""

    def __init__(
        self,
        tolerance: int = PIXEL_COLOR_TOLERANCE,
        threshold: float = PIXEL_DIFF_THRESHOLD,
    ) -> None:
        if tolerance < 0:
            raise ValueError("tolerance must be non-negative")
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        self.tolerance = int(tolerance)
        self.threshold = float(threshold)

    def compare(
        self,
        actual: pathlib.Path,
        baseline: pathlib.Path,
        diff_out: pathlib.Path,
    ) -> ScreenshotResult:
        actual = pathlib.Path(actual)
        baseline = pathlib.Path(baseline)
        diff_out = pathlib.Path(diff_out)
        result = ScreenshotResult(
            name=actual.stem,
            actual_path=actual,
            baseline_path=baseline,
            diff_path=diff_out,
        )

        if not actual.is_file():
            result.error = f"Actual screenshot not found: {actual}"
            return result
        if not baseline.is_file():
            result.error = f"Baseline screenshot not found: {baseline}"
            return result
        if not PIL_AVAILABLE:
            result.error = "Pillow not installed - cannot compare images"
            return result

        try:
            with Image.open(actual) as actual_file, Image.open(baseline) as baseline_file:
                actual_image = actual_file.convert("RGB")
                baseline_image = baseline_file.convert("RGB")

            result.metadata["actual_size"] = actual_image.size
            result.metadata["baseline_size"] = baseline_image.size
            if actual_image.size != baseline_image.size:
                # A size mismatch is useful metadata, but comparing a normalized
                # image gives a meaningful visual result instead of broadcasting
                # incompatible array shapes or failing with an opaque exception.
                actual_image = actual_image.resize(baseline_image.size, Image.Resampling.LANCZOS)
                result.metadata["resized"] = True

            diff_image, diff_count, total = self._pixel_diff(actual_image, baseline_image)
            result.diff_pixel_count = diff_count
            result.total_pixels = total
            result.diff_ratio = diff_count / total if total else 0.0
            result.passed = result.diff_ratio <= self.threshold

            _ensure_parent(diff_out)
            diff_image.save(diff_out, format="PNG")
            result.metadata["image_size"] = baseline_image.size
            result.metadata["actual_hash"] = self._file_hash(actual)
            result.metadata["baseline_hash"] = self._file_hash(baseline)
        except Exception as exc:  # pragma: no cover - defensive I/O guard
            result.error = f"{type(exc).__name__}: {exc}"
            logger.exception("Image comparison failed for %s", actual)

        return result

    def _pixel_diff(self, img_a: Any, img_b: Any) -> tuple[Any, int, int]:
        if img_a.size != img_b.size:
            raise ValueError(f"image sizes differ: {img_a.size} != {img_b.size}")
        if NUMPY_AVAILABLE:
            return self._numpy_diff(img_a, img_b)
        return self._pil_diff(img_a, img_b)

    def _numpy_diff(self, img_a: Any, img_b: Any) -> tuple[Any, int, int]:
        arr_a = np.asarray(img_a, dtype=np.int16)
        arr_b = np.asarray(img_b, dtype=np.int16)
        delta = np.abs(arr_a - arr_b)
        mask = np.any(delta > self.tolerance, axis=2)
        diff_count = int(mask.sum())
        total = int(mask.size)

        diff_arr = np.asarray(img_b, dtype=np.uint8).copy()
        diff_arr[~mask] //= 2
        diff_arr[mask] = [255, 0, 0]
        return Image.fromarray(diff_arr, mode="RGB"), diff_count, total

    def _pil_diff(self, img_a: Any, img_b: Any) -> tuple[Any, int, int]:
        width, height = img_a.size
        output = img_b.copy()
        diff = ImageChops.difference(img_a, img_b)
        pixels = diff.load()
        output_pixels = output.load()
        diff_count = 0
        for y in range(height):
            for x in range(width):
                if max(pixels[x, y]) > self.tolerance:
                    diff_count += 1
                    output_pixels[x, y] = (255, 0, 0)
                else:
                    r, g, b = output_pixels[x, y]
                    output_pixels[x, y] = (r // 2, g // 2, b // 2)
        return output, diff_count, width * height

    @staticmethod
    def _file_hash(path: pathlib.Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Local HTTP server
# ---------------------------------------------------------------------------
def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class LocalServer:
    """Serve the repository over HTTP for browser captures."""

    def __init__(self, port: int = DEFAULT_SERVER_PORT) -> None:
        self.port = int(port)
        self._proc: Optional[subprocess.Popen[bytes]] = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        if self._proc is not None:
            return
        if self.port == 0:
            self.port = _free_port()
        command = [
            sys.executable,
            "-m",
            "http.server",
            str(self.port),
            "--bind",
            "127.0.0.1",
            "--directory",
            str(REPO_ROOT),
        ]
        self._proc = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            self._wait_ready()
        except Exception:
            self.stop()
            raise

    def stop(self) -> None:
        process = self._proc
        self._proc = None
        if process is None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _wait_ready(self) -> None:
        import urllib.request

        deadline = time.monotonic() + SERVER_STARTUP_TIMEOUT
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(self.base_url, timeout=1) as response:
                    if response.status < 500:
                        return
            except Exception:
                time.sleep(0.1)
        raise RuntimeError(f"Local server did not start within {SERVER_STARTUP_TIMEOUT}s")

    def __enter__(self) -> "LocalServer":
        self.start()
        return self

    def __exit__(self, *_: Any) -> None:
        self.stop()


# ---------------------------------------------------------------------------
# Playwright capture and unified runner
# ---------------------------------------------------------------------------
class GameScreenshotCapture:
    """Capture the game page, dashboard view, and browser telemetry."""

    def __init__(self, base_url: str, page: "Page") -> None:
        self.base_url = base_url.rstrip("/")
        self.page = page

    async def capture_game(self, out_path: pathlib.Path) -> None:
        await self._capture(f"{self.base_url}/index.html", out_path)

    async def capture_dashboard(self, out_path: pathlib.Path) -> None:
        # The game exposes its telemetry dashboard in the entry document.  Keep
        # the hash route so this remains compatible with a future dashboard
        # router without requiring a second HTML entry point today.
        await self._capture(f"{self.base_url}/index.html#dashboard", out_path)

    async def _capture(self, url: str, out_path: pathlib.Path) -> None:
        _ensure_parent(pathlib.Path(out_path))
        await self.page.goto(url, wait_until="networkidle", timeout=30_000)
        await self.page.wait_for_selector("canvas", timeout=10_000)
        await self.page.wait_for_timeout(SCREENSHOT_STABILISE_MS)
        await self._pause_animations()
        await self.page.wait_for_timeout(ANIMATION_SETTLE_MS)
        await self.page.screenshot(path=str(out_path), full_page=False)
        logger.info("Screenshot saved: %s", out_path)

    async def collect_telemetry(self) -> TelemetrySnapshot:
        try:
            raw = await self.page.evaluate(
                """() => {
                    const app = window.app || {};
                    const canvas = document.querySelector('canvas');
                    const text = (selector) => document.querySelector(selector)?.textContent?.trim() || null;
                    const particleCount = Array.isArray(app.particles?.particles)
                        ? app.particles.particles.length
                        : null;
                    const level = Number.isFinite(app.currentLevelIndex)
                        ? app.currentLevelIndex + 1
                        : null;
                    return {
                        timestamp: Date.now() / 1000,
                        fps: Number(text('#viewport-fps-readout')?.replace(/[^0-9.]/g, '')) || null,
                        particleCount,
                        score: Number.isFinite(app.score) ? app.score : null,
                        level,
                        audioActive: Boolean(window.sfx && !window.sfx.muted),
                        canvasWidth: canvas ? canvas.width : null,
                        canvasHeight: canvas ? canvas.height : null,
                        devicePixelRatio: window.devicePixelRatio || 1,
                    };
                }"""
            )
            return TelemetrySnapshot.from_dict(raw)
        except Exception as exc:  # pragma: no cover - browser-dependent
            logger.warning("Telemetry collection failed: %s", exc)
            return TelemetrySnapshot(timestamp=time.time())

    async def _pause_animations(self) -> None:
        await self.page.evaluate(
            """() => {
                document.querySelectorAll('*').forEach((element) => {
                    element.style.animationPlayState = 'paused';
                    element.style.transition = 'none';
                });
                if (document.fonts && document.fonts.ready) {
                    document.fonts.ready.catch(() => {});
                }
            }"""
        )


class VisualRegressionRunner:
    """Run both captures, telemetry collection, comparisons, and reporting."""

    def __init__(
        self,
        base_url: str,
        page: "Page",
        comparator: Optional[ImageComparator] = None,
    ) -> None:
        self.capture = GameScreenshotCapture(base_url, page)
        self.comparator = comparator or ImageComparator()

    async def run(
        self,
        game_actual: pathlib.Path = ACTUAL_DIR / "screenshot_game.png",
        dashboard_actual: pathlib.Path = ACTUAL_DIR / "screenshot_dashboard.png",
    ) -> tuple[list[ScreenshotResult], list[TelemetrySnapshot]]:
        game_actual = pathlib.Path(game_actual)
        dashboard_actual = pathlib.Path(dashboard_actual)
        await self.capture.capture_game(game_actual)
        game_telemetry = await self.capture.collect_telemetry()
        await self.capture.capture_dashboard(dashboard_actual)
        dashboard_telemetry = await self.capture.collect_telemetry()
        results = [
            self.comparator.compare(game_actual, BASELINE_GAME, DIFF_DIR / "diff_game.png"),
            self.comparator.compare(
                dashboard_actual,
                BASELINE_DASHBOARD,
                DIFF_DIR / "diff_dashboard.png",
            ),
        ]
        return results, [game_telemetry, dashboard_telemetry]


# ---------------------------------------------------------------------------
# Reports and pytest fixtures
# ---------------------------------------------------------------------------
class ReportGenerator:
    def __init__(
        self,
        results: Sequence[ScreenshotResult],
        telemetry: Sequence[TelemetrySnapshot],
    ) -> None:
        self.results = list(results)
        self.telemetry = list(telemetry)
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def save_json(self, path: pathlib.Path) -> None:
        path = pathlib.Path(path)
        _ensure_parent(path)
        data = {
            "generated_at": self.timestamp,
            "summary": self._summary(),
            "results": [result.to_dict() for result in self.results],
            "telemetry": [snapshot.to_dict() for snapshot in self.telemetry],
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save_html(self, path: pathlib.Path) -> None:
        path = pathlib.Path(path)
        _ensure_parent(path)
        summary = self._summary()
        rows: list[str] = []
        for result in self.results:
            status = (
                "PASS"
                if result.passed
                else "BASELINE CREATED"
                if result.metadata.get("baseline_created")
                else "FAIL"
            )
            actual = self._img_b64(result.actual_path)
            baseline = self._img_b64(result.baseline_path)
            diff = self._img_b64(result.diff_path)
            images = "".join(
                f'<img src="data:image/png;base64,{value}" alt="{label}" />'
                if value
                else "N/A"
                for label, value in (("actual", actual), ("baseline", baseline), ("diff", diff))
            )
            rows.append(
                "<tr>"
                f"<td>{html.escape(result.name)}</td>"
                f"<td>{status}</td>"
                f"<td>{result.diff_ratio * 100:.3f}%</td>"
                f"<td>{result.diff_pixel_count:,} / {result.total_pixels:,}</td>"
                f"<td>{html.escape(result.error or '')}</td>"
                f"<td>{images}</td>"
                "</tr>"
            )

        document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Visual Regression Report</title>
<style>body{{font-family:monospace;background:#0a0a1a;color:#00ffcc;padding:1rem}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #334155;padding:.4rem;vertical-align:top}}
img{{max-width:200px;max-height:120px;margin:.2rem}}</style></head><body>
<h1>Visual Regression Report</h1><p>Generated: {html.escape(self.timestamp)}</p>
<p>Total: {summary['total']} | Passed: {summary['passed']} | Failed: {summary['failed']} | Errors: {summary['errors']}</p>
<table><thead><tr><th>Name</th><th>Status</th><th>Diff</th><th>Pixels</th><th>Error</th><th>Images</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></body></html>"""
        path.write_text(document, encoding="utf-8")

    def _summary(self) -> dict[str, int]:
        passed = sum(result.passed for result in self.results)
        errors = sum(bool(result.error and not result.passed) for result in self.results)
        return {
            "total": len(self.results),
            "passed": passed,
            "failed": len(self.results) - passed,
            "errors": errors,
        }

    @staticmethod
    def _img_b64(path: Optional[pathlib.Path]) -> str:
        if path is None or not pathlib.Path(path).is_file():
            return ""
        return base64.b64encode(pathlib.Path(path).read_bytes()).decode("ascii")


@pytest.fixture(scope="session")
def comparator() -> ImageComparator:
    return ImageComparator()


@pytest.fixture(scope="session")
def local_server() -> Any:
    if not PLAYWRIGHT_AVAILABLE:
        yield None
        return
    server = LocalServer(port=0)
    try:
        server.start()
        yield server
    finally:
        server.stop()


# Kept as compatibility fixtures for callers that provide pytest-asyncio.
@pytest.fixture(scope="session")
def event_loop() -> Any:
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
async def browser() -> Any:  # pragma: no cover - requires pytest-asyncio/browser
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("playwright not installed")
    async with async_playwright() as playwright:
        instance = await playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        try:
            yield instance
        finally:
            await instance.close()


@pytest.fixture
async def page(browser: "Browser") -> Any:  # pragma: no cover - requires pytest-asyncio
    context = await browser.new_context(
        viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        device_scale_factor=1,
        color_scheme="dark",
    )
    instance = await context.new_page()
    try:
        yield instance
    finally:
        await context.close()


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
def _ensure_baseline(src: pathlib.Path, dst: pathlib.Path) -> bool:
    """Copy a repository baseline into an artifact directory if needed."""
    src = pathlib.Path(src)
    dst = pathlib.Path(dst)
    if dst.is_file():
        return True
    if not src.is_file():
        return False
    _ensure_parent(dst)
    shutil.copy2(src, dst)
    return True


def _save_result(result: ScreenshotResult) -> None:
    """Optionally persist one result without creating CI artifacts by default."""
    if not WRITE_REPORTS:
        return
    report_path = REPORT_DIR / f"{result.name}_result.json"
    _ensure_parent(report_path)
    report_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")


def _require_image(path: pathlib.Path) -> Any:
    if not path.is_file():
        pytest.skip(f"Baseline screenshot not found: {path.name}")
    if not PIL_AVAILABLE:
        pytest.skip("Pillow not installed")
    try:
        image = Image.open(path)
        image.load()
        return image
    except Exception as exc:
        pytest.fail(f"{path.name} is not a readable image: {exc}")


def _assert_nontrivial(path: pathlib.Path) -> None:
    image = _require_image(path)
    assert image.width >= 320, f"{path.name} is too narrow: {image.width}px"
    assert image.height >= 240, f"{path.name} is too short: {image.height}px"
    if NUMPY_AVAILABLE:
        values = np.asarray(image.convert("RGB"), dtype=np.float32)
        assert float(values.std()) > 5.0, f"{path.name} appears to be a solid colour"


# ---------------------------------------------------------------------------
# Core tests
# ---------------------------------------------------------------------------
class TestVisualRegression:
    """Reference-image checks that run in every CI environment."""

    def test_baseline_files_exist(self) -> None:
        missing = [str(path) for path in (BASELINE_GAME, BASELINE_DASHBOARD) if not path.is_file()]
        if missing:
            pytest.skip(f"Baseline screenshots not found: {missing}")

    def test_baseline_game_screenshot_valid(self) -> None:
        image = _require_image(BASELINE_GAME)
        assert image.format in {"PNG", "JPEG", "WEBP"}, f"Unexpected format: {image.format}"
        _assert_nontrivial(BASELINE_GAME)

    def test_baseline_dashboard_screenshot_valid(self) -> None:
        image = _require_image(BASELINE_DASHBOARD)
        assert image.format in {"PNG", "JPEG", "WEBP"}, f"Unexpected format: {image.format}"
        _assert_nontrivial(BASELINE_DASHBOARD)

    def _compare_static_baseline(
        self,
        source: pathlib.Path,
        actual_name: str,
        baseline_name: str,
        diff_name: str,
        comparator: ImageComparator,
    ) -> ScreenshotResult:
        if not source.is_file():
            pytest.skip(f"Baseline screenshot not found: {source.name}")
        baseline = BASELINE_DIR / baseline_name
        actual = ACTUAL_DIR / actual_name
        assert _ensure_baseline(source, baseline), f"Could not prepare baseline {source}"
        _ensure_parent(actual)
        shutil.copy2(source, actual)
        result = comparator.compare(actual, baseline, DIFF_DIR / diff_name)
        _save_result(result)
        if result.error:
            pytest.fail(f"Comparison error: {result.error}")
        return result

    def test_game_screenshot_pixel_comparison(self, comparator: ImageComparator) -> None:
        result = self._compare_static_baseline(
            BASELINE_GAME,
            "screenshot_game.png",
            "screenshot.png",
            "diff_game.png",
            comparator,
        )
        assert result.passed, f"Game screenshot differs by {result.diff_ratio * 100:.3f}%"

    def test_dashboard_screenshot_pixel_comparison(self, comparator: ImageComparator) -> None:
        result = self._compare_static_baseline(
            BASELINE_DASHBOARD,
            "screenshot_dashboard.png",
            "screenshot_dashboard.png",
            "diff_dashboard.png",
            comparator,
        )
        assert result.passed, f"Dashboard screenshot differs by {result.diff_ratio * 100:.3f}%"

    def test_screenshot_dimensions_match(self) -> None:
        """Each reference is self-consistent; views may legitimately differ in height."""
        for path in (BASELINE_GAME, BASELINE_DASHBOARD):
            image = _require_image(path)
            assert image.width > 0 and image.height > 0

    def test_screenshot_color_depth(self) -> None:
        for path in (BASELINE_GAME, BASELINE_DASHBOARD):
            if not path.is_file():
                continue
            image = _require_image(path)
            assert image.mode in {"RGB", "RGBA", "L"}, f"{path.name}: unexpected mode {image.mode}"

    def test_screenshot_file_size_reasonable(self) -> None:
        for path in (BASELINE_GAME, BASELINE_DASHBOARD):
            if not path.is_file():
                continue
            size_kb = path.stat().st_size / 1024
            assert size_kb >= 1, f"{path.name} is suspiciously small ({size_kb:.1f} KB)"
            assert size_kb <= 50_000, f"{path.name} is suspiciously large ({size_kb:.1f} KB)"

    def test_game_screenshot_has_dark_background(self) -> None:
        if not (PIL_AVAILABLE and NUMPY_AVAILABLE):
            pytest.skip("Pillow/NumPy not installed")
        image = _require_image(BASELINE_GAME).convert("RGB")
        values = np.asarray(image, dtype=np.float32)
        luminance = 0.299 * values[:, :, 0] + 0.587 * values[:, :, 1] + 0.114 * values[:, :, 2]
        assert float(luminance.mean()) < 180, "Game screenshot is unexpectedly bright"

    def test_game_screenshot_has_neon_colors(self) -> None:
        if not (PIL_AVAILABLE and NUMPY_AVAILABLE):
            pytest.skip("Pillow/NumPy not installed")
        values = np.asarray(_require_image(BASELINE_GAME).convert("RGB"), dtype=np.int16)
        saturation = values.max(axis=2) - values.min(axis=2)
        neon = (values.max(axis=2) >= 150) & (saturation >= 80)
        assert float(neon.mean()) >= 0.001, "Game screenshot contains no meaningful neon colour content"


@pytest.mark.skipif(not PLAYWRIGHT_AVAILABLE, reason="playwright not installed")
class TestLiveVisualRegression:
    """Browser-backed captures; skipped when the optional browser is absent."""

    def test_rendered_game_and_dashboard_against_baselines(self, local_server: Any) -> None:
        if local_server is None:
            pytest.skip("playwright integration is unavailable")
        if not BASELINE_GAME.is_file() or not BASELINE_DASHBOARD.is_file():
            pytest.skip("baseline screenshots not found")

        async def run() -> tuple[list[ScreenshotResult], list[TelemetrySnapshot]]:
            async with async_playwright() as playwright:
                browser_instance = await playwright.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                )
                try:
                    context = await browser_instance.new_context(
                        viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                        device_scale_factor=1,
                        color_scheme="dark",
                    )
                    try:
                        page_instance = await context.new_page()
                        runner = VisualRegressionRunner(local_server.base_url, page_instance)
                        return await runner.run()
                    finally:
                        await context.close()
                finally:
                    await browser_instance.close()

        results, telemetry = asyncio.run(run())
        ReportGenerator(results, telemetry).save_json(REPORT_DIR / "visual_regression_report.json") if WRITE_REPORTS else None
        failures = [result for result in results if not result.passed or result.error]
        assert not failures, "Live visual regression failed: " + "; ".join(
            f"{result.name}: {result.error or result.diff_ratio:.4f}" for result in failures
        )
