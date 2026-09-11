#!/usr/bin/env python3
"""Ce qui transforme le site en application installable (Android, iPhone, bureau).

Trois pièces, et rien de plus :
  * un manifeste — le nom, la couleur et les icônes que le système affichera ;
  * des icônes PNG dessinées ici même (aucune dépendance : ni Pillow, ni fichier
    binaire à versionner, l'icône se régénère à chaque build) ;
  * un service worker — le seul moyen pour que l'enfant révise dans le train,
    sans réseau, avec les enregistrements déjà écoutés.

Toutes les URL sont relatives : le site est publié sous /courses-languages/ sur
GitHub Pages, un chemin absolu casserait tout.
"""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

ACCENT = (200, 69, 43)      # --accent du site
CREAM = (253, 250, 245)     # --bg du site

APP_NAME = "Les langues à la maison"
APP_SHORT = "Langues"


# --------------------------------------------------------------------------- #
# Icônes : un PNG écrit à la main, sans bibliothèque
# --------------------------------------------------------------------------- #
def _png(pixels: list[list[tuple[int, int, int]]]) -> bytes:
    """Encode une image RGB en PNG (filtre 0, une ligne = un octet 0 + les pixels)."""
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in pixels)
    size = len(pixels)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9))
            + chunk(b"IEND", b""))


def _rounded(x: float, y: float, x0: float, y0: float, x1: float, y1: float, r: float) -> bool:
    if not (x0 <= x <= x1 and y0 <= y <= y1):
        return False
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def _bubble(x: float, y: float) -> bool:
    """Une bulle de parole : le corps arrondi, plus la petite pointe en bas."""
    if _rounded(x, y, .20, .24, .80, .62, .13):
        return True
    # la pointe : un triangle sous le coin bas-gauche du corps
    if .30 <= x <= .46 and .62 <= y <= .78:
        return (y - .62) <= (.46 - x) * 1.0
    return False


def _dots(x: float, y: float) -> bool:
    for cx in (.35, .50, .65):
        if (x - cx) ** 2 + (y - .43) ** 2 <= .052 ** 2:
            return True
    return False


def icon_png(size: int, maskable: bool = False) -> bytes:
    """L'icône du site : bulle de parole crème sur fond chaud.

    « maskable » : Android recadre l'icône (cercle, goutte…). On garde donc le
    dessin dans les 80 % centraux, sinon la bulle se fait rogner.
    """
    ss = 3                      # anticrénelage : on échantillonne 3×3 par pixel
    scale = .78 if maskable else 1.0
    rows = []
    for py in range(size):
        row = []
        for px in range(size):
            acc = [0, 0, 0]
            for sy in range(ss):
                for sx in range(ss):
                    u = (px + (sx + .5) / ss) / size
                    v = (py + (sy + .5) / ss) / size
                    # coordonnées du dessin, recentrées si l'icône est recadrable
                    du = (u - .5) / scale + .5
                    dv = (v - .5) / scale + .5
                    if maskable:
                        col = ACCENT          # le fond couvre tout le carré
                    else:
                        col = ACCENT if _rounded(u, v, .02, .02, .98, .98, .22) else CREAM
                    if _bubble(du, dv):
                        col = CREAM if col == ACCENT else ACCENT
                        if _dots(du, dv):
                            col = ACCENT if col == CREAM else CREAM
                    for i in range(3):
                        acc[i] += col[i]
            row.append(tuple(c // (ss * ss) for c in acc))
        rows.append(row)
    return _png(rows)


ICONS = [("icons/icon-192.png", 192, False),
         ("icons/icon-512.png", 512, False),
         ("icons/icon-maskable-512.png", 512, True),
         ("icons/apple-touch-icon.png", 180, False)]


# --------------------------------------------------------------------------- #
# Manifeste
# --------------------------------------------------------------------------- #
def manifest(langs: list[dict]) -> str:
    shortcuts = [{
        "name": c["name_fr"],
        "short_name": c["name"],
        "url": f'./{c["code"]}/index.html',
    } for c in langs]
    data = {
        "name": APP_NAME,
        "short_name": APP_SHORT,
        "description": "Un programme de langue pour enfants : vocabulaire, dialogues "
                       "et vraies voix, utilisable hors connexion.",
        "lang": "fr",
        "start_url": "./index.html",
        "scope": "./",
        "display": "standalone",
        "orientation": "any",
        "background_color": "#fdfaf5",
        "theme_color": "#c8452b",
        "icons": [
            {"src": "./icons/icon-192.png", "sizes": "192x192", "type": "image/png",
             "purpose": "any"},
            {"src": "./icons/icon-512.png", "sizes": "512x512", "type": "image/png",
             "purpose": "any"},
            {"src": "./icons/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": shortcuts,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def head_tags(depth: int) -> str:
    """Ce qui va dans <head> pour qu'Android et iOS proposent l'installation."""
    up = "../" * depth
    return (
        f'<link rel="manifest" href="{up}manifest.webmanifest">\n'
        f'<link rel="apple-touch-icon" href="{up}icons/apple-touch-icon.png">\n'
        '<meta name="theme-color" content="#c8452b" media="(prefers-color-scheme: light)">\n'
        '<meta name="theme-color" content="#181614" media="(prefers-color-scheme: dark)">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        # iOS ignore encore le manifeste : ces deux balises sont ce qui rend
        # « Sur l'écran d'accueil » plein écran et lisible sur iPhone.
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
        f'<meta name="apple-mobile-web-app-title" content="{APP_SHORT}">'
    )


def register_js(depth: int) -> str:
    """L'enregistrement du service worker, silencieux si le navigateur n'en veut pas."""
    up = "../" * depth
    return (
        "if('serviceWorker' in navigator && location.protocol!=='file:'){"
        f"window.addEventListener('load',function(){{navigator.serviceWorker.register('{up}sw.js')"
        ".catch(function(){});});}"
    )


# --------------------------------------------------------------------------- #
# Service worker
# --------------------------------------------------------------------------- #
SW_TEMPLATE = """/* Service worker : le site doit rester utilisable sans réseau.

   Deux régimes, parce que les besoins diffèrent :
     * les pages HTML → réseau d'abord, cache en secours. Une révision corrigée
       doit arriver ; si la connexion manque, la version en cache s'affiche.
     * tout le reste (icônes, enregistrements .mp3, exports) → cache d'abord.
       Un mot déjà écouté ne doit plus jamais dépendre du réseau.

   VERSION change à chaque build dont le contenu change : les anciens caches
   sont alors supprimés, sans quoi l'enfant garderait une leçon périmée. */
var VERSION = '%(version)s';
var SHELL = 'shell-' + VERSION;
var RUNTIME = 'runtime-' + VERSION;
var PRECACHE = %(precache)s;

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(SHELL).then(function (c) {
    /* addAll() échoue en bloc dès qu'un fichier manque : on ajoute un par un
       pour qu'une seule ressource absente ne prive pas de tout le hors-ligne. */
    return Promise.all(PRECACHE.map(function (u) { return c.add(u).catch(function () {}); }));
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.map(function (k) {
      if (k !== SHELL && k !== RUNTIME) { return caches.delete(k); }
    }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') { return; }
  var url = new URL(req.url);
  if (url.origin !== location.origin) { return; }

  var wantsPage = req.mode === 'navigate' ||
    (req.headers.get('accept') || '').indexOf('text/html') !== -1;

  if (wantsPage) {
    e.respondWith(fetch(req).then(function (res) {
      var copy = res.clone();
      caches.open(RUNTIME).then(function (c) { c.put(req, copy); });
      return res;
    }).catch(function () {
      return caches.match(req).then(function (hit) {
        return hit || caches.match(%(home)s);
      });
    }));
    return;
  }

  e.respondWith(caches.match(req).then(function (hit) {
    return hit || fetch(req).then(function (res) {
      if (res.ok && res.type === 'basic') {
        var copy = res.clone();
        caches.open(RUNTIME).then(function (c) { c.put(req, copy); });
      }
      return res;
    });
  }));
});
"""


def service_worker(site: Path, version: str) -> str:
    """Le service worker, avec la liste des pages à mettre en cache dès l'installation.

    Les .mp3 ne sont PAS préchargés : il y en a plus d'un millier, soit des
    dizaines de mégaoctets imposés à l'installation. Ils entrent dans le cache
    au fil de l'écoute, ce qui suffit pour réviser ensuite sans réseau.
    """
    files = sorted(
        "./" + p.relative_to(site).as_posix()
        for p in site.rglob("*")
        if p.is_file() and p.suffix in {".html", ".png", ".webmanifest"}
        and "print" not in p.relative_to(site).parts
    )
    return SW_TEMPLATE % {
        "version": version,
        "precache": json.dumps(files, indent=2),
        "home": json.dumps("./index.html"),
    }


def write_all(site: Path, langs: list[dict], version: str) -> int:
    (site / "icons").mkdir(parents=True, exist_ok=True)
    for name, size, maskable in ICONS:
        (site / name).write_bytes(icon_png(size, maskable))
    (site / "manifest.webmanifest").write_text(manifest(langs), encoding="utf-8")
    # après les icônes et le manifeste : ils doivent figurer dans le précache.
    (site / "sw.js").write_text(service_worker(site, version), encoding="utf-8")
    return len(ICONS)
