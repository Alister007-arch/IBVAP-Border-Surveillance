# Demo Assets

Place sample video clips here for testing the pipeline without live cameras.

## Recommended Free Sources

| Type | Source | Search Term |
|---|---|---|
| Daytime CCTV / crowd | [Pexels](https://www.pexels.com/search/videos/surveillance/) | "cctv", "surveillance", "crowd walking" |
| Night / low-light | [Pexels](https://www.pexels.com/search/videos/night%20street/) | "night street", "low light" |
| Drone footage | [Pixabay](https://pixabay.com/videos/search/drone/) | "aerial", "drone view" |
| Kaggle CCTV datasets | [Kaggle](https://www.kaggle.com/datasets?search=cctv+surveillance) | "CCTV surveillance dataset" |

## Naming Convention

Place files in this folder with these names so the demo commands work out of the box:

```
demo_assets/
├── sample.mp4          # daytime clip (people / vehicles) — used for Phase 1 smoke-test
├── night_sample.mp4    # night / low-light clip — used for Phase 4 night-mode test
├── crowd_sample.mp4    # crowd / group clip — used for Phase 6 event-grouping test
└── drone_sample.mp4    # aerial/small-object clip — used for Phase 3 Tier-2 test
```

## Quick Download (yt-dlp, optional)

If you have `yt-dlp` installed you can grab royalty-free clips directly:

```bash
# Example — replace with any Creative Commons / royalty-free URL
yt-dlp -o "demo_assets/sample.mp4" --format "mp4" <URL>
```

> [!NOTE]
> The pipeline runs without demo_assets if you have a live webcam.
> Use `--source 0` (or any index) instead of `--source demo_assets/sample.mp4`.
