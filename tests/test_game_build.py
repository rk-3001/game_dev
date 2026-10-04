import unittest
import os
import re
import json
from pathlib import Path
from html.parser import HTMLParser
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_HTML = BASE_DIR / "index.html"
STYLE_CSS = BASE_DIR / "css" / "style.css"

# ---------------------------------------------------------------------------
# HTML Parser helpers
# ---------------------------------------------------------------------------

class FullHTMLParser(HTMLParser):
    """Collects tags, attributes, scripts, and inline styles from HTML."""

    def __init__(self):
        super().__init__()
        self.tags = []
        self.tag_attrs = defaultdict(list)
        self.ids = {}
        self.classes = defaultdict(list)
        self.canvas_elements = []
        self.script_srcs = []
        self.link_hrefs = []
        self.meta_tags = []
        self.inline_scripts = []
        self.inline_styles = []
        self._current_script = None
        self._current_style = None
        self._in_script = False
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self.tags.append(tag)
        self.tag_attrs[tag].append(attr_dict)

        if "id" in attr_dict:
            self.ids[attr_dict["id"]] = tag

        if "class" in attr_dict:
            for cls in attr_dict["class"].split():
                self.classes[cls].append(tag)

        if tag == "canvas":
            self.canvas_elements.append(attr_dict)

        if tag == "script":
            if "src" in attr_dict:
                self.script_srcs.append(attr_dict["src"])
            else:
                self._in_script = True
                self._current_script = []

        if tag == "link":
            if attr_dict.get("rel") == "stylesheet" and "href" in attr_dict:
                self.link_hrefs.append(attr_dict["href"])

        if tag == "meta":
            self.meta_tags.append(attr_dict)

        if tag == "style":
            self._in_style = True
            self._current_style = []

    def handle_endtag(self, tag):
        if tag == "script" and self._in_script:
            self.inline_scripts.append("".join(self._current_script))
            self._in_script = False
            self._current_script = None

        if tag == "style" and self._in_style:
            self.inline_styles.append("".join(self._current_style))
            self._in_style = False
            self._current_style = None

    def handle_data(self, data):
        if self._in_script and self._current_script is not None:
            self._current_script.append(data)
        if self._in_style and self._current_style is not None:
            self._current_style.append(data)

def parse_html(path: Path) -> FullHTMLParser:
    parser = FullHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser

def read_css(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def extract_css_selectors(css: str) -> list:
    """Return a list of all CSS selectors found in the stylesheet."""
    # Strip comments
    css_no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # Match selector blocks
    selectors = re.findall(r"([^{}]+)\{[^{}]*\}", css_no_comments)
    flat = []
    for sel_group in selectors:
        for sel in sel_group.split(","):
            flat.append(sel.strip())
    return [s for s in flat if s]

def extract_css_properties(css: str) -> dict:
    """Return {selector: [properties]} mapping."""
    css_no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    result = {}
    blocks = re.findall(r"([^{}]+)\{([^{}]*)\}", css_no_comments)
    for selector_group, body in blocks:
        props = {}
        for decl in body.split(";"):
            decl = decl.strip()
            if ":" in decl:
                prop, _, val = decl.partition(":")
                props[prop.strip()] = val.strip()
        for sel in selector_group.split(","):
            sel = sel.strip()
            if sel:
                result.setdefault(sel, {}).update(props)
    return result

def extract_css_variables(css: str) -> dict:
    """Extract CSS custom properties (variables) from :root."""
    variables = {}
    root_match = re.search(r":root\s*\{([^}]*)\}", css, re.DOTALL)
    if root_match:
        body = root_match.group(1)
        for match in re.finditer(r"(--[\w-]+)\s*:\s*([^;]+);", body):
            variables[match.group(1)] = match.group(2).strip()
    return variables

def extract_keyframe_names(css: str) -> list:
    """Return list of @keyframes animation names."""
    return re.findall(r"@keyframes\s+([\w-]+)", css)

def extract_media_queries(css: str) -> list:
    """Return list of @media query strings."""
    return re.findall(r"@media\s+([^{]+)\{", css)

def all_inline_js(parser: FullHTMLParser) -> str:
    parts = list(parser.inline_scripts)
    src_dir = BASE_DIR / "src"
    if src_dir.exists():
        for js_file in sorted(src_dir.glob("*.js")):
            try:
                parts.append(js_file.read_text(encoding="utf-8"))
            except Exception:
                pass
    for src in parser.script_srcs:
        p = BASE_DIR / src
        if p.exists() and p.parent != src_dir:
            try:
                parts.append(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestFileExistence(unittest.TestCase):
    """Verify that required project files exist."""

    def test_index_html_exists(self):
        self.assertTrue(INDEX_HTML.exists(), f"index.html not found at {INDEX_HTML}")

    def test_css_style_exists(self):
        self.assertTrue(STYLE_CSS.exists(), f"css/style.css not found at {STYLE_CSS}")

    def test_index_html_non_empty(self):
        self.assertGreater(INDEX_HTML.stat().st_size, 0, "index.html is empty")

    def test_css_style_non_empty(self):
        self.assertGreater(STYLE_CSS.stat().st_size, 0, "css/style.css is empty")

class TestHTMLStructure(unittest.TestCase):
    """Verify fundamental HTML document structure."""

    @classmethod
    def setUpClass(cls):
        cls.parser = parse_html(INDEX_HTML)
        cls.raw = INDEX_HTML.read_text(encoding="utf-8")

    def test_doctype_present(self):
        self.assertTrue(self.raw.strip().upper().startswith("<!DOCTYPE HTML"),
                        "Missing <!DOCTYPE html> declaration")

    def test_html_tag_present(self):
        self.assertIn("html", self.parser.tags, "Missing <html> tag")

    def test_head_tag_present(self):
        self.assertIn("head", self.parser.tags, "Missing <head> tag")

    def test_body_tag_present(self):
        self.assertIn("body", self.parser.tags, "Missing <body> tag")

    def test_title_tag_present(self):
        self.assertIn("title", self.parser.tags, "Missing <title> tag")

    def test_meta_charset(self):
        charsets = [m for m in self.parser.meta_tags if "charset" in m]
        self.assertTrue(len(charsets) >= 1, "Missing <meta charset> tag")

    def test_meta_viewport(self):
        viewports = [m for m in self.parser.meta_tags
                     if m.get("name", "").lower() == "viewport"]
        self.assertTrue(len(viewports) >= 1, "Missing <meta name='viewport'> tag")

    def test_viewport_content(self):
        for m in self.parser.meta_tags:
            if m.get("name", "").lower() == "viewport":
                content = m.get("content", "")
                self.assertIn("width=device-width", content,
                              "Viewport meta missing width=device-width")
                return
        self.fail("No viewport meta tag found")

    def test_stylesheet_linked(self):
        self.assertTrue(len(self.parser.link_hrefs) >= 1,
                        "No stylesheet <link> tags found")

    def test_css_style_linked(self):
        css_links = [h for h in self.parser.link_hrefs
                     if "style.css" in h or "css" in h.lower()]
        self.assertTrue(len(css_links) >= 1,
                        "css/style.css not linked in <head>")

class TestCanvasSetup(unittest.TestCase):
    """Verify HTML canvas element configuration for game rendering."""

    @classmethod
    def setUpClass(cls):
        cls.parser = parse_html(INDEX_HTML)
        cls.js = all_inline_js(cls.parser)

    def test_canvas_element_exists(self):
        self.assertGreater(len(self.parser.canvas_elements), 0,
                           "No <canvas> element found in index.html")

    def test_canvas_has_id(self):
        for canvas in self.parser.canvas_elements:
            if "id" in canvas:
                return
        self.fail("No <canvas> element has an id attribute")

    def test_canvas_id_value(self):
        ids = [c.get("id", "") for c in self.parser.canvas_elements]
        # Accept common game canvas IDs
        valid_ids = {"gameCanvas", "canvas", "game-canvas", "main-canvas",
                     "renderCanvas", "screen"}
        found = any(cid in valid_ids or "canvas" in cid.lower() for cid in ids)
        self.assertTrue(found, f"Canvas id not recognized: {ids}")

    def test_canvas_2d_context_acquired(self):
        patterns = [
            r"getContext\s*\(\s*['\"]2d['\"]",
            r"getContext\s*\(\s*['\"]webgl['\"]",
            r"getContext\s*\(\s*['\"]experimental-webgl['\"]",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found,
                        "No canvas getContext('2d') or getContext('webgl') call found in JS")

    def test_request_animation_frame_used(self):
        self.assertRegex(self.js, r"requestAnimationFrame",
                         "requestAnimationFrame not found – 60fps loop required")

    def test_delta_time_calculation(self):
        patterns = [
            r"deltaTime",
            r"delta[Tt]ime",
            r"dt\b",
            r"elapsed",
            r"timestamp",
            r"performance\.now\(\)",
            r"Date\.now\(\)",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found,
                        "No delta-time variable found – physics must use delta-time")

    def test_canvas_resize_handling(self):
        patterns = [
            r"resize",
            r"window\.innerWidth",
            r"window\.innerHeight",
            r"devicePixelRatio",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found,
                        "No canvas resize / devicePixelRatio handling found")

    def test_high_dpi_device_pixel_ratio(self):
        self.assertRegex(self.js, r"devicePixelRatio",
                         "devicePixelRatio not referenced – high-DPI canvas required")

    def test_canvas_clear_each_frame(self):
        patterns = [
            r"clearRect",
            r"fillRect.*0.*0",
            r"ctx\.reset\(\)",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found,
                        "No canvas clear operation found (clearRect / fillRect)")

class TestGameLoopAndPhysics(unittest.TestCase):
    """Verify game loop structure and vector physics patterns."""

    @classmethod
    def setUpClass(cls):
        cls.js = all_inline_js(parse_html(INDEX_HTML))

    def test_game_loop_function_defined(self):
        patterns = [
            r"function\s+(?:gameLoop|loop|update|render|tick|animate|frame)",
            r"(?:const|let|var)\s+(?:gameLoop|loop|update|render|tick|animate|frame)\s*=",
            r"\b(?:gameLoop|loop|update|render|tick|animate|frame)\s*\([^)]*\)\s*\{",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "No game loop function definition found")


    def test_raf_recursive_call(self):
        # requestAnimationFrame should be called inside the loop
        raf_calls = re.findall(r"requestAnimationFrame\s*\(", self.js)
        self.assertGreaterEqual(len(raf_calls), 1,
                                "requestAnimationFrame must be called at least once")

    def test_velocity_vectors_present(self):
        patterns = [
            r"\bvx\b", r"\bvy\b",
            r"velocity",
            r"vel\b",
            r"speed",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "No velocity vector variables found (vx/vy/velocity)")

    def test_position_vectors_present(self):
        patterns = [r"\bx\b", r"\by\b", r"pos(?:ition)?", r"\.x\b", r"\.y\b"]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "No position vector variables found")

    def test_collision_detection(self):
        patterns = [
            r"collid",
            r"intersect",
            r"overlap",
            r"bounce",
            r"hit\b",
            r"detect",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No collision detection logic found")

    def test_game_state_management(self):
        patterns = [
            r"gameState",
            r"state\s*[=:]",
            r"PLAYING",
            r"GAME_OVER",
            r"PAUSED",
            r"score\b",
            r"lives\b",
            r"level\b",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No game state management found")

class TestVisualJuice(unittest.TestCase):
    """Verify visual effects: particles, screen shake, glows, trails."""

    @classmethod
    def setUpClass(cls):
        cls.js = all_inline_js(parse_html(INDEX_HTML))

    def test_particle_system_present(self):
        patterns = [
            r"particle",
            r"Particle",
            r"particles\b",
            r"emitter",
            r"burst",
            r"spark",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "No particle system found – visual juice required")

    def test_screen_shake_present(self):
        patterns = [
            r"shake",
            r"screenShake",
            r"camera.*shake",
            r"trauma",
            r"shakeAmount",
            r"shakeIntensity",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No screen shake effect found")

    def test_glow_or_shadow_blur(self):
        patterns = [
            r"shadowBlur",
            r"shadowColor",
            r"glow",
            r"bloom",
            r"filter.*blur",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No glow/shadowBlur effect found – neon aesthetics required")

    def test_neon_colors_present(self):
        # Neon colors: cyan, magenta, lime, electric blue, hot pink
        neon_patterns = [
            r"#[0-9a-fA-F]{3,6}",  # hex colors
            r"rgba?\s*\(",
            r"hsl\s*\(",
            r"cyan",
            r"magenta",
            r"neon",
            r"electric",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in neon_patterns)
        self.assertTrue(found, "No neon color definitions found in JS")

    def test_particle_trail_or_fade(self):
        patterns = [
            r"trail",
            r"alpha",
            r"opacity",
            r"fade",
            r"globalAlpha",
            r"ttl\b",
            r"lifetime",
            r"lifespan",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No particle trail/fade/alpha found")

    def test_animation_easing_or_lerp(self):
        patterns = [
            r"\blerp\b",
            r"easing",
            r"ease",
            r"tween",
            r"interpolat",
            r"\* 0\.\d+",  # common lerp pattern: val += (target - val) * 0.x
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No animation easing/lerp found – smooth animations required")

class TestCyberpunkHUD(unittest.TestCase):
    """Verify cyberpunk telemetry HUD elements in HTML and JS."""

    @classmethod
    def setUpClass(cls):
        cls.parser = parse_html(INDEX_HTML)
        cls.js = all_inline_js(cls.parser)
        cls.raw_html = INDEX_HTML.read_text(encoding="utf-8")

    def test_hud_container_exists(self):
        hud_ids = [k for k in self.parser.ids
                   if any(kw in k.lower() for kw in ["hud", "dashboard", "overlay",
                                                       "telemetry", "ui", "panel"])]
        hud_classes = [k for k in self.parser.classes
                       if any(kw in k.lower() for kw in ["hud", "dashboard", "overlay",
                                                           "telemetry", "ui", "panel"])]

        self.assertTrue(len(hud_ids) + len(hud_classes) >= 1,
                        "No HUD/dashboard/overlay container found in HTML")

    def test_score_display_element(self):
        score_ids = [k for k in self.parser.ids
                     if any(kw in k.lower() for kw in ["score", "points", "tally"])]
        score_classes = [k for k in self.parser.classes
                         if any(kw in k.lower() for kw in ["score", "points", "tally"])]
        score_in_js = re.search(r"score", self.js, re.IGNORECASE)
        self.assertTrue(len(score_ids) + len(score_classes) >= 1 or score_in_js,
                        "No score display element found")

    def test_lives_or_health_display(self):
        patterns_html = ["lives", "health", "hp", "shield", "energy", "life"]
        found_html = any(
            any(kw in k.lower() for kw in patterns_html)
            for k in list(self.parser.ids) + list(self.parser.classes)
        )
        found_js = any(re.search(p, self.js, re.IGNORECASE)
                       for p in [r"\blives\b", r"\bhealth\b", r"\bhp\b",
                                  r"\bshield\b", r"\benergy\b"])
        self.assertTrue(found_html or found_js,
                        "No lives/health/HP display found")

    def test_level_or_wave_display(self):
        patterns = [r"\blevel\b", r"\bwave\b", r"\bstage\b", r"\bround\b"]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No level/wave/stage indicator found")

    def test_hud_updates_dynamically(self):
        # HUD should update DOM elements or draw on canvas
        patterns = [
            r"innerHTML",
            r"textContent",
            r"innerText",
            r"getElementById.*score",
            r"querySelector.*hud",
            r"fillText",  # canvas text rendering
            r"ctx\.fillText",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "HUD does not appear to update dynamically")

    def test_telemetry_fps_or_perf_display(self):
        patterns = [
            r"\bfps\b",
            r"frameRate",
            r"performance",
            r"telemetry",
            r"debug",
            r"frameCount",
            r"frameTime",
        ]
        found = any(re.search(p, self.js, re.IGNORECASE) for p in patterns)
        self.assertTrue(found, "No FPS/performance telemetry display found")

class TestWebAudioAPI(unittest.TestCase):
    """Verify procedural Web Audio API sound synthesis."""

    @classmethod
    def setUpClass(cls):
        cls.js = all_inline_js(parse_html(INDEX_HTML))

    def test_audio_context_created(self):
        patterns = [
            r"AudioContext",
            r"webkitAudioContext",
            r"new\s+AudioContext",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "No AudioContext found – Web Audio API required")

    def test_oscillator_used(self):
        self.assertRegex(self.js, r"createOscillator|OscillatorNode",
                         "No oscillator found – procedural audio required")

    def test_gain_node_used(self):
        self.assertRegex(self.js, r"createGain|GainNode",
                         "No GainNode found – gain envelope required")

    def test_oscillator_frequency_set(self):
        patterns = [
            r"frequency\.setValueAtTime",
            r"frequency\.value\s*=",
            r"frequency\.linearRampToValueAtTime",
            r"frequency\.exponentialRampToValueAtTime",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "Oscillator frequency not configured")

    def test_gain_envelope_applied(self):
        patterns = [
            r"gain\.setValueAtTime",
            r"gain\.linearRampToValueAtTime",
            r"gain\.exponentialRampToValueAtTime",
            r"gain\.value\s*=",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "No gain envelope found – audio shaping required")

    def test_oscillator_connected_to_destination(self):
        patterns = [
            r"connect\s*\(",
            r"\.connect\s*\(",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "Audio nodes not connected to destination")

    def test_oscillator_started(self):
        patterns = [
            r"\.start\s*\(",
            r"oscillator\.start",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "Oscillator never started")

    def test_oscillator_stopped_or_scheduled(self):
        patterns = [
            r"\.stop\s*\(",
            r"oscillator\.stop",
            r"stopTime",
        ]
        found = any(re.search(p, self.js) for p in patterns)
        self.assertTrue(found, "Oscillator never stopped – memory leak risk")

    def test_no_external_audio_files(self):
        # Zero-dependency: no <audio> src or fetch for audio files
        audio_file_patterns = [
            r"\.mp3",
            r"\.ogg",
            r"\.wav",
            r"\.aac",
            r"\.flac",
        ]
        for p in audio_file_patterns:
            self.assertNotRegex(self.js, p,
                                f"External audio file reference found ({p}) – use procedural audio only")

class TestCSSStylesheet(unittest.TestCase):
    """Verify CSS stylesheet integrity and cyberpunk design tokens."""

    @classmethod
    def setUpClass(cls):
        cls.css = read_css(STYLE_CSS)
        cls.selectors = extract_css_selectors(cls.css)
        cls.properties = extract_css_properties(cls.css)
        cls.variables = extract_css_variables(cls.css)
        cls.keyframes = extract_keyframe_names(cls.css)
        cls.media_queries = extract_media_queries(cls.css)

    def test_css_has_content(self):
        self.assertGreater(len(self.css.strip()), 100,
                           "css/style.css appears nearly empty")

    def test_root_variables_defined(self):
        self.assertGreater(len(self.variables), 0,
                           "No CSS custom properties (variables) defined in :root")

    def test_neon_color_variables(self):
        # At least one neon/cyberpunk color variable
        neon_keywords = ["neon", "cyan", "magenta", "electric", "glow",
                         "primary", "accent", "highlight"]
        found = any(
            any(kw in var_name.lower() for kw in neon_keywords)
            for var_name in self.variables
        )
        # Also check variable values for neon hex codes
        neon_hex = re.compile(
            r"#(00ffff|ff00ff|00ff00|ff0080|0080ff|ff4500|7fff00|ff69b4|"
            r"00bfff|ff1493|39ff14|ff6600|bf00ff|00ff7f)",
            re.IGNORECASE
        )
        found_in_values = any(neon_hex.search(v) for v in self.variables.values())
        self.assertTrue(found or found_in_values,
                        "No neon/cyberpunk color variables found in :root")

    def test_body_or_html_selector(self):
        body_selectors = [s for s in self.selectors
                          if s.strip() in ("body", "html", "html, body", "html,body",
                                           "*, *::before, *::after", "*")]
        self.assertTrue(len(body_selectors) >= 1,
                        "No body/html base selector found in CSS")

    def test_canvas_styled(self):
        canvas_selectors = [s for s in self.selectors
                            if "canvas" in s.lower()]
        self.assertTrue(len(canvas_selectors) >= 1,
                        "No canvas selector found in CSS")

    def test_hud_or_overlay_styled(self):
        hud_keywords = ["hud", "overlay", "dashboard", "panel", "telemetry", "ui"]
        found = any(
            any(kw in s.lower() for kw in hud_keywords)
            for s in self.selectors
        )
        self.assertTrue(found, "No HUD/overlay/dashboard CSS selectors found")

    def test_keyframe_animations_defined(self):
        self.assertGreater(len(self.keyframes), 0,
                           "No @keyframes animations defined in CSS")

    def test_glow_animation_or_filter(self):
        glow_keywords = ["glow", "pulse", "flicker", "blink", "neon", "shine"]
        found_keyframe = any(
            any(kw in name.lower() for kw in glow_keywords)
            for name in self.keyframes
        )
        found_filter = re.search(r"filter\s*:.*blur|box-shadow.*#|text-shadow", self.css)
        self.assertTrue(found_keyframe or found_filter,
                        "No glow animation or filter effect found in CSS")

    def test_responsive_media_queries(self):
        self.assertGreater(len(self.media_queries), 0,
                           "No @media queries found – responsive design required")

    def test_font_family_defined(self):
        font_found = re.search(r"font-family\s*:", self.css)
        self.assertIsNotNone(font_found, "No font-family defined in CSS")

    def test_cyberpunk_font_or_monospace(self):
        mono_fonts = ["monospace", "courier", "consolas", "orbitron",
                      "rajdhani", "exo", "share tech", "vt323", "press start",
                      "audiowide", "oxanium", "chakra petch"]
        found = any(f.lower() in self.css.lower() for f in mono_fonts)
        self.assertTrue(found,
                        "No cyberpunk/monospace font found – use a retro/tech font")

    def test_overflow_hidden_on_body_or_canvas(self):
        found = re.search(r"overflow\s*:\s*hidden", self.css)
        self.assertIsNotNone(found,
                             "overflow:hidden not set – canvas may cause scrollbars")

    def test_background_dark_theme(self):
        # Dark background: black, very dark hex, or dark CSS variable
        dark_patterns = [
            r"background(?:-color)?\s*:\s*#0[0-3][0-9a-fA-F]{4}",
            r"background(?:-color)?\s*:\s*#000",
            r"background(?:-color)?\s*:\s*black",
            r"background(?:-color)?\s*:\s*rgb\s*\(\s*0\s*,\s*0\s*,\s*0",
            r"background(?:-color)?\s*:\s*rgba\s*\(\s*0\s*,\s*0\s*,\s*0",
            r"background(?:-color)?\s*:\s*var\(--",
        ]
        found = any(re.search(p, self.css, re.IGNORECASE) for p in dark_patterns)
        self.assertTrue(found, "No dark background color found – cyberpunk requires dark theme")

    def test_position_fixed_or_absolute_for_hud(self):
        found = re.search(r"position\s*:\s*(fixed|absolute)", self.css)
        self.assertIsNotNone(found,
                             "No fixed/absolute positioning found – HUD overlays need it")

    def test_z_index_layering(self):
        found = re.search(r"z-index\s*:", self.css)
        self.assertIsNotNone(found, "No z-index layering found – HUD overlays need it")


if __name__ == "__main__":
    unittest.main()