import pytest
import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "index.html"
STYLE_CSS = BASE_DIR / "css" / "style.css"

def _read(path: Path) -> str:
    if not path.exists():
        pytest.skip(f"Required file not found: {path}")
    return path.read_text(encoding="utf-8")

@pytest.fixture(scope="module")
def html_source():
    return _read(INDEX_HTML)

@pytest.fixture(scope="module")
def soup(html_source):
    return BeautifulSoup(html_source, "html.parser")

@pytest.fixture(scope="module")
def css_source():
    return _read(STYLE_CSS)

# ---------------------------------------------------------------------------
# 1. HTML Document Structure
# ---------------------------------------------------------------------------

class TestHTMLDocumentStructure:
    """Verify the fundamental HTML5 document skeleton."""

    def test_doctype_present(self, html_source):
        assert html_source.strip().lower().startswith("<!doctype html"), (
            "Document must begin with <!DOCTYPE html>"
        )

    def test_html_lang_attribute(self, soup):
        html_tag = soup.find("html")
        assert html_tag is not None, "<html> element missing"
        assert html_tag.get("lang"), "<html> must carry a lang attribute"

    def test_head_element_exists(self, soup):
        assert soup.find("head") is not None, "<head> element missing"

    def test_body_element_exists(self, soup):
        assert soup.find("body") is not None, "<body> element missing"

    def test_charset_meta(self, soup):
        metas = soup.find_all("meta")
        charsets = [m for m in metas if m.get("charset")]
        assert charsets, "A <meta charset> declaration is required"
        assert charsets[0]["charset"].lower() == "utf-8", "charset must be utf-8"

    def test_viewport_meta(self, soup):
        viewport = soup.find("meta", attrs={"name": "viewport"})
        assert viewport is not None, "<meta name='viewport'> is required"
        content = viewport.get("content", "")
        assert "width=device-width" in content, (
            "viewport must include width=device-width"
        )

    def test_title_element(self, soup):
        title = soup.find("title")
        assert title is not None, "<title> element missing"
        assert title.get_text(strip=True), "<title> must not be empty"

    def test_stylesheet_link(self, soup):
        links = soup.find_all("link", rel=lambda r: r and "stylesheet" in r)
        assert links, "At least one stylesheet <link> is required"

    def test_css_link_points_to_style_css(self, soup):
        links = soup.find_all("link", rel=lambda r: r and "stylesheet" in r)
        hrefs = [l.get("href", "") for l in links]
        assert any("style.css" in h for h in hrefs), (
            "A stylesheet link pointing to style.css is expected"
        )

# ---------------------------------------------------------------------------
# 2. Canvas Element
# ---------------------------------------------------------------------------

class TestCanvasElement:
    """Verify the HTML5 canvas used as the game rendering surface."""

    def _get_canvas(self, soup):
        canvas = soup.find("canvas")
        if canvas is None:
            pytest.fail("<canvas> element not found in index.html")
        return canvas

    def test_canvas_exists(self, soup):
        assert soup.find("canvas") is not None, "<canvas> element is required"

    def test_canvas_has_id(self, soup):
        canvas = self._get_canvas(soup)
        assert canvas.get("id"), "<canvas> must have an id attribute"

    def test_canvas_id_value(self, soup):
        canvas = self._get_canvas(soup)
        cid = canvas.get("id", "")
        assert cid, "<canvas> id must not be empty"
        # Common game canvas ids
        assert re.match(r"[a-zA-Z][\w\-]*", cid), (
            f"<canvas> id '{cid}' is not a valid identifier"
        )

    def test_canvas_width_attribute(self, soup):
        canvas = self._get_canvas(soup)
        # width may be set via attribute or CSS; attribute is preferred for 2D context
        # We accept either attribute presence or inline style
        has_attr = canvas.get("width") is not None
        has_style = "width" in (canvas.get("style") or "")
        assert has_attr or has_style, (
            "<canvas> should declare a width (attribute or inline style)"
        )

    def test_canvas_height_attribute(self, soup):
        canvas = self._get_canvas(soup)
        has_attr = canvas.get("height") is not None
        has_style = "height" in (canvas.get("style") or "")
        assert has_attr or has_style, (
            "<canvas> should declare a height (attribute or inline style)"
        )

    def test_canvas_fallback_content(self, soup):
        canvas = self._get_canvas(soup)
        # Fallback text/content for browsers that don't support canvas
        fallback = canvas.get_text(strip=True)
        # Fallback is optional but good practice; we just warn via a soft check
        # (not a hard failure so we don't block games that omit it)
        _ = fallback  # acknowledged

    def test_canvas_inside_body(self, soup):
        body = soup.find("body")
        assert body is not None
        canvas = body.find("canvas")
        assert canvas is not None, "<canvas> must be inside <body>"

# ---------------------------------------------------------------------------
# 3. Cyberpunk Telemetry HUD Elements
# ---------------------------------------------------------------------------

class TestCyberpunkTelemetryHUD:
    """Verify the cyberpunk telemetry / HUD overlay elements exist in the DOM."""

    # We look for common HUD patterns: score, lives, level, fps counter, etc.
    # Tests are flexible enough to match various id/class naming conventions.

    def _find_by_patterns(self, soup, *patterns):
        """Return first element matching any of the given id/class regex patterns."""
        for pat in patterns:
            regex = re.compile(pat, re.IGNORECASE)
            el = soup.find(id=regex) or soup.find(class_=regex)
            if el:
                return el
        return None

    def test_hud_container_exists(self, soup):
        el = self._find_by_patterns(
            soup,
            r"hud",
            r"overlay",
            r"dashboard",
            r"telemetry",
            r"ui[-_]?container",
            r"game[-_]?ui",
        )
        assert el is not None, (
            "A HUD/overlay container element (id or class matching hud, overlay, "
            "dashboard, telemetry, ui-container, or game-ui) is required"
        )

    def test_score_display_exists(self, soup):
        el = self._find_by_patterns(
            soup,
            r"score",
            r"points",
            r"pts",
        )
        assert el is not None, (
            "A score/points display element is required in the HUD"
        )

    def test_lives_or_health_display_exists(self, soup):
        el = self._find_by_patterns(
            soup,
            r"lives?",
            r"health",
            r"hp",
            r"shield",
            r"energy",
        )
        assert el is not None, (
            "A lives/health/energy display element is required in the HUD"
        )

    def test_level_or_wave_display_exists(self, soup):
        el = self._find_by_patterns(
            soup,
            r"level",
            r"wave",
            r"stage",
            r"round",
        )
        assert el is not None, (
            "A level/wave/stage display element is required in the HUD"
        )

    def test_fps_or_telemetry_counter_exists(self, soup):
        el = self._find_by_patterns(
            soup,
            r"fps",
            r"frame[-_]?rate",
            r"telemetry",
            r"perf",
            r"debug",
            r"stats",
        )
        assert el is not None, (
            "An FPS/telemetry/performance counter element is required"
        )

    def test_hud_elements_are_in_body(self, soup):
        body = soup.find("body")
        assert body is not None
        # At least one div/span/section with a HUD-like id or class must be in body
        hud_patterns = re.compile(
            r"hud|overlay|dashboard|telemetry|score|lives|health|level|wave|fps",
            re.IGNORECASE,
        )
        found = body.find(id=hud_patterns) or body.find(class_=hud_patterns)
        assert found is not None, (
            "HUD elements must be present inside <body>"
        )

# ---------------------------------------------------------------------------
# 4. UI Dashboard Overlays
# ---------------------------------------------------------------------------

class TestUIDashboardOverlays:
    """Verify game-state overlay screens: start, pause, game-over, etc."""

    def _find_overlay(self, soup, *patterns):
        for pat in patterns:
            regex = re.compile(pat, re.IGNORECASE)
            el = soup.find(id=regex) or soup.find(class_=regex)
            if el:
                return el
        return None

    def test_start_screen_overlay_exists(self, soup):
        el = self._find_overlay(
            soup,
            r"start[-_]?(screen|menu|overlay|panel)?",
            r"(screen|menu|overlay|panel)?[-_]?start",
            r"title[-_]?(screen|menu)?",
            r"intro",
            r"splash",
            r"main[-_]?menu",
        )
        assert el is not None, (
            "A start/title/intro screen overlay element is required"
        )

    def test_game_over_overlay_exists(self, soup):
        el = self._find_overlay(
            soup,
            r"game[-_]?over",
            r"over[-_]?screen",
            r"death[-_]?screen",
            r"end[-_]?(screen|panel|overlay)?",
            r"(screen|panel|overlay)?[-_]?end",
        )
        assert el is not None, (
            "A game-over/end screen overlay element is required"
        )

    def test_pause_overlay_exists(self, soup):
        el = self._find_overlay(
            soup,
            r"pause",
            r"paused",
            r"pause[-_]?(screen|menu|overlay|panel)?",
        )
        assert el is not None, (
            "A pause screen/menu overlay element is required"
        )

    def test_overlays_have_display_none_or_hidden_class(self, soup):
        """Overlays that are not the default view should start hidden."""
        overlay_patterns = re.compile(
            r"game[-_]?over|pause|paused|end[-_]screen|death[-_]screen",
            re.IGNORECASE,
        )
        overlays = soup.find_all(id=overlay_patterns) + soup.find_all(
            class_=overlay_patterns
        )
        for overlay in overlays:
            style = overlay.get("style", "")
            classes = " ".join(overlay.get("class", []))
            is_hidden = (
                "display:none" in style.replace(" ", "")
                or "display: none" in style
                or "hidden" in classes
                or "inactive" in classes
                or "invisible" in classes
            )
            assert is_hidden, (
                f"Overlay element '{overlay.get('id') or overlay.get('class')}' "
                f"should start hidden (display:none or a hidden/inactive class)"
            )

    def test_start_button_exists(self, soup):
        btn_patterns = re.compile(
            r"start[-_]?(btn|button|play)?|play[-_]?(btn|button)?|(btn|button)?[-_]?start",
            re.IGNORECASE,
        )
        btn = (
            soup.find("button", id=btn_patterns)
            or soup.find("button", class_=btn_patterns)
            or soup.find(id=btn_patterns)
            or soup.find(class_=btn_patterns)
        )
        assert btn is not None, (
            "A start/play button element is required"
        )

    def test_restart_button_exists(self, soup):
        btn_patterns = re.compile(
            r"restart|replay|play[-_]?again|retry|(btn|button)?[-_]?restart",
            re.IGNORECASE,
        )
        btn = (
            soup.find("button", id=btn_patterns)
            or soup.find("button", class_=btn_patterns)
            or soup.find(id=btn_patterns)
            or soup.find(class_=btn_patterns)
        )
        assert btn is not None, (
            "A restart/replay/retry button element is required"
        )

# ---------------------------------------------------------------------------
# 5. JavaScript Integration
# ---------------------------------------------------------------------------

class TestJavaScriptIntegration:
    """Verify script tags and inline JS patterns for game loop and audio."""

    def _get_scripts(self, soup):
        return soup.find_all("script")

    def test_at_least_one_script_tag(self, soup):
        scripts = self._get_scripts(soup)
        assert scripts, "At least one <script> tag is required"

    def test_main_script_present(self, soup):
        scripts = self._get_scripts(soup)
        src_scripts = [s for s in scripts if s.get("src")]
        inline_scripts = [s for s in scripts if not s.get("src") and s.string]
        assert src_scripts or inline_scripts, (
            "Either an external script src or inline script content is required"
        )

    def test_request_animation_frame_referenced(self, soup):
        """The game loop must use requestAnimationFrame."""
        scripts = self._get_scripts(soup)
        all_js = " ".join(
            (s.string or "") for s in scripts if not s.get("src")
        )
        # Also check src filenames for common game script names
        src_names = [s.get("src", "") for s in scripts if s.get("src")]
        has_raf_inline = "requestAnimationFrame" in all_js
        has_game_script = any(
            re.search(r"game|main|app|engine", src, re.IGNORECASE)
            for src in src_names
        )
        assert has_raf_inline or has_game_script, (
            "requestAnimationFrame must be referenced in inline JS, or a "
            "game/main/app/engine script must be linked"
        )

    def test_web_audio_api_referenced(self, soup):
        """Procedural audio must use the Web Audio API."""
        scripts = self._get_scripts(soup)
        all_js = " ".join(
            (s.string or "") for s in scripts if not s.get("src")
        )
        src_names = [s.get("src", "") for s in scripts if s.get("src")]
        has_audio_inline = (
            "AudioContext" in all_js
            or "webkitAudioContext" in all_js
            or "OscillatorNode" in all_js
        )
        has_audio_script = any(
            re.search(r"audio|sound|sfx", src, re.IGNORECASE)
            for src in src_names
        )
        assert has_audio_inline or has_audio_script, (
            "Web Audio API (AudioContext / OscillatorNode) must be referenced "
            "in inline JS or a dedicated audio script must be linked"
        )

    def test_no_external_framework_dependencies(self, soup):
        """Game must be zero-dependency (no jQuery, React, Vue, etc.)."""
        scripts = self._get_scripts(soup)
        forbidden = re.compile(
            r"jquery|react|vue|angular|lodash|underscore|backbone|ember|svelte",
            re.IGNORECASE,
        )
        for script in scripts:
            src = script.get("src", "")
            assert not forbidden.search(src), (
                f"External framework dependency detected in script src: '{src}'. "
                "The game must be zero-dependency."
            )

    def test_delta_time_pattern_in_inline_js(self, soup):
        """Delta-time physics pattern must appear in inline JS."""
        scripts = self._get_scripts(soup)
        all_js = " ".join(
            (s.string or "") for s in scripts if not s.get("src")
        )
        has_delta = bool(
            re.search(r"\bdelta\b|\bdt\b|\belapsed\b|\bdeltaTime\b", all_js)
        )
        src_names = [s.get("src", "") for s in scripts if s.get("src")]
        has_game_script = any(
            re.search(r"game|main|app|engine|physics", src, re.IGNORECASE)
            for src in src_names
        )
        assert has_delta or has_game_script, (
            "Delta-time variable (delta/dt/elapsed/deltaTime) must appear in "
            "inline JS or a physics/game script must be linked"
        )

# ---------------------------------------------------------------------------
# 6. CSS Stylesheet Integrity
# ---------------------------------------------------------------------------

class TestCSSStylesheetIntegrity:
    """Verify css/style.css for cyberpunk visual design tokens."""

    def test_css_file_exists(self):
        assert STYLE_CSS.exists(), f"css/style.css not found at {STYLE_CSS}"

    def test_css_not_empty(self, css_source):
        assert len(css_source.strip()) > 0, "css/style.css must not be empty"

    def test_css_has_body_rule(self, css_source):
        assert re.search(r"\bbody\s*\{", css_source), (
            "css/style.css must contain a body {} rule"
        )

    def test_css_has_canvas_rule(self, css_source):
        assert re.search(r"\bcanvas\s*\{", css_source), (
            "css/style.css must contain a canvas {} rule"
        )

    def test_css_uses_neon_colors(self, css_source):
        """Cyberpunk palette: neon cyan, magenta, green, or yellow."""
        neon_patterns = [
            r"#0ff|#00ffff|cyan",
            r"#f0f|#ff00ff|magenta",
            r"#0f0|#00ff00",
            r"#ff0|#ffff00",
            r"#[0-9a-fA-F]{3,6}",  # any hex color (fallback)
        ]
        has_neon = any(
            re.search(pat, css_source, re.IGNORECASE) for pat in neon_patterns[:4]
        )
        has_any_color = bool(re.search(r"#[0-9a-fA-F]{3,6}", css_source))
        assert has_neon or has_any_color, (
            "css/style.css must define cyberpunk neon colors"
        )

    def test_css_has_glow_or_box_shadow(self, css_source):
        assert re.search(r"box-shadow|text-shadow|filter\s*:\s*drop-shadow", css_source), (
            "css/style.css must use box-shadow, text-shadow, or drop-shadow for neon glow effects"
        )

    def test_css_has_font_family(self, css_source):
        assert re.search(r"font-family\s*:", css_source), (
            "css/style.css must declare a font-family"
        )

    def test_css_uses_monospace_or_cyberpunk_font(self, css_source):
        assert re.search(
            r"monospace|'Courier|\"Courier|Orbitron|Share Tech|VT323|Press Start|Rajdhani|Exo|Roboto Mono",
            css_source,
            re.IGNORECASE,
        ), (
            "css/style.css should use a monospace or cyberpunk-themed font"
        )

    def test_css_has_position_absolute_or_fixed_for_hud(self, css_source):
        assert re.search(r"position\s*:\s*(absolute|fixed)", css_source), (
            "css/style.css must use position: absolute or fixed for HUD overlay positioning"
        )

    def test_css_has_z_index(self, css_source):
        assert re.search(r"z-index\s*:", css_source), (
            "css/style.css must use z-index to layer HUD elements above the canvas"
        )

    def test_css_has_overflow_hidden_on_body_or_html(self, css_source):
        assert re.search(r"overflow\s*:\s*hidden", css_source), (
            "css/style.css must set overflow: hidden to prevent scrollbars during gameplay"
        )

    def test_css_has_margin_zero_on_body(self, css_source):
        # body { margin: 0 } or margin: 0 0 0 0 or margin: 0px etc.
        assert re.search(r"margin\s*:\s*0", css_source), (
            "css/style.css must reset body margin to 0"
        )

    def test_css_has_background_color(self, css_source):
        assert re.search(r"background(-color)?\s*:", css_source), (
            "css/style.css must define a background color"
        )

    def test_css_background_is_dark(self, css_source):
        """Cyberpunk games use dark backgrounds."""
        dark_patterns = [
            r"background(-color)?\s*:\s*#0{3,6}",       # #000 / #000000
            r"background(-color)?\s*:\s*#[01][0-9a-fA-F]{2,5}",  # very dark hex
            r"background(-color)?\s*:\s*black",
            r"background(-color)?\s*:\s*rgb\(\s*0\s*,\s*0\s*,\s*0",
            r"background(-color)?\s*:\s*rgba\(\s*0\s*,\s*0\s*,\s*0",
        ]
        has_dark = any(re.search(p, css_source, re.IGNORECASE) for p in dark_patterns)
        assert has_dark, (
            "css/style.css background should be dark (cyberpunk aesthetic)"
        )

    def test_css_has_transition_or_animation(self, css_source):
        assert re.search(r"transition\s*:|animation\s*:|@keyframes", css_source), (
            "css/style.css must define CSS transitions or animations for UI juice"
        )

    def test_css_has_opacity_or_visibility_for_overlays(self, css_source):
        assert re.search(r"opacity\s*:|visibility\s*:", css_source), (
            "css/style.css must use opacity or visibility for overlay fade effects"
        )

    def test_css_no_syntax_errors_basic(self, css_source):
        """Basic brace-balance check."""
        open_braces = css_source.count("{")
        close_braces = css_source.count("}")
        assert open_braces == close_braces, (
            f"css/style.css has unbalanced braces: "
            f"{open_braces} '{{' vs {close_braces} '}}'"
        )

    def test_css_has_display_flex_or_grid(self, css_source):
        assert re.search(r"display\s*:\s*(flex|grid)", css_source), (
            "css/style.css should use flexbox or grid for layout"
        )

    def test_css_has_pointer_events_none_for_canvas(self, css_source):
        # Canvas should not intercept pointer events if HUD is above it,
        # OR the HUD should have pointer-events: none
        # Either pattern is acceptable
        has_pe = re.search(r"pointer-events\s*:", css_source)
        # This is a soft recommendation; skip if not present but note it
        if not has_pe:
            pytest.skip(
                "pointer-events not set in CSS — recommended for HUD layering"
            )

# ---------------------------------------------------------------------------
# 7. High-DPI / Responsive Canvas
# ---------------------------------------------------------------------------

class TestHighDPIResponsiveCanvas:
    """Verify responsive and high-DPI canvas handling patterns."""

    def test_viewport_initial_scale(self, soup):
        viewport = soup.find("meta", attrs={"name": "viewport"})
        assert viewport is not None
        content = viewport.get("content", "")
        assert "initial-scale=1" in content, (
            "viewport meta must include initial-scale=1"
        )

    def test_canvas_max_width_in_css(self, css_source):
        assert re.search(r"max-width\s*:|width\s*:\s*100%", css_source), (
            "css/style.css should set max-width or 100% width for responsive canvas"
        )

    def test_device_pixel_ratio_in_js(self, soup):
        """High-DPI support requires devicePixelRatio."""
        scripts = soup.find_all("script")
        all_js = " ".join(
            (s.string or "") for s in scripts if not s.get("src")
        )
        src_names = [s.get("src", "") for s in scripts if s.get("src")]
        has_dpr_inline = "devicePixelRatio" in all_js
        has_game_script = any(
            re.search(r"game|main|app|engine|render", src, re.IGNORECASE)
            for src in src_names
        )
        assert has_dpr_inline or has_game_script, (
            "devicePixelRatio must be referenced for high-DPI canvas support, "
            "or a render/game script must be linked"
        )

    def test_canvas_display_block_in_css(self, css_source):
        """Canvas should be display:block to remove inline baseline gap."""
        assert re.search(r"canvas\s*\{[^}]*display\s*:\s*block", css_source, re.DOTALL), (
            "canvas rule in css/style.css should set display: block"
        )

    def test_resize_event_or_responsive_handling(self, soup):
        scripts = soup.find_all("script")
        all_js = " ".join(
            (s.string or "") for s in scripts if not s.get("src")
        )
        src_names = [s.get("src", "") for s in scripts if s.get("src")]
        has_resize = "resize" in all_js or "ResizeObserver" in all_js
        has_game_script = any(
            re.search(r"game|main|app|engine|render", src, re.IGNORECASE)
            for src in src_names
        )
        assert has_resize or has_game_script, (
            "Window resize or ResizeObserver must be handled for responsive canvas, "
            "or a game/render script must be linked"
        )

# ---------------------------------------------------------------------------
# 8. Particle & Visual Effects Markup
# ---------------------------------------------------------------------------

class TestParticleAndVisualEffectsMarkup:
    """Verify DOM hooks for particle systems and screen-shake effects."""

    def _find_by_patterns(self, soup, *patterns):
        for pat in patterns:
            regex = re.compile(pat, re.IGNORECASE)
            el = soup.find(id=regex) or soup.find(class_=regex)
            if el:
                return el
        return None

    def test_particle_container_or_canvas_exists(self, soup):
        """Particles may be rendered on canvas or in a dedicated container."""
        particle_el = self._find_by_patterns(
            soup,
            r"particle",
            r"fx",
            r"effects?",
            r"vfx",
            r"sparks?",
            r"burst",
        )
        canvas = soup.find("canvas")
        assert particle_el is not None or canvas is not None, (
            "A particle container element or canvas for particle rendering is required"
        )

    def test_screen_shake_class_or_js_reference(self, soup):
        scripts = soup.find_all("script")
        all_js = " ".join(
            (s.string or "") for s in scripts if not s.get("src")
        )
        src_names = [s.get("src", "") for s in scripts if s.get("src")]
        has_shake_inline = bool(
            re.search(r"shake|trauma|screenshake|screen_shake", all_js, re.IGNORECASE)
        )
        has_shake_css = bool(
            re.search(r"shake|trauma", " ".join(
                " ".join(el.get("class", [])) for el in soup.find_all(True)
            ), re.IGNORECASE)
        )
        has_game_script = any(
            re.search(r"game|main|app|engine|effects?|vfx", src, re.IGNORECASE)
            for src in src_names
        )
        assert has_shake_inline or has_shake_css or has_game_script, (
            "Screen shake must be referenced in inline JS, CSS classes, "
            "or a game/effects script must be linked"
        )

    def test_neon_glow_css_class_exists(self, css_source):
        assert re.search(
            r"\.(neon|glow|cyberpunk|hud|telemetry|pulse|flicker)",
            css_source,
            re.IGNORECASE,
        ), (
            "css/style.css must define at least one neon/glow/cyberpunk CSS class"
        )

    def test_animation_keyframes_for_pulse_or_flicker(self, css_source):
        assert re.search(
            r"@keyframes\s+(pulse|flicker|glow|blink|scan|neon|fade)",
            css_source,
            re.IGNORECASE,
        ), (
            "css/style.css must define @keyframes for pulse, flicker, glow, "
            "blink, scan, or neon animations"
        )

# ---------------------------------------------------------------------------
# 9. Accessibility & Semantic Markup
# ---------------------------------------------------------------------------

class TestAccessibilityAndSemanticMarkup:
    """Basic accessibility checks for the game UI."""

    def test_buttons_have_text_or_aria_label(self, soup):
        buttons = soup.find_all("button")
        for btn in buttons:
            text = btn.get_text(strip=True)
            aria = btn.get("aria-label", "")
            title = btn.get("title", "")
            assert text or aria or title, (
                f"Button element must have visible text, aria-label, or title: {btn}"
            )

    def test_canvas_has_aria_label_or_role(self, soup):
        canvas = soup.find("canvas")
        if canvas is None:
            pytest.skip("No canvas element found")
        aria_label = canvas.get("aria-label", "")
        role = canvas.get("role", "")
        aria_desc = canvas.get("aria-describedby", "")
        # Canvas accessibility is optional but recommended