#!/usr/bin/env python3
"""
Shorts Conveyor Engine (shorts-conveyor)
High-retention batch video generation pipeline for viral YouTube Shorts.
Supports standalone and multi-part cliffhanger series.
"""

import os
import sys
import io
import math
import json
import time
import re
import random
import asyncio
import textwrap
import subprocess
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/Users/tim/shorts-conveyor"
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_CACHE = "/tmp/conveyor_cache"

os.makedirs(ASSETS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_CACHE, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_and_download_image(query, save_path):
    """Searches Bing for ultra-high-res 4K thematic images and saves the best match."""
    import requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Try query with 'wallpaper 4k' suffix for cinematic look
    search_terms = [f"{query} cinematic 4k wallpaper", f"{query} 4k", query]
    for term in search_terms:
        try:
            url = f"https://www.bing.com/images/search?q={requests.utils.quote(term)}&form=HDRSC2&first=1"
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                murls = re.findall(r'&quot;murl&quot;:&quot;(http[^&]+)&quot;', r.text)
                for u in murls[:6]:
                    try:
                        r_img = requests.get(u, headers=headers, timeout=5)
                        if r_img.status_code == 200:
                            img = Image.open(io.BytesIO(r_img.content)).convert("RGB")
                            if img.width >= 720 and img.height >= 480:
                                img.save(save_path, quality=94)
                                print(f"[+] Downloaded 4K scene for '{query}': {img.size}")
                                return True
                    except Exception:
                        continue
        except Exception as e:
            print(f"[-] Search error for '{term}': {e}")
            continue
            
    return False

def generate_video(story):
    """
    Renders a complete vertical Short from a story specification.
    story = {
        'id': 'kola_part1',
        'title': '...',
        'series_name': 'ТАЙНЫ ЗЕМЛИ',
        'part': 1,
        'script': '...',
        'scenes': ['query1', 'query2', ...],
        'shock_words': ['УЖАС', 'КРИКИ', ...]
    }
    """
    story_id = story["id"]
    print(f"\n=======================================================")
    print(f"🚀 CONVEYOR: Starting production for [{story_id}]")
    print(f"Title: {story['title']}")
    print(f"=======================================================")
    
    story_tmp = os.path.join(TEMP_CACHE, story_id)
    os.makedirs(story_tmp, exist_ok=True)
    
    # 1. VOICE SYNTHESIS VIA EDGE-TTS WITH WORD BOUNDARY
    print("🎙 Step 1: Synthesizing voiceover with exact WordBoundary timestamps...")
    voice_path = os.path.join(story_tmp, "voice.mp3")
    
    import edge_tts
    word_events = []
    
    async def run_tts():
        comm = edge_tts.Communicate(story["script"], "ru-RU-DmitryNeural", rate="+5%", boundary="WordBoundary")
        with open(voice_path, "wb") as f_voice:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f_voice.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    st = chunk["offset"] / 1e7
                    dur = chunk["duration"] / 1e7
                    txt = chunk["text"].strip()
                    if txt:
                        word_events.append({"text": txt, "start": st, "end": st + dur})
                        
    asyncio.run(run_tts())
    
    res = subprocess.run([
        "/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", voice_path
    ], capture_output=True, text=True)
    total_duration = float(res.stdout.strip())
    print(f"✓ Voiceover ready: {total_duration:.2f}s, {len(word_events)} words recorded.")
    
    # 2. GROUP WORDS INTO KINETIC SUBTITLE CARDS
    print("📝 Step 2: Auto-clustering words into punchy subtitle badges...")
    sub_cues = []
    
    # Smart clustering: groups of 2-4 words, or break at punctuation (. , ! ? :)
    current_cluster = []
    for w in word_events:
        clean_word = w["text"].upper()
        current_cluster.append(w)
        
        # Check if punctuation ends phrase or length exceeds 3-4 words
        has_punct = any(clean_word.endswith(p) for p in [".", ",", "!", "?", "—", ":", "..."])
        words_length = sum(len(x["text"]) for x in current_cluster)
        
        if has_punct or len(current_cluster) >= 3 or words_length > 18:
            t_start = current_cluster[0]["start"]
            t_end = current_cluster[-1]["end"]
            card_text = " ".join(x["text"].upper().strip(".,!?:—") for x in current_cluster)
            sub_cues.append((t_start, t_end, card_text))
            current_cluster = []
            
    if current_cluster:
        t_start = current_cluster[0]["start"]
        t_end = current_cluster[-1]["end"]
        card_text = " ".join(x["text"].upper().strip(".,!?:—") for x in current_cluster)
        sub_cues.append((t_start, t_end, card_text))
        
    print(f"✓ Created {len(sub_cues)} dynamic subtitle cards.")
    
    # 3. DOWNLOAD / PREPARE SCENE IMAGES
    print("🖼 Step 3: Downloading & caching thematic scene visuals...")
    scene_paths = []
    for idx, q in enumerate(story["scenes"]):
        img_p = os.path.join(story_tmp, f"scene_{idx}.jpg")
        if not os.path.exists(img_p):
            success = search_and_download_image(q, img_p)
            if not success:
                # Fallback to an existing scenic asset or generate dark canvas if download fails
                fallback_p = os.path.join("/tmp/pilot_render/scenes", f"scene{(idx % 5) + 1}.jpg")
                if os.path.exists(fallback_p):
                    img_p = fallback_p
                else:
                    Image.new("RGB", (1080, 1920), (14, 16, 26)).save(img_p, quality=92)
        scene_paths.append(img_p)
        
    num_scenes = len(scene_paths)
    scene_duration = total_duration / num_scenes
    print(f"✓ {num_scenes} scenes ready (~{scene_duration:.2f}s per scene).")
    
    # 4. RENDER DYNAMIC KEN BURNS BACKGROUND (1080x1920 @ 30fps)
    print("🎥 Step 4: Rendering dynamic Ken Burns background animation...")
    fps = 30
    total_frames = int(math.ceil(total_duration * fps))
    bg_video_path = os.path.join(story_tmp, "bg.mp4")
    
    aspect = 1080 / 1920
    loaded_scenes = []
    for idx, p in enumerate(scene_paths):
        img = Image.open(p).convert("RGB")
        iw, ih = img.size
        if iw / ih > aspect:
            max_h = ih
            max_w = int(ih * aspect)
        else:
            max_w = iw
            max_h = int(iw / aspect)
        loaded_scenes.append({
            "start": idx * scene_duration,
            "end": (idx + 1) * scene_duration if idx + 1 < num_scenes else total_duration,
            "img": img,
            "iw": iw, "ih": ih,
            "max_w": max_w, "max_h": max_h
        })
        
    cmd_bg = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", "1080x1920",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "h264_videotoolbox",
        "-b:v", "9000k",
        bg_video_path
    ]
    p_bg = subprocess.Popen(cmd_bg, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    for f_idx in range(total_frames):
        t = f_idx / fps
        sc_idx = min(num_scenes - 1, int(t / scene_duration))
        sc = loaded_scenes[sc_idx]
        
        sc_dur = max(0.1, sc["end"] - sc["start"])
        prog = min(1.0, max(0.0, (t - sc["start"]) / sc_dur))
        
        # Alternating zoom in / zoom out for visual rhythm
        if sc_idx % 2 == 0:
            zoom = 1.0 - 0.12 * prog
        else:
            zoom = 0.88 + 0.12 * prog
            
        cw = int(sc["max_w"] * zoom)
        ch = int(sc["max_h"] * zoom)
        cx = (sc["iw"] - cw) // 2
        cy = (sc["ih"] - ch) // 2
        
        frame = sc["img"].crop((cx, cy, cx + cw, cy + ch)).resize((1080, 1920), Image.Resampling.BILINEAR)
        p_bg.stdin.write(frame.tobytes())
        
    p_bg.stdin.close()
    p_bg.wait()
    print("✓ Ken Burns background track rendered!")
    
    # 5. RENDER WORD-SYNCED SUBTITLES & TOP PART BADGE
    print("🎨 Step 5: Rendering kinetic subtitles & series badge overlay...")
    subs_mov = os.path.join(story_tmp, "subs.mov")
    cmd_subs = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-loglevel", "error",
        "-f", "rawvideo",
        "-pix_fmt", "rgba",
        "-s", "1080x1920",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "qtrle",
        subs_mov
    ]
    p_subs = subprocess.Popen(cmd_subs, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    
    font_sub_path = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
    shock_keywords = [w.upper() for w in story.get("shock_words", [])] + [
        "УЖАС", "ВЗРЫВ", "СМЕРТЬ", "ЖУТКО", "КРИКИ", "ВЫРВАЛОСЬ", "ЗАВАРИЛИ", "ШОК",
        "СМОТРИ", "ЧАСТЬ", "ТАЙНА", "ЧЕЛОВЕЧЕСТВА", "АД", "МОНСТР"
    ]
    
    # Part badge specs
    part_num = story.get("part")
    series_name = story.get("series_name", "ТАЙНЫ")
    font_badge = ImageFont.truetype(font_sub_path, 34)
    
    for frame_idx in range(total_frames):
        t = frame_idx / fps
        img = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 5a. Top Badge (Part indicator)
        if part_num:
            badge_txt = f"ЧАСТЬ {part_num}  |  {series_name.upper()}"
            b_box = font_badge.getbbox(badge_txt)
            text_w = b_box[2] - b_box[0]
            text_h = b_box[3] - b_box[1]
            
            # Badge dimensions: pad_left + circle(16) + gap(14) + text_w + pad_right
            bw = text_w + 76
            bh = text_h + 26
            bx0 = 540 - bw // 2
            by0 = 190
            
            draw.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=16, fill=(10, 12, 20, 220), outline=(255, 45, 45, 240), width=3)
            # Glowing live indicator red dot
            dot_cx = bx0 + 26
            dot_cy = by0 + bh // 2
            r = 7
            draw.ellipse([dot_cx - r - 2, dot_cy - r - 2, dot_cx + r + 2, dot_cy + r + 2], fill=(255, 40, 40, 90))
            draw.ellipse([dot_cx - r, dot_cy - r, dot_cx + r, dot_cy + r], fill=(255, 45, 45, 255))
            # Text
            draw.text((bx0 + 44, by0 + bh // 2), badge_txt, font=font_badge, fill=(255, 255, 255, 255), anchor="lm")
            
        # 5b. Subtitle Card
        active_phrase = None
        for st, en, text in sub_cues:
            if st <= t <= en:
                active_phrase = text
                break
                
        if active_phrase:
            is_shock = any(k in active_phrase for k in shock_keywords)
            lines = textwrap.wrap(active_phrase, width=15)
            font_size = 62 if len(lines) > 1 else 68
            font_sub = ImageFont.truetype(font_sub_path, font_size)
            
            line_bboxes = [font_sub.getbbox(l) for l in lines]
            line_widths = [b[2] - b[0] for b in line_bboxes]
            line_heights = [b[3] - b[1] for b in line_bboxes]
            max_w = max(line_widths)
            line_spacing = 16
            total_h = sum(line_heights) + (len(lines) - 1) * line_spacing
            
            y_center = 510
            pad_x = 44
            pad_y = 24
            x0 = max(60, 540 - max_w // 2 - pad_x)
            x1 = min(1020, 540 + max_w // 2 + pad_x)
            y0 = y_center - total_h // 2 - pad_y
            y1 = y_center + total_h // 2 + pad_y
            
            border_col = (255, 55, 0, 245) if is_shock else (255, 215, 0, 245)
            draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(10, 12, 20, 225), outline=border_col, width=5)
            
            curr_y = y_center - total_h // 2 + line_heights[0] // 2
            for i, line in enumerate(lines):
                txt_col = (255, 75, 20, 255) if is_shock else (255, 230, 20, 255)
                draw.text(
                    (540, curr_y), line,
                    font=font_sub, fill=txt_col,
                    anchor="mm",
                    stroke_width=5, stroke_fill=(0, 0, 0, 255)
                )
                if i + 1 < len(lines):
                    curr_y += line_heights[i] + line_spacing
                    
        p_subs.stdin.write(img.tobytes())
        
    p_subs.stdin.close()
    p_subs.wait()
    print("✓ Overlays & Subtitles rendered!")
    
    # 6. AUDIO MASTERING & HOOK MIX (WITH BANNER SOUND AT 5.0s)
    print("🔊 Step 6: Mastering audio layers (Voice + Hook Riser + Ambient Drone + Stitch Sound)...")
    hook_wav = os.path.join(ASSETS_DIR, "signature_hook_mastered.wav")
    bg_music = os.path.join(ASSETS_DIR, "horror_bg.mp3")
    stitch_vid = os.path.join(ASSETS_DIR, "stitch_banner.mp4")
    mixed_audio = os.path.join(story_tmp, "master_audio.m4a")
    
    cmd_audio = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-i", voice_path,
        "-i", hook_wav,
        "-ss", "12", "-i", bg_music,
        "-i", stitch_vid,
        "-filter_complex",
        f"[0:a]volume=1.28,compand=attacks=0.02:decays=0.1:points=-80/-80|-20/-10|-8/-3|0/0[v]; "
        f"[1:a]volume=1.35[h]; "
        f"[2:a]volume=0.16,afade=t=in:st=0:d=1.0,afade=t=out:st={max(0.0, total_duration-1.2):.2f}:d=1.2[b]; "
        f"[3:a]adelay=5000|5000,volume=0.92[st]; "
        f"[v][h][b][st]amix=inputs=4:duration=first:dropout_transition=2[out]",
        "-map", "[out]",
        "-c:a", "aac", "-b:a", "192k",
        mixed_audio
    ]
    subprocess.run(cmd_audio, check=True)
    print("✓ Sound track mastered (including Stitch audio at 5.0s)!")
    
    # 7. FINAL MULTI-LAYER VIDEO COMPOSITE
    print("⚡ Step 7: Assembling multi-layer video (Fire 0-0.5s, Stitch strictly at 5.0s, Hardware H.264)...")
    fire_vid = os.path.join(ASSETS_DIR, "fire.ogv")
    output_mp4 = os.path.join(OUTPUT_DIR, f"{story_id}.mp4")
    
    cmd_final = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-i", bg_video_path,
        "-ss", "1.8", "-i", fire_vid,
        "-itsoffset", "5", "-i", stitch_vid,
        "-i", subs_mov,
        "-i", mixed_audio,
        "-t", f"{total_duration:.2f}",
        "-filter_complex",
        "[0:v]eq=contrast=1.12:saturation=1.22:brightness=-0.02[base]; "
        "[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        "colorkey=0x000000:0.18:0.1,format=yuva420p[fire]; "
        "[base][fire]overlay=enable='lte(t,0.5)':x=0:y=0[with_fire]; "
        "[2:v]scale=660:-1,colorkey=0x00FF00:0.3:0.1,format=yuva420p[stitch]; "
        "[with_fire][stitch]overlay=enable='between(t,5.0,11.04)':x=(W-w)/2:y=H-h-160[with_banner]; "
        "[with_banner][3:v]overlay=0:0[final_v]",
        "-map", "[final_v]",
        "-map", "4:a",
        "-c:v", "h264_videotoolbox",
        "-b:v", "8500k",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output_mp4
    ]
    subprocess.run(cmd_final, check=True)
    
    # 8. WRITE METADATA JSON FOR YOUTUBE UPLOADER (STRICTLY RUSSIAN HASHTAGS + PROMOCODE SHORTS)
    description = (
        f"🎁 Промокод: SHORTS\n\n"
        f"{story['title']}\n\n"
        f"Смотри продолжение в профиле и подписывайся, чтобы не пропустить развязку!\n\n"
        f"#шортс #истории #факты #мистика #катастрофы #тайны #наука #шок #крипота #выживание"
    )
    
    meta = {
        "id": story_id,
        "title": story["title"],
        "series": story.get("series_name", ""),
        "part": story.get("part"),
        "description": description,
        "tags": ["шортс", "истории", "факты", "мистика", "катастрофы", "тайны", "наука", "шок", "крипота", "выживание"],
        "duration": total_duration,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    meta_path = os.path.join(OUTPUT_DIR, f"{story_id}.json")
    with open(meta_path, "w", encoding="utf-8") as f_meta:
        json.dump(meta, f_meta, ensure_ascii=False, indent=2)
        
    # Copy automatically to biribro channel pending queue if it exists
    biribro_queue = os.path.expanduser("~/youtube-uploader/channels/biribro/pending")
    if os.path.exists(biribro_queue):
        import shutil
        dest_vid = os.path.join(biribro_queue, f"{story_id}.mp4")
        dest_json = os.path.join(biribro_queue, f"{story_id}.json")
        shutil.copy2(output_mp4, dest_vid)
        shutil.copy2(meta_path, dest_json)
        print(f"📦 Скопировано в очередь канала biribro: {dest_vid}")
        
    # Auto-cleanup heavy intermediate files (~1 GB per render)
    for _tmp_f in [bg_video_path, subs_mov, mixed_audio, voice_path]:
        if os.path.exists(_tmp_f):
            try:
                os.remove(_tmp_f)
            except OSError:
                pass

    print(f"\n🎉 DONE! Finished video rendered to: {output_mp4}")
    return output_mp4

if __name__ == "__main__":
    if len(sys.argv) > 1:
        story_file = sys.argv[1]
        with open(story_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    generate_video(item)
            else:
                generate_video(data)
    else:
        print("Usage: python3 conveyor.py <story.json>")
