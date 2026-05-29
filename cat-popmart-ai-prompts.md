# Mystery Meow — AI 视频生成提示词

面向 Runway Gen-3 / Pika 2.0 / Sora / Kling / Hailuo 的逐镜头提示词。

## 通用提示词写作原则

1. **主语 + 动作 + 环境 + 光线 + 风格 + 画幅**
2. 泡泡玛特风格关键词：`designer toy aesthetic`, `glossy finish`, `kawaii`, `blind box`, `collectible figure`, `soft vinyl texture`
3. 所有提示词给出英文版（主流工具对英文响应更好），中文版附后供参考

---

## Shot 01 — 神秘盒子降临 (0–3s)

### 提示词

```
[Runway Gen-3 / Sora]
A blind box toy package with a glowing "?" symbol slowly descending from above, floating mid-air center frame. Dark cosmic purple background with tiny floating sparkle particles like stardust. Magenta rim light edges the box. Haze atmosphere. Cinematic slow motion, shallow depth of field. 9:16 vertical aspect ratio. Designer toy unboxing aesthetic, Pop Mart style. Photorealistic with glossy toy-like texture. Camera slowly pushes in.
```

```
[Pika 2.0]
Mystery blind box floating in space, "?" symbol glowing pink, stardust particles drifting, dark purple ambiance, magical atmosphere, slow zoom in, 9:16 vertical
```

### 负面提示词 (Negative Prompt)
```
blurry, low quality, text watermark, deformed box, realistic human, dark and moody
```

---

## Shot 02 — 拆盒爆光 (3–6s)

### 提示词

```
[Runway Gen-3 / Sora]
A blind box bursting open with intense white light exploding outward from inside, lens flare, overexposed bloom transition. A cute cat plush doll figure emerges from the light, bouncing playfully with elastic squash-and-stretch motion. Pink and gold sparkle particles burst outward. White background fading in after flash. Camera shake effect. High energy, magical reveal moment. Designer vinyl toy aesthetic, kawaii style. 9:16 vertical.
```

```
[Pika 2.0]
Blind box opens, bright magical light bursts out, cute kawaii cat plush toy pops out bouncing, sparkles everywhere, white flash, exciting unboxing, 9:16 vertical
```

### 负面提示词
```
dark, scary, horror, aggressive motion, ugly creature, low quality
```

---

## Shot 03 — 面部大特写 (6–9s)

### 提示词

```
[Runway Gen-3 / Sora]
Extreme close-up macro shot of a cute kawaii cat plush doll face. Big round glossy black eyes with white catch light reflection, blinking once slowly. Pink soft blush on cheeks. Tiny cute nose and small smiling mouth. Ultra-soft peach-skin fleece fabric texture visible. Ring light reflection in eyes. Soft pink and cream color palette. Very shallow depth of field, background completely blurred with bokeh circles. Heartwarming, adorable. Designer toy aesthetic. 9:16 vertical.
```

```
[Pika 2.0]
Extreme close up of cute kawaii plush cat face, big glossy eyes blinking, pink blush, soft fabric texture, ring light in eyes, heartwarming adorable, bokeh background, slow motion, 9:16
```

### 负面提示词
```
realistic cat, fur, animal, ugly, scary eyes, dirty, damaged toy
```

---

## Shot 04 — 全身环绕展示 (9–12s)

### 提示词

```
[Runway Gen-3 / Sora]
Full body shot of a cute kawaii cat plush doll toy doing a playful spin, tail wagging. The cat wears a tiny pastel outfit with star patterns. Ultra-soft fleece material with subtle fabric texture. 360-degree orbiting camera movement around the toy. Studio lighting with soft key light and subtle backlight glow. Clean minimal pastel pink background with floating bokeh light dots. Smooth fluid motion. Designer collectible toy aesthetic, Pop Mart style product showcase. 9:16 vertical.
```

```
[Pika 2.0]
Cute kawaii cat plush doll spinning playfully showing full outfit, tail wagging, 360 camera orbit, soft studio lighting, pastel pink background with bokeh, smooth product showcase, 9:16 vertical
```

### 负面提示词
```
robotic movement, stiff, static, dark background, harsh lighting
```

---

## Shot 05 — 疯狂变体切换 (12–16s)

### 提示词

```
[Runway Gen-3 / Sora]
Rapid morphing sequence: the same cute kawaii cat plush doll toy rapidly changes color and outfit variants — pink starlight version → blue ocean sailor version → green forest elf version → orange sunny toast version → purple lavender version → golden galaxy rare version. Each transformation syncs to a beat. Frame-freeze morph transition effect. Color background matches each variant. High energy fast pace. Pop art color palette. Designer vinyl toy collection reveal. Stop-motion inspired. 9:16 vertical.
```

```
[Pika 2.0]
Fast morph color changing cute kawaii cat plush toy, pink to blue to green to orange to purple to gold, each change on beat, colorful backgrounds matching, high energy, pop art style, fun collection reveal, 9:16 vertical
```

### 负面提示词
```
slow motion, fade transition, blurry morph, creepy transformation
```

---

## Shot 06 — 全系列队形 (16–20s)

### 提示词

```
[Runway Gen-3 / Sora]
Six different cute kawaii cat plush dolls lined up in a row on a glossy display platform. From left to right: pink, blue, green, orange, purple, and a golden secret rare version rising up elevated above the others with a spotlight beam. Sequential spotlight sweeps across each toy. Gallery exhibition lighting. Clean minimal white background with subtle sparkle particles. Collectible designer toy series reveal. Proud, premium presentation. Depth of field. 9:16 vertical. Camera dollies from left to right.
```

```
[Pika 2.0]
Six kawaii cat plush dolls lined up, pink blue green orange purple variants, golden secret rare rises above with spotlight, camera slides left to right, gallery lighting, white clean background, premium toy collection, 9:16 vertical
```

### 负面提示词
```
messy, cluttered, dark, dirty, uneven lighting, missing toys
```

---

## Shot 07 — Logo / CTA 尾板 (20–25s)

### 提示词

```
[Runway Gen-3 / Sora]
Clean graphic composition on animated gradient background shifting from hot pink to purple to electric blue. "Mystery Meow" stylized logo text bounces in with elastic animation, glossy 3D rendered text with reflections. Below the logo: a blind box product mockup tilting slightly. Price tag pop animation. Sparkle and star particle effects around the logo. Premium brand identity reveal. Pop Mart style graphic design. Clean, bold, modern. 9:16 vertical. Last 2 seconds: fade to black with small website URL.
```

```
[Pika 2.0]
Animated logo "Mystery Meow" bouncing in on pink purple blue gradient background, glossy 3D text, blind box product below, sparkle stars, premium brand reveal, clean bold graphic, 9:16 vertical
```

### 负面提示词
```
text corruption, unreadable text, blurry logo, messy composition, cluttered design
```

---

## 三语字幕提示词 / Subtitle Overlay Prompts

如果工具支持图生视频或视频编辑，可使用以下提示添加字幕：

```
[Runway Gen-3 图生视频 / Video-to-Video]
Add clean bold white subtitle text at bottom third of frame: "[Insert subtitle text]". Rounded font with soft black shadow. Pop in with elastic scale animation, stay for 2 seconds, pop out. Minimal, modern typography. Do not alter the main video content.

[中文]
在画面底部三分之一处添加白色粗体字幕："[插入字幕文字]"。圆角字体配软黑阴影。弹性缩放动画弹出，停留2秒后弹走。极简现代排版。不改变主视频内容。

[日本語]
画面下部3分の1に白い太字の字幕を追加：「[字幕テキストを挿入]」。ソフトな黒影付きの丸みを帯びたフォント。弾性スケールアニメーションで登場、2秒表示後、消える。ミニマルでモダンなタイポグラフィ。メイン映像は変更しない。
```

---

## 工具推荐对比

| 工具 | 优势 | 适合镜头 |
|------|------|---------|
| **Runway Gen-3** | 画质最高, 物理模拟好 | Shot 01-04 写实镜头 |
| **Pika 2.0** | 速度快, 风格化强 | Shot 05 变体切换 |
| **Sora** | 长视频, 场景理解 | 全片一体生成 |
| **Kling** | 人物/动物表情 | Shot 03 面部特写 |
| **Hailuo** | 性价比高 | Shot 06-07 静态展示 |

---

## 备选：全片一体提示词 (Sora / Veo)

如果使用支持长视频的工具（Sora, Veo 2），可以尝试以下统一提示词：

```
[Full Video — 25 seconds, 9:16 vertical]
A 25-second Pop Mart style promotional video for a designer cat plush blind box toy series called "Mystery Meow: Cosmic Kittens".

Scene progression:
1. (0-3s) Mystery blind box with glowing "?" floating in cosmic purple space, slowly descending
2. (3-6s) Box bursts open with intense white light, cute kawaii cat plush toy bounces out
3. (6-9s) Extreme close-up of the cat toy face — big glossy eyes blinking, pink blush, soft fleece texture
4. (9-12s) 360-degree orbit around the toy showing full body and outfit details
5. (12-16s) Rapid morphing through 6 color variants (pink, blue, green, orange, purple, gold) on beat
6. (16-20s) All 6 variants lined up, golden secret rare rises elevated with spotlight
7. (20-25s) "Mystery Meow" logo animation on gradient background with product mockup

Style: Glossy designer vinyl toy aesthetic, photorealistic toy product photography, kawaii cute, Pop Mart brand style. Bouncy energetic pacing with beat-synced transitions. Vibrant pastel color palette with neon accents. Clean minimal backgrounds with sparkle particles throughout. Professional product commercial quality. No real animals, no humans.
```

---

## 音效提示词 (用于 AI 音频工具)

```
[ElevenLabs / Suno / Udio — BGM prompt]
Upbeat K-pop style instrumental, 128 BPM, future bass synth, cute sparkling chime accents, bouncy rhythm, catchy drop at 12 seconds, positive energetic mood, 25-second loop, no vocals, clean production

[Suno 歌词版 — 可选]
Genre: Kawaii Future Bass, Female Vocal Chop
Mood: Exciting, cute, magical, collectible
Style: Pop Mart commercial soundtrack

[ElevenLabs — 旁白生成]
Voice profile: Young female, warm and energetic, clear articulation, slight smile in voice
Language: Chinese (zh-CN) / English (en-US) / Japanese (ja-JP)
```

---

## 交付清单 / Deliverable Checklist

- [ ] Shot 01 视频片段 (3s)
- [ ] Shot 02 视频片段 (3s)
- [ ] Shot 03 视频片段 (3s)
- [ ] Shot 04 视频片段 (3s)
- [ ] Shot 05 视频片段 (4s)
- [ ] Shot 06 视频片段 (4s)
- [ ] Shot 07 视频片段 (5s)
- [ ] 中文旁白音频 (25s)
- [ ] 英文旁白音频 (25s)
- [ ] 日文旁白音频 (25s)
- [ ] BGM 音频 (25s)
- [ ] 中文版字幕 SRT
- [ ] 英文版字幕 SRT
- [ ] 日文版字幕 SRT
- [ ] 最终合成: 中文版 .mp4
- [ ] 最终合成: 英文版 .mp4
- [ ] 最终合成: 日文版 .mp4
