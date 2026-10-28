#!/usr/bin/env python3
"""Find which video on a YouTube channel contains a quote, using auto-captions.

    ytsearch.py CHANNEL_OR_PLAYLIST_URL "quote or fragment" [options]

Captions are cached in --cache (default ./captions/<channel-slug>), so re-running
with a different quote only costs the search. Requires yt-dlp (see run.sh).
"""
import argparse, difflib, glob, os, re, subprocess, sys, time

def ytdlp(*args, **kw):
    return subprocess.run([sys.executable, "-m", "yt_dlp", *args], text=True, **kw)

def list_videos(url):
    r = ytdlp("--flat-playlist", "--print", "%(id)s|%(title)s", url,
              capture_output=True)
    vids = [l.split("|", 1) for l in r.stdout.splitlines() if "|" in l]
    if not vids:
        sys.exit(f"No videos found at {url}\n{r.stderr[-500:]}")
    return vids

def fetch_captions(vids, cache, delay):
    """Download English auto-captions (VTT) for each video not already cached."""
    os.makedirs(cache, exist_ok=True)
    missing = []
    for vid, title in vids:
        if glob.glob(os.path.join(glob.escape(cache), glob.escape(vid) + ".*vtt")) \
                or os.path.exists(os.path.join(cache, vid + ".none")):
            continue
        ytdlp("--skip-download", "--write-auto-subs", "--sub-langs", "en-orig,en",
              "--sub-format", "vtt", "-o", os.path.join(cache, "%(id)s.%(ext)s"),
              f"https://www.youtube.com/watch?v={vid}", capture_output=True)
        if not glob.glob(os.path.join(glob.escape(cache), glob.escape(vid) + ".*vtt")):
            open(os.path.join(cache, vid + ".none"), "w").close()  # no captions
            missing.append(title)
        print(f"  fetched {vid}  {title[:60]}", file=sys.stderr)
        time.sleep(delay)
    return missing

def norm(s):
    return re.sub(r"[^a-z0-9' ]", "", s.lower().replace("-", " "))

def words_with_times(path):
    """Collapse YouTube's rolling captions into one clean word stream + timestamps."""
    stream, times, t = [], [], 0
    for line in open(path, encoding="utf-8"):
        m = re.match(r"(\d+):(\d+):(\d+)\.\d+ -->", line)
        if m:
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3]); continue
        if not line.strip() or line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        w = norm(re.sub(r"<[^>]+>", "", line)).split()
        # rolling captions repeat the previous line's tail; drop the overlap
        k = min(len(w), len(stream), 40)
        while k and stream[-k:] != w[:k]:
            k -= 1
        for x in w[k:]:
            stream.append(x); times.append(t)
    return stream, times

def best_window(stream, target):
    n = len(target)
    best = (0.0, 0)
    for i in range(max(1, len(stream) - n + 1)):
        r = difflib.SequenceMatcher(None, stream[i:i + n], target).ratio()
        if r > best[0]:
            best = (r, i)
    return best

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="channel /videos URL, playlist URL, etc.")
    ap.add_argument("quote")
    ap.add_argument("--cache", help="caption cache dir (default captions/<slug>)")
    ap.add_argument("--min-score", type=float, default=0.6,
                    help="fuzzy match threshold 0-1 (default 0.6; lower = looser)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--delay", type=float, default=2, help="seconds between downloads")
    ap.add_argument("--no-fetch", action="store_true", help="search cached captions only")
    a = ap.parse_args()

    url = a.url if "/videos" in a.url or "playlist" in a.url or "watch" in a.url \
        else a.url.rstrip("/") + "/videos"
    slug = re.sub(r"\W+", "_", url.split("youtube.com/")[-1]).strip("_")
    cache = a.cache or os.path.join("captions", slug)

    vids = list_videos(url)
    titles = dict(vids)
    print(f"{len(vids)} videos in {url}", file=sys.stderr)
    if not a.no_fetch:
        nocap = fetch_captions(vids, cache, a.delay)
        if nocap:
            print(f"{len(nocap)} new videos have no captions", file=sys.stderr)

    target = norm(a.quote).split()
    frags = [" ".join(target[i:i + 3]) for i in range(max(1, len(target) - 2))]
    hits, scanned = [], 0
    by_vid = {}
    for path in sorted(glob.glob(os.path.join(glob.escape(cache), "*.vtt"))):
        vid = os.path.basename(path).split(".")[0]
        if vid in titles and (vid not in by_vid or "en-orig" in path):
            by_vid[vid] = path  # one file per video, prefer the original-language track
    for vid, path in by_vid.items():
        stream, times = words_with_times(path)
        if not stream:
            continue
        scanned += 1
        score, i = best_window(stream, target)
        text = " ".join(stream)
        found = [f for f in frags if f in text]
        if score >= a.min_score or found:
            hits.append((score, len(found), vid, times[i],
                         " ".join(stream[max(0, i - 4):i + len(target) + 4])))
    hits.sort(key=lambda h: (h[0], h[1]), reverse=True)
    for score, nf, vid, t, ctx in hits[:a.top]:
        print(f"{score:.2f}  {titles[vid]}\n      https://youtu.be/{vid}?t={t}\n"
              f"      \"...{ctx}...\"  ({nf}/{len(frags)} 3-word fragments exact)\n")
    print(f"scanned {scanned}/{len(vids)} videos with captions; "
          f"{len(hits)} hit(s)" if hits else
          f"no matches in {scanned}/{len(vids)} videos with captions")

if __name__ == "__main__":
    main()
