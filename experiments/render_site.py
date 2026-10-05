"""Render the built site with the system Chrome: review screenshots, share images and the film.

Usage (after `npm run build` in site/):
    uv run python experiments/render_site.py review   # screenshots of every beat, desktop and phone, into .render/
    uv run python experiments/render_site.py pages    # full-page screenshots of the tracker pages
    uv run python experiments/render_site.py film     # share/is-it-alpha-yet.mp4, rendered frame by frame
    uv run python experiments/render_site.py share    # share/og.png and the thread images
"""

from __future__ import annotations

import argparse
import contextlib
import subprocess
import time
import urllib.request

from playwright.sync_api import Browser, Page, sync_playwright

from lab.data import REPO_ROOT

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Needed for Chrome to start inside this machine's sandbox; harmless elsewhere.
CHROME_ARGS = ["--no-sandbox", "--disable-gpu-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
               "--no-proxy-server", "--hide-scrollbars"]
BASE = "http://127.0.0.1:4173"
SITE = REPO_ROOT / "site"
RENDER = REPO_ROOT / ".render"
NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def reachable() -> bool:
    try:
        NO_PROXY.open(BASE, timeout=2)
        return True
    except OSError:
        return False


@contextlib.contextmanager
def preview_server():
    if reachable():
        yield
        return
    proc = subprocess.Popen(["npx", "--offline", "vite", "preview", "--port", "4173", "--strictPort", "--host", "127.0.0.1"],
                            cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            if reachable():
                break
            time.sleep(0.5)
        yield
    finally:
        proc.terminate()


@contextlib.contextmanager
def chrome():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, headless=True, args=CHROME_ARGS)
        try:
            yield browser
        finally:
            browser.close()


def open_page(browser: Browser, path: str, width: int, height: int, reduced_motion: bool = False, scale: float = 1) -> Page:
    context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale,
                                  reduced_motion="reduce" if reduced_motion else "no-preference")
    page = context.new_page()
    page.goto(f"{BASE}{path}", wait_until="networkidle")
    return page


def scroll_to_beat(page: Page, beat: str, progress: float) -> None:
    page.evaluate(
        """([id, p]) => {
            const el = document.getElementById(id);
            const span = Math.max(el.offsetHeight - window.innerHeight, 0);
            window.scrollTo(0, el.offsetTop + p * span);
        }""",
        [beat, progress],
    )
    page.wait_for_timeout(350)


def review() -> None:
    RENDER.mkdir(exist_ok=True)
    desktop = [("pitch", 0.02), ("pitch", 0.5), ("pitch", 0.95), ("peek", 0.06), ("peek", 0.95), ("fees", 0.95),
               ("all-fees", 0.95), ("hindsight", 0.95), ("luck", 0.95), ("hold", 0.95), ("ai", 0.95),
               ("feed", 0), ("spot", 0), ("verdict", 0)]
    phone = [("pitch", 0.95), ("peek", 0.95), ("fees", 0.95), ("all-fees", 0.95), ("luck", 0.95), ("ai", 0.95), ("verdict", 0)]
    with preview_server(), chrome() as browser:
        for name, (w, h), beats in [("desktop", (1280, 800), desktop), ("phone", (390, 844), phone)]:
            page = open_page(browser, "/", w, h, scale=1 if name == "desktop" else 2)
            for beat, p in beats:
                scroll_to_beat(page, beat, p)
                page.screenshot(path=str(RENDER / f"{name}-{beat}-{int(p * 100):02d}.png"))
            page.context.close()
    print(f"Screenshots in {RENDER}")


def pages() -> None:
    """Full-page screenshots of the tracker pages, desktop and phone."""
    import json

    RENDER.mkdir(exist_ok=True)
    site = json.loads((SITE / "src" / "data" / "site.json").read_text())
    paths = ["/claims", "/live", "/method"] + [f"/claims/{c['slug']}" for c in site["claims"]]
    with preview_server(), chrome() as browser:
        for name, (w, h) in [("desktop", (1280, 900)), ("phone", (390, 844))]:
            for path in paths:
                page = open_page(browser, path, w, h, scale=1)
                page.wait_for_timeout(300)
                page.screenshot(path=str(RENDER / f"page-{name}{path.replace('/', '-')}.png"), full_page=True)
                page.context.close()
    print(f"Page screenshots in {RENDER}")


FILM_SIZE = (1080, 1350)
SHARE = REPO_ROOT / "share"


def film_page(browser: Browser) -> tuple[Page, float]:
    page = open_page(browser, "/?film=1&controlled=1", *FILM_SIZE)
    page.wait_for_function("window.__filmDuration > 0")
    return page, float(page.evaluate("window.__filmDuration"))


def seek(page: Page, ms: float) -> None:
    page.evaluate("ms => window.__filmSeek(ms)", ms)
    page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")


def film_frames_at(seconds: list[float]) -> None:
    """A few frames of the film, for checking the layout before a full render."""
    RENDER.mkdir(exist_ok=True)
    with preview_server(), chrome() as browser:
        page, _ = film_page(browser)
        for s in seconds:
            seek(page, s * 1000)
            page.screenshot(path=str(RENDER / f"film-{s:05.1f}s.png"))
    print(f"Test frames in {RENDER}")


def film(fps: int = 30) -> None:
    """Render the film frame by frame (deterministic, no dropped frames), then encode an H.264 MP4 for X."""
    frames_dir = RENDER / "film"
    if frames_dir.exists():
        for f in frames_dir.glob("*.png"):
            f.unlink()
    frames_dir.mkdir(parents=True, exist_ok=True)
    with preview_server(), chrome() as browser:
        page, duration = film_page(browser)
        count = int(duration / 1000 * fps) + 1
        for k in range(count):
            seek(page, k * 1000 / fps)
            page.screenshot(path=str(frames_dir / f"frame_{k:05d}.png"))
            if k % (fps * 5) == 0:
                print(f"  {k / fps:4.0f}s of {duration / 1000:.0f}s", flush=True)
    SHARE.mkdir(exist_ok=True)
    out = SHARE / "is-it-alpha-yet.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames_dir / "frame_%05d.png"),
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "slow", "-movflags", "+faststart", str(out)],
        check=True,
    )
    print(f"Wrote {out.relative_to(REPO_ROOT)} ({out.stat().st_size / 1e6:.1f} MB, {duration / 1000:.0f}s at {fps} fps)")


# Thread images, in posting order. The pitch has no still of its own: the hype is only ever shown next to its debunk.
THREAD_SHOTS = {
    "waterfall": "thread-1-how-the-number-was-made.png",
    "all-fees": "thread-2-fees.png",
    "hindsight": "thread-3-hindsight.png",
    "luck": "thread-4-luck.png",
    "ai": "thread-5-ai.png",
}


def share() -> None:
    """The link-preview card (also copied into site/public) and the thread images."""
    import shutil

    SHARE.mkdir(exist_ok=True)
    with preview_server(), chrome() as browser:
        shots = [("og", (1200, 630), "og.png")] + [(scene, FILM_SIZE, name) for scene, name in THREAD_SHOTS.items()]
        for scene, (w, h), name in shots:
            page = open_page(browser, f"/?shot={scene}", w, h)
            page.wait_for_timeout(300)
            page.screenshot(path=str(SHARE / name))
            page.context.close()
    shutil.copy(SHARE / "og.png", SITE / "public" / "og.png")
    print(f"Share images in {SHARE.relative_to(REPO_ROOT)}; og.png copied to site/public (rebuild to include it)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["review", "pages", "film", "film-test", "share"])
    parser.add_argument("--at", default="1,7,13,19,26,33,40,47,52", help="seconds, for film-test")
    args = parser.parse_args()
    if args.command == "review":
        review()
    elif args.command == "pages":
        pages()
    elif args.command == "film-test":
        film_frames_at([float(s) for s in args.at.split(",")])
    elif args.command == "film":
        film()
    elif args.command == "share":
        share()


if __name__ == "__main__":
    main()
