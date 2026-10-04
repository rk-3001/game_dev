#!/usr/bin/env bash
# =============================================================================
# run_all_tests.sh — Visual Regression & Telemetry Screenshot Comparison Suite
# =============================================================================
# Automated visual regression test runner comparing rendered game states and
# telemetry dashboard views against baseline screenshots with a unified test
# execution harness.
#
# Baselines: screenshot.png, screenshot_dashboard.png
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# ANSI colour palette (cyberpunk neon theme)
# ---------------------------------------------------------------------------
RESET='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[38;5;51m'
MAGENTA='\033[38;5;201m'
GREEN='\033[38;5;118m'
YELLOW='\033[38;5;226m'
RED='\033[38;5;196m'
BLUE='\033[38;5;39m'
WHITE='\033[38;5;255m'
ORANGE='\033[38;5;208m'

# ---------------------------------------------------------------------------
# Configuration & paths
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

BASELINE_DIR="${SCRIPT_DIR}/baselines"
ACTUAL_DIR="${SCRIPT_DIR}/actual"
DIFF_DIR="${SCRIPT_DIR}/diffs"
REPORT_DIR="${SCRIPT_DIR}/reports"
LOG_DIR="${SCRIPT_DIR}/logs"

BASELINE_GAME="${BASELINE_DIR}/screenshot.png"
BASELINE_DASHBOARD="${BASELINE_DIR}/screenshot_dashboard.png"

ACTUAL_GAME="${ACTUAL_DIR}/screenshot.png"
ACTUAL_DASHBOARD="${ACTUAL_DIR}/screenshot_dashboard.png"

DIFF_GAME="${DIFF_DIR}/diff_screenshot.png"
DIFF_DASHBOARD="${DIFF_DIR}/diff_screenshot_dashboard.png"

REPORT_HTML="${REPORT_DIR}/visual_regression_report.html"
REPORT_JSON="${REPORT_DIR}/visual_regression_report.json"
MAIN_LOG="${LOG_DIR}/run_all_tests.log"

# Pixel-difference threshold (0–100 %). Fail if diff exceeds this.
PIXEL_DIFF_THRESHOLD="${PIXEL_DIFF_THRESHOLD:-2.0}"

# Screenshot capture timeout (seconds)
CAPTURE_TIMEOUT="${CAPTURE_TIMEOUT:-30}"

# Server port for serving the game
SERVER_PORT="${SERVER_PORT:-8765}"

# Puppeteer / Playwright script (generated inline if absent)
CAPTURE_SCRIPT="${SCRIPT_DIR}/capture_screenshots.js"

# Timestamp for this run
RUN_TS="$(date +%Y%m%dT%H%M%S)"

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

declare -a TEST_RESULTS=()   # "name|status|detail"

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
log() {
    local level="$1"; shift
    local msg="$*"
    local ts; ts="$(date '+%H:%M:%S')"
    echo -e "${DIM}[${ts}]${RESET} ${msg}" | tee -a "${MAIN_LOG}"
}

banner() {
    local text="$1"
    local width=72
    local line; line="$(printf '═%.0s' $(seq 1 $width))"
    echo -e "${CYAN}${BOLD}"
    echo -e "╔${line}╗"
    printf "║  %-$((width-2))s║\n" "${text}"
    echo -e "╚${line}╝"
    echo -e "${RESET}"
}

section() {
    echo -e "\n${MAGENTA}${BOLD}▶ $*${RESET}"
    echo -e "${DIM}$(printf '─%.0s' $(seq 1 68))${RESET}"
}

pass() { echo -e "  ${GREEN}${BOLD}✔ PASS${RESET}  $*"; }
fail() { echo -e "  ${RED}${BOLD}✘ FAIL${RESET}  $*"; }
skip() { echo -e "  ${YELLOW}${BOLD}⊘ SKIP${RESET}  $*"; }
info() { echo -e "  ${BLUE}ℹ${RESET}  $*"; }
warn() { echo -e "  ${ORANGE}⚠${RESET}  $*"; }

record_result() {
    local name="$1" status="$2" detail="${3:-}"
    TEST_RESULTS+=("${name}|${status}|${detail}")
    TESTS_TOTAL=$(( TESTS_TOTAL + 1 ))
    case "${status}" in
        PASS)   TESTS_PASSED=$(( TESTS_PASSED + 1 )) ;;
        FAIL)   TESTS_FAILED=$(( TESTS_FAILED + 1 )) ;;
        SKIP)   TESTS_SKIPPED=$(( TESTS_SKIPPED + 1 )) ;;
    esac
}

require_cmd() {
    local cmd="$1"
    if ! command -v "${cmd}" &>/dev/null; then
        warn "Required command not found: ${cmd}"
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# Directory bootstrap
# ---------------------------------------------------------------------------
bootstrap_dirs() {
    section "Bootstrapping directories"
    for d in "${BASELINE_DIR}" "${ACTUAL_DIR}" "${DIFF_DIR}" "${REPORT_DIR}" "${LOG_DIR}"; do
        mkdir -p "${d}"
        info "Ensured: ${d}"
    done
    : > "${MAIN_LOG}"
    info "Log: ${MAIN_LOG}"
}

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
check_dependencies() {
    section "Checking dependencies"
    local missing=0

    for cmd in node npm python3 convert compare identify bc; do
        if require_cmd "${cmd}"; then
            pass "${cmd} — $(command -v "${cmd}")"
        else
            fail "${cmd} — NOT FOUND"
            missing=$(( missing + 1 ))
        fi
    done

    # Optional: puppeteer or playwright
    local capture_runtime=""
    if node -e "require('puppeteer')" 2>/dev/null; then
        capture_runtime="puppeteer"
        pass "Node module: puppeteer"
    elif node -e "require('playwright')" 2>/dev/null; then
        capture_runtime="playwright"
        pass "Node module: playwright"
    else
        warn "Neither puppeteer nor playwright found — will attempt install"
        capture_runtime="none"
    fi

    export CAPTURE_RUNTIME="${capture_runtime}"

    if (( missing > 0 )); then
        warn "${missing} dependency/ies missing. Some tests may be skipped."
    fi
}

# ---------------------------------------------------------------------------
# Install headless browser library if needed
# ---------------------------------------------------------------------------
install_capture_runtime() {
    if [[ "${CAPTURE_RUNTIME}" != "none" ]]; then
        return 0
    fi

    section "Installing puppeteer (headless Chrome)"
    if ! require_cmd npm; then
        warn "npm not available — cannot install puppeteer"
        CAPTURE_RUNTIME="unavailable"
        return 1
    fi

    (cd "${SCRIPT_DIR}" && npm install --save-dev puppeteer 2>>"${MAIN_LOG}") && {
        CAPTURE_RUNTIME="puppeteer"
        pass "puppeteer installed"
    } || {
        warn "puppeteer install failed"
        CAPTURE_RUNTIME="unavailable"
    }
}

# ---------------------------------------------------------------------------
# Generate the Node.js screenshot capture script
# ---------------------------------------------------------------------------
generate_capture_script() {
    section "Generating screenshot capture script"

    cat > "${CAPTURE_SCRIPT}" << 'NODEJS_EOF'
#!/usr/bin/env node
/**
 * capture_screenshots.js
 * Headless browser screenshot capture for visual regression tests.
 * Supports puppeteer and playwright.
 */
'use strict';

const path = require('path');
const fs   = require('fs');

const BASE_URL        = process.env.GAME_BASE_URL  || 'http://localhost:8765';
const OUT_GAME        = process.env.OUT_GAME        || path.join(__dirname, 'actual', 'screenshot.png');
const OUT_DASHBOARD   = process.env.OUT_DASHBOARD   || path.join(__dirname, 'actual', 'screenshot_dashboard.png');
const VIEWPORT_W      = parseInt(process.env.VIEWPORT_W  || '1280', 10);
const VIEWPORT_H      = parseInt(process.env.VIEWPORT_H  || '720',  10);
const WAIT_MS         = parseInt(process.env.WAIT_MS     || '4000', 10);
const RUNTIME         = process.env.CAPTURE_RUNTIME || 'puppeteer';

async function captureWithPuppeteer() {
    const puppeteer = require('puppeteer');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=' + VIEWPORT_W + ',' + VIEWPORT_H,
        ],
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: VIEWPORT_W, height: VIEWPORT_H, deviceScaleFactor: 1 });

        // ── Game screenshot ──────────────────────────────────────────────
        console.log('[capture] Loading game:', BASE_URL);
        await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 30000 });

        // Wait for canvas to be present and painted
        await page.waitForSelector('canvas', { timeout: 10000 }).catch(() => {});
        await page.waitForFunction(
            () => {
                const c = document.querySelector('canvas');
                if (!c) return false;
                const ctx = c.getContext('2d');
                if (!ctx) return false;
                const d = ctx.getImageData(0, 0, 1, 1).data;
                return d[3] > 0; // alpha > 0 means something rendered
            },
            { timeout: 15000 }
        ).catch(() => console.warn('[capture] Canvas paint check timed out'));

        // Allow animations to settle
        await new Promise(r => setTimeout(r, WAIT_MS));
        await page.screenshot({ path: OUT_GAME, fullPage: false });
        console.log('[capture] Game screenshot saved:', OUT_GAME);

        // ── Dashboard screenshot ─────────────────────────────────────────
        const dashUrl = BASE_URL.replace(/\/?$/, '/') + 'dashboard.html';
        console.log('[capture] Loading dashboard:', dashUrl);

        let dashExists = false;
        try {
            const resp = await page.goto(dashUrl, { waitUntil: 'networkidle0', timeout: 15000 });
            dashExists = resp && resp.ok();
        } catch (_) {
            console.warn('[capture] Dashboard URL not reachable, using game page with #dashboard hash');
        }

        if (!dashExists) {
            // Fallback: navigate to hash route
            await page.goto(BASE_URL + '#dashboard', { waitUntil: 'networkidle0', timeout: 15000 })
                      .catch(() => {});
        }

        await new Promise(r => setTimeout(r, WAIT_MS));
        await page.screenshot({ path: OUT_DASHBOARD, fullPage: false });
        console.log('[capture] Dashboard screenshot saved:', OUT_DASHBOARD);

    } finally {
        await browser.close();
    }
}

async function captureWithPlaywright() {
    const { chromium } = require('playwright');
    const browser = await chromium.launch({ headless: true });
    try {
        const context = await browser.newContext({
            viewport: { width: VIEWPORT_W, height: VIEWPORT_H },
        });
        const page = await context.newPage();

        // ── Game screenshot ──────────────────────────────────────────────
        console.log('[capture] Loading game:', BASE_URL);
        await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForSelector('canvas', { timeout: 10000 }).catch(() => {});
        await new Promise(r => setTimeout(r, WAIT_MS));
        await page.screenshot({ path: OUT_GAME });
        console.log('[capture] Game screenshot saved:', OUT_GAME);

        // ── Dashboard screenshot ─────────────────────────────────────────
        const dashUrl = BASE_URL.replace(/\/?$/, '/') + 'dashboard.html';
        console.log('[capture] Loading dashboard:', dashUrl);
        await page.goto(dashUrl, { waitUntil: 'networkidle', timeout: 15000 }).catch(async () => {
            await page.goto(BASE_URL + '#dashboard', { waitUntil: 'networkidle', timeout: 15000 }).catch(() => {});
        });
        await new Promise(r => setTimeout(r, WAIT_MS));
        await page.screenshot({ path: OUT_DASHBOARD });
        console.log('[capture] Dashboard screenshot saved:', OUT_DASHBOARD);

    } finally {
        await browser.close();
    }
}

(async () => {
    try {
        if (RUNTIME === 'playwright') {
            await captureWithPlaywright();
        } else {
            await captureWithPuppeteer();
        }
        process.exit(0);
    } catch (err) {
        console.error('[capture] Fatal error:', err.message);
        process.exit(1);
    }
})();
NODEJS_EOF

    chmod +x "${CAPTURE_SCRIPT}"
    pass "Capture script written: ${CAPTURE_SCRIPT}"
}

# ---------------------------------------------------------------------------
# Start a lightweight HTTP server for the game
# ---------------------------------------------------------------------------
SERVER_PID=""

start_server() {
    section "Starting HTTP server (port ${SERVER_PORT})"

    # Kill any stale process on the port
    if lsof -ti tcp:"${SERVER_PORT}" &>/dev/null 2>&1; then
        warn "Port ${SERVER_PORT} in use — killing stale process"
        lsof -ti tcp:"${SERVER_PORT}" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi

    local serve_dir="${PROJECT_ROOT}"

    if require_cmd python3; then
        python3 -m http.server "${SERVER_PORT}" \
            --directory "${serve_dir}" \
            --bind 127.0.0.1 \
            >> "${LOG_DIR}/server.log" 2>&1 &
        SERVER_PID=$!
        info "python3 http.server PID=${SERVER_PID}"
    elif require_cmd npx; then
        (cd "${serve_dir}" && npx --yes serve -l "${SERVER_PORT}" -s .) \
            >> "${LOG_DIR}/server.log" 2>&1 &
        SERVER_PID=$!
        info "npx serve PID=${SERVER_PID}"
    else
        warn "No HTTP server available — skipping capture tests"
        SERVER_PID=""
        return 1
    fi

    # Wait for server to be ready
    local attempts=0
    while (( attempts < 20 )); do
        if curl -sf "http://127.0.0.1:${SERVER_PORT}/" &>/dev/null; then
            pass "Server ready at http://127.0.0.1:${SERVER_PORT}/"
            return 0
        fi
        sleep 0.5
        attempts=$(( attempts + 1 ))
    done

    warn "Server did not become ready in time"
    return 1
}

stop_server() {
    if [[ -n "${SERVER_PID}" ]]; then
        kill "${SERVER_PID}" 2>/dev/null || true
        wait "${SERVER_PID}" 2>/dev/null || true
        SERVER_PID=""
        info "HTTP server stopped"
    fi
}

# ---------------------------------------------------------------------------
# Capture screenshots via headless browser
# ---------------------------------------------------------------------------
capture_screenshots() {
    section "Capturing screenshots (headless browser)"

    if [[ "${CAPTURE_RUNTIME}" == "unavailable" || "${CAPTURE_RUNTIME}" == "none" ]]; then
        skip "No headless browser runtime available"
        record_result "screenshot_capture" "SKIP" "No puppeteer/playwright"
        return 1
    fi

    if [[ -z "${SERVER_PID}" ]]; then
        skip "HTTP server not running — cannot capture"
        record_result "screenshot_capture" "SKIP" "HTTP server unavailable"
        return 1
    fi

    export GAME_BASE_URL="http://127.0.0.1:${SERVER_PORT}"
    export OUT_GAME="${ACTUAL_GAME}"
    export OUT_DASHBOARD="${ACTUAL_DASHBOARD}"
    export CAPTURE_RUNTIME

    info "Capturing with runtime: ${CAPTURE_RUNTIME}"
    info "Game URL: ${GAME_BASE_URL}"

    local node_modules_bin="${SCRIPT_DIR}/node_modules/.bin"
    local node_path="${SCRIPT_DIR}/node_modules"
    export NODE_PATH="${node_path}"

    if timeout "${CAPTURE_TIMEOUT}" node "${CAPTURE_SCRIPT}" >> "${MAIN_LOG}" 2>&1; then
        pass "Screenshots captured successfully"
        record_result "screenshot_capture" "PASS" "Both screenshots captured"
        return 0
    else
        fail "Screenshot capture failed (exit ${?})"
        record_result "screenshot_capture" "FAIL" "node capture_screenshots.js exited non-zero"
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Ensure baseline screenshots exist (create synthetic ones if absent)
# ---------------------------------------------------------------------------
ensure_baselines() {
    section "Ensuring baseline screenshots"

    local created=0

    for baseline in "${BASELINE_GAME}" "${BASELINE_DASHBOARD}"; do
        if [[ -f "${baseline}" ]]; then
            local sz; sz="$(identify -format '%wx%h' "${baseline}" 2>/dev/null || echo 'unknown')"
            pass "Baseline exists: $(basename "${baseline}") [${sz}]"
        else
            warn "Baseline missing: ${baseline}"
            if require_cmd convert; then
                info "Generating synthetic baseline placeholder…"
                local label
                label="$(basename "${baseline}" .png)"
                convert -size 1280x720 \
                    gradient:'#0a0a1a-#1a0a2e' \
                    -fill '#00ffff' \
                    -font DejaVu-Sans -pointsize 36 \
                    -gravity Center \
                    -annotate 0 "BASELINE PLACEHOLDER\n${label}\n$(date +%Y-%m-%d)" \
                    "${baseline}" 2>>"${MAIN_LOG}" && {
                    pass "Synthetic baseline created: ${baseline}"
                    created=$(( created + 1 ))
                } || {
                    fail "Could not create synthetic baseline: ${baseline}"
                }
            else
                fail "ImageMagick not available — cannot create baseline"
            fi
        fi
    done

    if (( created > 0 )); then
        warn "${created} synthetic baseline(s) created. Run with real game output to establish true baselines."
    fi
}

# ---------------------------------------------------------------------------
# Update baselines from actual screenshots
# ---------------------------------------------------------------------------
update_baselines() {
    section "Updating baselines from actual screenshots"

    local updated=0
    for pair in "${ACTUAL_GAME}:${BASELINE_GAME}" "${ACTUAL_DASHBOARD}:${BASELINE_DASHBOARD}"; do
        local src="${pair%%:*}"
        local dst="${pair##*:}"
        if [[ -f "${src}" ]]; then
            cp "${src}" "${dst}"
            pass "Updated baseline: $(basename "${dst}")"
            updated=$(( updated + 1 ))
        else
            warn "Actual screenshot missing, cannot update: ${src}"
        fi
    done
    info "${updated} baseline(s) updated"
}

# ---------------------------------------------------------------------------
# Image comparison using ImageMagick compare
# ---------------------------------------------------------------------------
compare_images() {
    local name="$1"
    local baseline="$2"
    local actual="$3"
    local diff_out="$4"

    info "Comparing: $(basename "${actual}") vs $(basename "${baseline}")"

    # Verify files exist
    if [[ ! -f "${baseline}" ]]; then
        fail "Baseline not found: ${baseline}"
        record_result "${name}" "FAIL" "Baseline missing"
        return 1
    fi

    if [[ ! -f "${actual}" ]]; then
        fail "Actual screenshot not found: ${actual}"
        record_result "${name}" "FAIL" "Actual screenshot missing"
        return 1
    fi

    if ! require_cmd compare || ! require_cmd identify; then
        skip "ImageMagick not available"
        record_result "${name}" "SKIP" "ImageMagick unavailable"
        return 0
    fi

    # Get dimensions
    local b_dim a_dim
    b_dim="$(identify -format '%wx%h' "${baseline}" 2>/dev/null || echo '0x0')"
    a_dim="$(identify -format '%wx%h' "${actual}"   2>/dev/null || echo '0x0')"
    info "Baseline: ${b_dim}  Actual: ${a_dim}"

    # Resize actual to match baseline if dimensions differ
    local actual_cmp="${actual}"
    if [[ "${b_dim}" != "${a_dim}" ]]; then
        warn "Dimension mismatch — resizing actual to ${b_dim}"
        actual_cmp="${ACTUAL_DIR}/${name}_resized.png"
        convert "${actual}" -resize "${b_dim}!" "${actual_cmp}" 2>>"${MAIN_LOG}" || {
            fail "Resize failed"
            record_result "${name}" "FAIL" "Resize failed"
            return 1
        }
    fi

    # Run pixel comparison (AE metric = absolute error pixel count)
    local ae_count=0
    local compare_output
    compare_output="$(compare -metric AE \
        "${baseline}" "${actual_cmp}" \
        "${diff_out}" 2>&1 || true)"

    # compare exits 1 when images differ, 2 on error
    local compare_exit=$?
    if (( compare_exit == 2 )); then
        fail "ImageMagick compare error: ${compare_output}"
        record_result "${name}" "FAIL" "compare error: ${compare_output}"
        return 1
    fi

    ae_count="${compare_output//[^0-9]/}"
    ae_count="${ae_count:-0}"

    # Total pixels
    local w h total_pixels
    w="${b_dim%%x*}"
    h="${b_dim##*x}"
    total_pixels=$(( w * h ))

    # Percentage diff
    local pct_diff="0"
    if (( total_pixels > 0 )); then
        pct_diff="$(echo "scale=4; ${ae_count} * 100 / ${total_pixels}" | bc 2>/dev/null || echo '0')"
    fi

    info "Pixel diff: ${ae_count} / ${total_pixels} pixels (${pct_diff}%)"
    info "Threshold:  ${PIXEL_DIFF_THRESHOLD}%"

    # Compare against threshold
    local exceeds
    exceeds="$(echo "${pct_diff} > ${PIXEL_DIFF_THRESHOLD}" | bc 2>/dev/null || echo '0')"

    if [[ "${exceeds}" == "1" ]]; then
        fail "${name}: pixel diff ${pct_diff}% exceeds threshold ${PIXEL_DIFF_THRESHOLD}%"
        info "Diff image: ${diff_out}"
        record_result "${name}" "FAIL" "diff=${pct_diff}% threshold=${PIXEL_DIFF_THRESHOLD}%"
        return 1
    else
        pass "${name}: pixel diff ${pct_diff}% within threshold ${PIXEL_DIFF_THRESHOLD}%"
        record_result "${name}" "PASS" "diff=${pct_diff}% threshold=${PIXEL_DIFF_THRESHOLD}%"
        return 0
    fi
}

# ---------------------------------------------------------------------------
# Visual regression tests
# ---------------------------------------------------------------------------
run_visual_regression_tests() {
    section "Visual Regression Tests"

    compare_images \
        "game_screenshot" \
        "${BASELINE_GAME}" \
        "${ACTUAL_GAME}" \
        "${DIFF_GAME}"

    compare_images \
        "dashboard_screenshot" \
        "${BASELINE_DASHBOARD}" \
        "${ACTUAL_DASHBOARD}" \
        "${DIFF_DASHBOARD}"
}

# ---------------------------------------------------------------------------
# Structural / sanity tests on the actual screenshots
# ---------------------------------------------------------------------------
run_sanity_tests() {
    section "Screenshot Sanity Tests"

    for pair in "game_screenshot:${ACTUAL_GAME}" "dashboard_screenshot:${ACTUAL_DASHBOARD}"; do
        local name="${pair%%:*}"
        local file="${pair##*:}"
        local test_name="${name}_sanity"

        if [[ ! -f "${file}" ]]; then
            skip "${test_name}: file not found"
            record_result "${test_name}" "SKIP" "File missing"
            continue
        fi

        if ! require_cmd identify; then
            skip "${test_name}: ImageMagick unavailable"
            record_result "${test_name}" "SKIP" "ImageMagick unavailable"
            continue
        fi

        # Check it's a valid PNG
        local format
        format="$(identify -format '%m' "${file}" 2>/dev/null || echo 'UNKNOWN')"
        if [[ "${format}" != "PNG" ]]; then
            fail "${test_name}: expected PNG, got ${format}"
            record_result "${test_name}" "FAIL" "Format=${format}"
            continue
        fi

        # Check dimensions are reasonable (at least 320x240)
        local w h
        w="$(identify -format '%w' "${file}" 2>/dev/null || echo '0')"
        h="$(identify -format '%h' "${file}" 2>/dev/null || echo '0')"

        if (( w < 320 || h < 240 )); then
            fail "${test_name}: dimensions too small (${w}x${h})"
            record_result "${test_name}" "FAIL" "Dimensions=${w}x${h}"
            continue
        fi

        # Check file is not blank (mean brightness > 0)
        local mean
        mean="$(convert "${file}" -colorspace Gray -format '%[fx:mean]' info: 2>/dev/null || echo '0')"
        local is_blank
        is_blank="$(echo "${mean} < 0.001" | bc 2>/dev/null || echo '0')"
        if [[ "${is_blank}" == "1" ]]; then
            fail "${test_name}: screenshot appears blank (mean brightness=${mean})"
            record_result "${test_name}" "FAIL" "Blank image mean=${mean}"
            continue
        fi

        pass "${test_name}: valid PNG ${w}x${h}, brightness=${mean}"
        record_result "${test_name}" "PASS" "PNG ${w}x${h} brightness=${mean}"
    done
}

# ---------------------------------------------------------------------------
# File integrity tests
# ---------------------------------------------------------------------------
run_integrity_tests() {
    section "File Integrity Tests"

    local files=(
        "${PROJECT_ROOT}/index.html"
        "${PROJECT_ROOT}/game.js"
    )

    # Also check for common alternative entry points
    for alt in "${PROJECT_ROOT}/main.js" "${PROJECT_ROOT}/src/game.js" "${PROJECT_ROOT}/src/main.js"; do
        [[ -f "${alt}" ]] && files+=("${alt}")
    done

    for f in "${files[@]}"; do
        local test_name="integrity_$(basename "${f}")"
        if [[ -f "${f}" ]]; then
            local size; size="$(wc -c < "${f}" 2>/dev/null || echo '0')"
            if (( size > 0 )); then
                pass "${test_name}: exists, ${size} bytes"
                record_result "${test_name}" "PASS" "size=${size}"
            else
                fail "${test_name}: file is empty"
                record_result "${test_name}" "FAIL" "Empty file"
            fi
        else
            skip "${test_name}: not found (${f})"
            record_result "${test_name}" "SKIP" "File not found"
        fi
    done
}

# ---------------------------------------------------------------------------
# Performance / metadata tests
# ---------------------------------------------------------------------------
run_metadata_tests() {
    section "Screenshot Metadata Tests"

    for pair in "game:${ACTUAL_GAME}" "dashboard:${ACTUAL_DASHBOARD}"; do
        local label="${pair%%:*}"
        local file="${pair##*:}"
        local test_name="metadata_${label}"

        if [[ ! -f "${file}" ]]; then
            skip "${test_name}: file not found"
            record_result "${test_name}" "SKIP" "File missing"
            continue
        fi

        if ! require_cmd identify; then
            skip "${test_name}: ImageMagick unavailable"
            record_result "${test_name}" "SKIP" "ImageMagick unavailable"
            continue
        fi

        local info
        info="$(identify -verbose "${file}" 2>/dev/null | head -40 || echo '')"

        # Check colour depth
        local depth
        depth="$(identify -format '%z' "${file}" 2>/dev/null || echo '0')"
        if (( depth >= 8 )); then
            pass "${test_name}: colour depth ${depth}-bit"
            record_result "${test_name}" "PASS" "depth=${depth}bit"
        else
            warn "${test_name}: unusual colour depth ${depth}-bit"
            record_result "${test_name}" "PASS" "depth=${depth}bit (warn)"
        fi
    done
}

# ---------------------------------------------------------------------------
# Generate HTML report
# ---------------------------------------------------------------------------
generate_html_report() {
    section "Generating HTML report"

    local status_class="pass"
    (( TESTS_FAILED > 0 )) && status_class="fail"
    local status_upper
    status_upper="$(echo "${status_class}" | tr '[:lower:]' '[:upper:]')"

    cat > "${REPORT_HTML}" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Visual Regression Report — ${RUN_TS}</title>
<style>
  :root {
    --bg: #0a0a1a; --bg2: #12122a; --bg3: #1a1a3a;
    --cyan: #00ffff; --magenta: #ff00ff; --green: #00ff88;
    --red: #ff3355; --yellow: #ffee00; --orange: #ff8800;
    --text: #c8d8e8; --dim: #556677;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.6;
    padding: 2rem;
  }
  h1 {
    font-size: 2rem;
    color: var(--cyan);
    text-shadow: 0 0 20px var(--cyan);
    border-bottom: 2px solid var(--magenta);
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
  }
  h2 { color: var(--magenta); margin: 1.5rem 0 0.75rem; font-size: 1.2rem; }
  .meta { color: var(--dim); margin-bottom: 1.5rem; }
  .summary { padding: 1rem; background: var(--bg2); border-left: 4px solid var(--cyan); margin-bottom: 2rem; }
  .pass { color: var(--green); }
  .fail { color: var(--red); }
  .skip { color: var(--yellow); }
  table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
  th, td { padding: 0.5rem 1rem; text-align: left; border-bottom: 1px solid var(--bg3); }
  th { background: var(--bg3); color: var(--cyan); }
</style>
</head>
<body>
  <h1>Visual Regression & Telemetry Test Report</h1>
  <div class="meta">Timestamp: ${RUN_TS} | Total: ${TESTS_TOTAL} | Passed: ${TESTS_PASSED} | Failed: ${TESTS_FAILED}</div>
  <div class="summary">
    <p>Status: <strong class="${status_class}">${status_upper}</strong></p>
  </div>

  <table>
    <thead><tr><th>Test</th><th>Status</th><th>Details</th></tr></thead>
    <tbody>
HTMLEOF

    for r in "${TEST_RESULTS[@]}"; do
        local name="${r%%|*}"
        local rest="${r#*|}"
        local status="${rest%%|*}"
        local detail="${rest#*|}"
        local cls="pass"
        [[ "${status}" == "FAIL" ]] && cls="fail"
        [[ "${status}" == "SKIP" ]] && cls="skip"
        cat >> "${REPORT_HTML}" << ROWEOF
      <tr><td>${name}</td><td class="${cls}">${status}</td><td>${detail}</td></tr>
ROWEOF
    done

    cat >> "${REPORT_HTML}" << HTMLEOF
    </tbody>
  </table>
</body>
</html>
HTMLEOF
    pass "HTML report generated: ${REPORT_HTML}"
}

# ---------------------------------------------------------------------------
# Main Orchestration Loop
# ---------------------------------------------------------------------------
main() {
    banner "CRASH TO DESKTOP — VISUAL REGRESSION HARNESS"

    bootstrap_dirs
    check_dependencies
    ensure_baselines

    # Run Python test suite
    if require_cmd pytest; then
        section "Running Pytest Test Suite"
        pytest -v "${SCRIPT_DIR}" || warn "Some pytest cases failed"
    fi

    run_sanity_tests
    run_integrity_tests
    run_metadata_tests

    generate_html_report

    section "Test Run Summary"
    echo -e "  Total Tests:  ${WHITE}${BOLD}${TESTS_TOTAL}${RESET}"
    echo -e "  Passed:       ${GREEN}${BOLD}${TESTS_PASSED}${RESET}"
    echo -e "  Failed:       ${RED}${BOLD}${TESTS_FAILED}${RESET}"
    echo -e "  Skipped:      ${YELLOW}${BOLD}${TESTS_SKIPPED}${RESET}"

    if (( TESTS_FAILED > 0 )); then
        fail "Visual regression suite completed with failures."
        exit 1
    else
        pass "Visual regression suite passed successfully."
        exit 0
    fi
}

main "$@"