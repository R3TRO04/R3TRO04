#!/usr/bin/env python3
"""Regenerate the generated SVG assets for this profile README.

The icon panel, badges, tagline and section headers are generated rather than
hand-written: the panel alone nests 35 logos and is far too large to edit by
hand. To change the tech stack, edit ROWS below and re-run this script.

    pip install fonttools brotli pillow
    python3 tools/build_assets.py

Logo artwork is downloaded from devicon and simple-icons at build time and
cached in tools/.cache, so no third-party art is committed. banner.svg and
footer.svg are hand-written and are not touched by this script.
"""
import base64, io, os, re, subprocess, sys, urllib.request
import xml.dom.minidom
from PIL import Image, ImageEnhance

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
os.makedirs(CACHE, exist_ok=True)

DEVICON = "https://raw.githubusercontent.com/devicons/devicon/master/icons"
SIMPLE  = "https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons"
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/pressstart2p/PressStart2P-Regular.ttf"
GLYPHS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 -.:?!&<>/@,'+#"

DEV_FILES = {
    "angular": "angular/angular-original.svg", "typescript": "typescript/typescript-original.svg",
    "javascript": "javascript/javascript-original.svg", "html5": "html5/html5-original.svg",
    "css3": "css3/css3-original.svg", "sass": "sass/sass-original.svg",
    "kotlin": "kotlin/kotlin-original.svg", "ktor": "ktor/ktor-original.svg",
    "java": "java/java-original.svg", "spring": "spring/spring-original.svg",
    "php": "php/php-original.svg", "nodejs": "nodejs/nodejs-original.svg",
    "junit": "junit/junit-original.svg", "mongodb": "mongodb/mongodb-original.svg",
    "redis": "redis/redis-original.svg", "docker": "docker/docker-original.svg",
    "kubernetes": "kubernetes/kubernetes-original.svg", "gitlab": "gitlab/gitlab-original.svg",
    "googlecloud": "googlecloud/googlecloud-original.svg", "gradle": "gradle/gradle-original.svg",
    "maven": "maven/maven-original.svg", "postman": "postman/postman-original.svg",
    "npm": "npm/npm-original-wordmark.svg", "pnpm": "pnpm/pnpm-original.svg",
    "bun": "bun/bun-original.svg", "deno": "denojs/denojs-original.svg",
    "intellij": "intellij/intellij-original.svg", "swift": "swift/swift-original.svg",
}
# Logos whose own brand colours are too dark to read on a dark tile are taken
# from simple-icons instead and recoloured to a legible tint.
SI_FILES = {"mysql": "mysql", "gnubash": "gnubash", "jest": "jest",
            "postgresql": "postgresql", "htmx": "htmx"}
MOCKITO_PNG = "https://raw.githubusercontent.com/mockito/mockito/release/3.x/src/javadoc/org/mockito/logo.png"


def _get(url, path):
    if not os.path.exists(path):
        with urllib.request.urlopen(url, timeout=60) as r, open(path, "wb") as f:
            f.write(r.read())
    return path


def _font():
    """Download Press Start 2P and subset it to the glyphs actually used."""
    ttf = _get(FONT_URL, os.path.join(CACHE, "PressStart2P.ttf"))
    woff2 = os.path.join(CACHE, "subset.woff2")
    if not os.path.exists(woff2):
        subprocess.run([sys.executable, "-m", "fontTools.subset", ttf,
                        f"--text={GLYPHS}", "--flavor=woff2",
                        f"--output-file={woff2}"], check=True)
    return base64.b64encode(open(woff2, "rb").read()).decode()


def fetch_art():
    for name, rel in DEV_FILES.items():
        _get(f"{DEVICON}/{rel}", os.path.join(CACHE, f"{name}.svg"))
    for name, slug in SI_FILES.items():
        _get(f"{SIMPLE}/{slug}.svg", os.path.join(CACHE, f"si-{name}.svg"))
    _get(MOCKITO_PNG, os.path.join(CACHE, "mockito.png"))


fetch_art()


FONT = _font()
FF = ("@font-face { font-family:'PS2P'; src:url(data:font/woff2;base64,%s) format('woff2'); }"
      " text { font-family:'PS2P',monospace; }" % FONT)
PINK, CYAN, VIOLET, YELLOW = "#ff2fb3", "#2de2e6", "#7733ff", "#ffd319"
BG_DEEP, BG_TILE, INK = "#0d0221", "#1b0b33", "#e8e6f0"
XMLNS = 'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"'

def _ns_ids(body, key):
    """Namespace all ids/references so nested logos can't collide."""
    ids = set(re.findall(r'\bid="([^"]+)"', body))
    for i in sorted(ids, key=len, reverse=True):
        new = f"{key}-{i}"
        body = re.sub(r'\bid="%s"' % re.escape(i), f'id="{new}"', body)
        body = body.replace(f'url(#{i})', f'url(#{new})')
        body = re.sub(r'((?:xlink:)?href)="#%s"' % re.escape(i), r'\1="#%s"' % new, body)
    return body

def inner(src, key, bx, by, bw, bh, wrap_fill=None, recolor=None):
    src = re.sub(r'<\?xml[^>]*\?>', '', src)
    src = re.sub(r'<!DOCTYPE[^>]*>', '', src, flags=re.I)
    src = re.sub(r'<!--.*?-->', '', src, flags=re.S).strip()
    vb = re.search(r'viewBox="([^"]+)"', src)
    if vb:
        nums = [float(v) for v in vb.group(1).replace(',', ' ').split()]
        vw, vh, vbs = nums[2], nums[3], vb.group(1)
    else:
        vw = float(re.search(r'width="([\d.]+)', src).group(1))
        vh = float(re.search(r'height="([\d.]+)', src).group(1))
        vbs = f"0 0 {vw} {vh}"
    body = re.sub(r'^<svg[^>]*>', '', src, count=1)
    body = re.sub(r'</svg>\s*$', '', body)
    body = _ns_ids(body, key)
    if recolor:
        for a, b in recolor.items(): body = body.replace(a, b)
    if wrap_fill: body = f'<g fill="{wrap_fill}">{body}</g>'
    s = min(bw / vw, bh / vh)
    w, h = vw * s, vh * s
    return (f'<svg x="{bx+(bw-w)/2:.1f}" y="{by+(bh-h)/2:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'viewBox="{vbs}">{body}</svg>')

def png_img(path, key, bx, by, bw, bh, crop=None, bright=None):
    im = Image.open(path).convert("RGBA")
    im = im.crop(im.getbbox())
    if crop: im = im.crop(crop)
    if bright: im = ImageEnhance.Brightness(im).enhance(bright)
    buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    s = min(bw / im.width, bh / im.height)
    w, h = im.width * s, im.height * s
    return (f'<image href="data:image/png;base64,{b64}" x="{bx+(bw-w)/2:.1f}" '
            f'y="{by+(bh-h)/2:.1f}" width="{w:.1f}" height="{h:.1f}"/>')



ICONS = f"{REPO}/icons"

gt = open(f"{ICONS}/gleam.svg").read()
gleam_raw = re.search(r'(<svg x=.*</svg>)\s*</svg>\s*$', gt, re.S).group(1)
gleam_raw = re.sub(r'^<svg[^>]*?viewBox="([^"]+)"[^>]*>', r'<svg viewBox="\1">', gleam_raw)

def dev(n, **kw): return ("svg", open(f"{CACHE}/{n}.svg").read(), kw)
def si(n, colour):
    s = open(f"{CACHE}/si-{n}.svg").read().replace("<path ", f'<path fill="{colour}" ')
    return ("svg", s, {})
ART = {
 "angular":dev("angular"),"typescript":dev("typescript"),"javascript":dev("javascript"),
 "html5":dev("html5"),"css3":dev("css3"),"sass":dev("sass"),"jest":si("jest","#E4536C"),
 "htmx":("svg", open(f"{CACHE}/si-htmx.svg").read().replace('<path ','<path fill="#ffffff" '), {}),
 "kotlin":dev("kotlin"),"ktor":dev("ktor"),"java":dev("java"),"spring":dev("spring"),
 "php":dev("php"),"nodejs":dev("nodejs"),"junit":dev("junit"),
 "mockito":("png",f"{CACHE}/mockito.png",{"crop":(0,0,329,133),"bright":1.5}),
 "mysql":si("mysql","#5B96C8"),"postgresql":si("postgresql","#6D9FE8"),"mongodb":dev("mongodb"),
 "redis":dev("redis"),"docker":dev("docker"),"kubernetes":dev("kubernetes"),
 "bash":si("gnubash","#6BD442"),"gitlab":dev("gitlab"),"googlecloud":dev("googlecloud"),
 "gradle":dev("gradle",wrap_fill="#ffffff",recolor={"#02303a":"#ffffff","#02303A":"#ffffff"}),
 "maven":dev("maven"),"postman":dev("postman"),"npm":dev("npm"),"pnpm":dev("pnpm"),
 "bun":dev("bun"),"deno":dev("deno",wrap_fill="#ffffff"),"intellij":dev("intellij"),
 "apidog":("svg", open(f"{ICONS}/apidog-seeklogo.svg").read(), {}),
 "swift":dev("swift"),"gleam":("svg", gleam_raw, {}),
}

WIDE = {"mockito", "npm"}
def tile(key, x, y, size=72):
    kind, data, kw = ART[key]
    pad = size*0.19
    px = size*0.09 if key in WIDE else pad
    box = (x+px, y+pad, size-2*px, size-2*pad)
    art = png_img(data, key, *box, **kw) if kind=="png" else inner(data, key, *box, **kw)
    return (f'<g><rect x="{x}" y="{y}" width="{size}" height="{size}" rx="{size*0.22:.0f}" '
            f'fill="{BG_TILE}" stroke="{PINK}" stroke-opacity="0.22" stroke-width="1.5"/>{art}</g>')

ROWS = [
 ("STAGE 1","FRONTEND",["angular","typescript","javascript","html5","css3","sass","jest","htmx"]),
 ("STAGE 2","BACKEND",["kotlin","ktor","java","spring","php","nodejs","junit","mockito"]),
 ("STAGE 3","DATABASE & DEVOPS",["mysql","postgresql","mongodb","redis","docker","kubernetes","bash","gitlab","googlecloud"]),
 ("STAGE 4","TOOLS",["gradle","maven","postman","npm","pnpm","bun","deno","intellij","apidog"]),
 ("BONUS","CURRENTLY EXPLORING",["swift","gleam"]),
]
W,PAD,TS,GAP,STRIDE,RH = 820,28,72,14,114,94
H = 24 + len(ROWS)*RH + (len(ROWS)-1)*(STRIDE-RH) + 24

parts=[]
for i,(pre,title,keys) in enumerate(ROWS):
    top = 24 + i*STRIDE
    parts.append(f'<text x="{PAD}" y="{top+12}" font-size="11" fill="{PINK}">{pre}'
                 f'<tspan fill="{CYAN}"> - {title.replace("&","&amp;")}</tspan></text>')
    for j,k in enumerate(keys):
        parts.append(tile(k, PAD + j*(TS+GAP), top+22, TS))

panel = f'''<svg {XMLNS} width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <style>{FF}</style>
    <pattern id="pscan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1.4" fill="#000" opacity="0.5"/></pattern>
    <clipPath id="pcard"><rect width="{W}" height="{H}" rx="24"/></clipPath>
    <linearGradient id="pbg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#12032a"/><stop offset="1" stop-color="{BG_DEEP}"/>
    </linearGradient>
  </defs>
  <g clip-path="url(#pcard)">
    <rect width="{W}" height="{H}" fill="url(#pbg)"/>
    {chr(10).join("    "+p for p in parts)}
    <rect width="{W}" height="{H}" fill="url(#pscan)" opacity="0.13"/>
    <rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="23" fill="none" stroke="{PINK}" stroke-opacity="0.3" stroke-width="1.5"/>
  </g>
</svg>'''
open(f"{ICONS}/panel-stack.svg","w").write(panel)

xml.dom.minidom.parseString(panel)
print("panel OK:", H, "tall,", len(panel)//1024, "KB")



ICONS = f"{REPO}/icons"
# Violet reads on both GitHub light and dark backgrounds. A prefers-color-scheme
# query is not used here: an SVG in an <img> follows the OS theme, not the page
# theme, so it would show cyan-on-white for a dark-OS visitor browsing in light mode.
THEME = f".t {{ fill:{VIOLET}; }}"

def save(name, svg):
    xml.dom.minidom.parseString(svg)
    open(f"{ICONS}/{name}", "w").write(svg)

# ---------- section headers ----------
def header(text, out, size=16):
    adv = size
    x_title = 3 * adv
    x_cur = x_title + len(text) * adv + adv * 0.35
    w = int(x_cur + adv * 0.62 + 4)
    h = size + 12
    base = size + 3
    save(out, f'''<svg {XMLNS} width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <style>{FF} {THEME}</style>
  <text x="0" y="{base}" font-size="{size}" fill="{PINK}">&gt;&gt;</text>
  <text x="{x_title}" y="{base}" font-size="{size}" class="t">{text}</text>
  <rect x="{x_cur:.0f}" y="{base-size+2}" width="{adv*0.62:.0f}" height="{size-1}" fill="{PINK}">
    <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1.2s" repeatCount="indefinite"/>
  </rect>
</svg>''')

header("CHOOSE YOUR WEAPON", "h-stack.svg")
header("MULTIPLAYER MODE", "h-connect.svg")

# ---------- badges ----------
def badge(left, right, accent, out, size=9):
    adv, padx, h = size, 11, 32
    lw = padx * 2 + len(left) * adv
    rw = padx * 2 + len(right) * adv
    w = lw + rw
    base = h / 2 + size / 2 - 1
    save(out, f'''<svg {XMLNS} width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <style>{FF}</style>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="7"/></clipPath>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="#12032a"/>
    <rect width="{lw}" height="{h}" fill="{accent}"/>
    <text x="{padx}" y="{base:.0f}" font-size="{size}" fill="{BG_DEEP}">{left}</text>
    <text x="{lw + padx}" y="{base:.0f}" font-size="{size}" fill="{INK}">{right}</text>
  </g>
  <rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="6.25" fill="none" stroke="{accent}" stroke-opacity="0.55" stroke-width="1.5"/>
</svg>''')

badge("TWINFORMATICS", "WORKING",       CYAN,   "b-twinformatics.svg")
badge("KOTLIN",        "MASTERING",     PINK,   "b-kotlin.svg")
badge("JAVA",          "MASTERING",     PINK,   "b-java.svg")
badge("LINKEDIN",      "NICO BERANEK",  CYAN,   "b-linkedin.svg")
badge("EMAIL",         "NICO@JUBE.AT",  YELLOW, "b-email.svg")
badge("DISCORD",       "R3T.RO",        VIOLET, "b-discord.svg")

# ---------- typing tagline (self-hosted, same font as everything else) ----------
LINES = ["CRAFTING BACKENDS WITH KOTLIN & KTOR",
         "BUILDING UIS WITH ANGULAR & HTMX",
         "FUELED BY ENERGY DRINKS"]
SIZE, W, H = 14, 820, 54
ADV, CX = SIZE, W / 2
PER = 4.5
TOTAL = PER * len(LINES)
TYPE_FRAC = 0.45

groups = []
for i, ln in enumerate(LINES):
    esc = ln.replace("&", "&amp;")
    n = len(ln)
    x0 = CX - n * ADV / 2
    t0 = i * PER
    step = PER * TYPE_FRAC / n
    kt, wv, xv = [0.0], [0], [x0]
    kt.append(t0 / TOTAL); wv.append(0); xv.append(x0)
    for c in range(1, n + 1):
        kt.append((t0 + c * step) / TOTAL); wv.append(c * ADV); xv.append(x0 + c * ADV)
    kt.append((t0 + PER) / TOTAL); wv.append(0); xv.append(x0)
    if kt[-1] < 1: kt.append(1.0); wv.append(0); xv.append(x0)
    ktj = ";".join(f"{v:.5f}" for v in kt)
    opac = f'0;1;0' if i else '1;0'
    okt  = (f'0;{t0/TOTAL:.5f};{(t0+PER)/TOTAL:.5f}' if i else f'0;{PER/TOTAL:.5f}')
    if not okt.endswith("1"): okt += ";1"; opac += ";0"
    groups.append(f'''  <g opacity="{1 if i==0 else 0}">
    <animate attributeName="opacity" values="{opac}" keyTimes="{okt}" calcMode="discrete" dur="{TOTAL}s" repeatCount="indefinite"/>
    <clipPath id="clip{i}"><rect x="{x0:.1f}" y="0" height="{H}" width="0">
      <animate attributeName="width" values="{';'.join(str(v) for v in wv)}" keyTimes="{ktj}" calcMode="discrete" dur="{TOTAL}s" repeatCount="indefinite"/>
    </rect></clipPath>
    <text x="{x0:.1f}" y="{H/2 + SIZE/2 - 2:.0f}" font-size="{SIZE}" class="t" clip-path="url(#clip{i})">{esc}</text>
    <rect y="{H/2 - SIZE/2 - 3:.0f}" width="{ADV*0.62:.0f}" height="{SIZE+2}" fill="{PINK}" x="{x0:.1f}">
      <animate attributeName="x" values="{';'.join(f'{v:.1f}' for v in xv)}" keyTimes="{ktj}" calcMode="discrete" dur="{TOTAL}s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite"/>
    </rect>
  </g>''')

save("tagline.svg", f'''<svg {XMLNS} width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>{FF} {THEME}</style>
{chr(10).join(groups)}
</svg>''')
print("headers, 6 badges, tagline written")
