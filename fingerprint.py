"""
Browser fingerprint randomization.
Each session gets unique device characteristics to avoid detection.
"""

import random


# Common Korean screen resolutions
RESOLUTIONS = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
    (1280, 720), (1600, 900), (2560, 1440), (1280, 800),
]

# Real-world User-Agent strings (Chrome on Windows, updated regularly)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

# Korean timezone and locale
TIMEZONES = ["Asia/Seoul"]
LOCALES = ["ko-KR"]

# WebGL vendors and renderers (common combinations)
WEBGL_CONFIGS = [
    {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0)"},
    {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"},
    {"vendor": "Google Inc. (AMD)", "renderer": "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0)"},
    {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)"},
    {"vendor": "Google Inc. (Intel)", "renderer": "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0)"},
    {"vendor": "Google Inc. (NVIDIA)", "renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0)"},
]


def generate_fingerprint() -> dict:
    """Generate a unique, realistic browser fingerprint."""
    resolution = random.choice(RESOLUTIONS)
    webgl = random.choice(WEBGL_CONFIGS)

    return {
        "user_agent": random.choice(USER_AGENTS),
        "viewport": {
            "width": resolution[0],
            "height": resolution[1],
        },
        "screen": {
            "width": resolution[0],
            "height": resolution[1],
        },
        "timezone": random.choice(TIMEZONES),
        "locale": random.choice(LOCALES),
        "webgl_vendor": webgl["vendor"],
        "webgl_renderer": webgl["renderer"],
        "device_memory": random.choice([4, 8, 16, 32]),
        "hardware_concurrency": random.choice([4, 6, 8, 12, 16]),
        "color_depth": 24,
        "pixel_ratio": random.choice([1.0, 1.25, 1.5]),
        "platform": "Win32",
        "languages": ["ko-KR", "ko", "en-US", "en"],
        "do_not_track": random.choice([None, "1"]),
        "max_touch_points": 0,  # Desktop
    }


STEALTH_SCRIPTS = """
// Override navigator properties
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        { name: 'Native Client', filename: 'internal-nacl-plugin' },
    ]
});

// Override permissions query
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);

// Chrome runtime mock
window.chrome = {
    runtime: { id: undefined },
    loadTimes: function() {},
    csi: function() {},
};

// Override iframe contentWindow detection
const originalAttachShadow = Element.prototype.attachShadow;
Element.prototype.attachShadow = function(init) {
    return originalAttachShadow.call(this, { ...init, mode: 'open' });
};
"""


def get_stealth_script(fingerprint: dict) -> str:
    """Generate full stealth injection script with fingerprint overrides."""
    fp = fingerprint
    return STEALTH_SCRIPTS + f"""
// Device fingerprint overrides
Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {fp['device_memory']} }});
Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {fp['hardware_concurrency']} }});
Object.defineProperty(navigator, 'platform', {{ get: () => '{fp['platform']}' }});
Object.defineProperty(navigator, 'languages', {{ get: () => {fp['languages']} }});
Object.defineProperty(navigator, 'maxTouchPoints', {{ get: () => {fp['max_touch_points']} }});
Object.defineProperty(screen, 'colorDepth', {{ get: () => {fp['color_depth']} }});
Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {fp['pixel_ratio']} }});

// WebGL fingerprint override
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(param) {{
    if (param === 37445) return '{fp['webgl_vendor']}';
    if (param === 37446) return '{fp['webgl_renderer']}';
    return getParameter.call(this, param);
}};
const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
WebGL2RenderingContext.prototype.getParameter = function(param) {{
    if (param === 37445) return '{fp['webgl_vendor']}';
    if (param === 37446) return '{fp['webgl_renderer']}';
    return getParameter2.call(this, param);
}};
"""
