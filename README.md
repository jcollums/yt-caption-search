# yt-caption-search

> **Note:** this is just a quick vibe-coded tool. Expect rough edges.

Find which video on a YouTube channel (or playlist) contains a quote, by searching
its auto-generated captions. No video is downloaded.

```
./run.sh https://www.youtube.com/@SomeChannel "the quote or a fragment of it"
```

- First run creates `.venv` and installs yt-dlp; captions are cached in `captions/<channel>/`,
  so searching a new quote on the same channel is instant (add `--no-fetch` to skip the refresh).
- Matching is fuzzy (auto-captions garble words): `--min-score 0.5` loosens it.
  Output gives a timestamped link per hit.
- Videos with no captions can't be searched; the run reports how many were skipped.
- Node-less/old yt-dlp can hit YouTube JS-challenge issues; `pip install -U yt-dlp` usually fixes it.
