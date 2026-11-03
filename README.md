# 🎬 Shorts Conveyor Engine

> **High-retention batch video generation pipeline for viral vertical videos (YouTube Shorts, Reels, TikTok).**  
> 100% automated local rendering on **Apple Silicon (M-series)** using hardware-accelerated FFmpeg (`h264_videotoolbox`).

---

## 🚀 Key Highlights

* **Hardware Accelerated Render:** Leverages Apple Silicon's Media Engine via `h264_videotoolbox` — full 1080x1920 60s render takes ~30 seconds.
* **Precise Kinetic Subtitles:** Uses `edge-tts` with native `WordBoundary` timestamps to cluster words into high-contrast kinetic cards with custom shock-word highlights.
* **Dynamic Ken Burns Background:** Automatically downloads thematic 4K cinematic scenes, pre-crops to 9:16, and applies alternating smooth zoom/pan animations.
* **Mastered Multi-Layer Audio:** Combines neural voiceover, signature low-end infrabass hook riser, dynamic background horror/ambient drone, and synchronized sound effects with zero audio clipping (`amix` + `compand`).
* **Multi-Part Story Engine:** Supports cliffhanger episodic serials (`ЧАСТЬ 1`, `ЧАСТЬ 2`, ...) with animated glowing live status badges.
* **Zero Resource Leakage:** Intermediate uncompressed RGBA/QTRLE layers and raw audio stems are automatically cleaned up post-render.

---

## 🛠 Architecture

```
                          ┌───────────────────────────┐
                          │   Story Spec (JSON)       │
                          └─────────────┬─────────────┘
                                        │
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
     [TTS Voiceover]             [Asset Pipeline]          [Kinetic Subtitles]
  edge-tts WordBoundary       Bing 4K Scraper + Fallback   Word Clustering & Boxes
             │                          │                          │
             ▼                          ▼                          ▼
     Master Audio Mix           Ken Burns Background        RGBA QTRLE Overlay
  (Compand + Hook Riser)      (h264_videotoolbox 9Mbps)            │
             │                          │                          │
             └──────────────────────────┼──────────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   Final Composite & Render  │
                         │   1080x1920 @ 30fps (H.264) │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │  output/<id>.mp4 + meta.json│
                         └─────────────────────────────┘
```

---

## 📦 Installation & Setup

### Prerequisites
* macOS with Apple Silicon (M1/M2/M3/M4) recommended.
* FFmpeg with `videotoolbox` support:
  ```bash
  brew install ffmpeg
  ```

### Quickstart
1. Clone the repository:
   ```bash
   git clone git@github.com:VseyadCraft/shorts-conveyor.git
   cd shorts-conveyor
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the conveyor with a story script:
   ```bash
   python3 conveyor.py stories/sample_story.json
   ```

---

## 📁 Repository Structure

```
shorts-conveyor/
├── conveyor.py           # Core production engine
├── requirements.txt      # Python dependencies
├── assets/               # Audio hooks, fire overlays, banners
│   └── fallback/         # Emergency offline visual assets
├── stories/              # JSON-based episode & series definitions
└── output/               # Rendered production videos & metadata
```

---

## 📜 License
MIT License. Created by [VseyadCraft](https://github.com/VseyadCraft).
