# ESCRIBE Skills Manifest — Phase 2 & Beyond

## Core Skills for ESCRIBE Pipeline

### Image Generation & Validation (Phase 2)
- **davila7/claude-code-templates@clip** (296 installs) — CLIP embeddings & image-text similarity
  - Validates Flux-generated images match prompts
  - Directly supports S3.2 CLIP feedback loop
  
- **davila7/claude-code-templates@stable-diffusion-image-generation** (975 installs)
  - Fallback image generation provider
  
### Video Processing & Composition (Phase 2-3)
- **erichowels/some_claude_skills@video-processing-editing** (696 installs) ⭐ TOP
  - Professional video editing, codec handling, frame manipulation
  - Supports color grading, transitions, effects composition
  
- **digitalsamba/claude-code-video-toolkit@ffmpeg** (3K installs) ⭐ ESSENTIAL
  - FFmpeg wrapper for video codec/probe validation
  - Direct support for Phase 1 black-frame detection
  
- **eachlabs/skills@video-color-grading** (192 installs)
  - Color grading profiles for S4.1 cinematography
  - Complements OpenMontage compose function

### Screenplay & Narrative (Phase 3)
- **rfxlamia/claude-skillkit@screenwriter** (76 installs)
  - Narrative-to-screenplay conversion
  - Enhances M7 director output

- **gtmagents/gtm-agents@scriptwriting** (79 installs)
  - Structure narratives into shootable scripts

### Advanced Effects (Phase 4)
- **bbeierle12/skill-mcp-claude@postfx-effects** (79 installs)
  - Vignette, lens flare, glitch, bloom effects
  - Supports S4.3 effect chain rendering

## Installation Queue

```bash
npx skills add davila7/claude-code-templates@clip
npx skills add erichowels/some_claude_skills@video-processing-editing
npx skills add digitalsamba/claude-code-video-toolkit@ffmpeg
npx skills add eachlabs/skills@video-color-grading
npx skills add davila7/claude-code-templates@stable-diffusion-image-generation
npx skills add rfxlamia/claude-skillkit@screenwriter
```

## Mapping to ESCRIBE Phases

| Phase | Objective | Required Skills |
|-------|-----------|-----------------|
| Phase 1 | Black video detection | ffmpeg, video-processing-editing |
| Phase 2 | Visual quality | clip, color-grading |
| Phase 3 | Cinematography | video-processing-editing, postfx-effects |
| Phase 4 | Professional effects | postfx-effects, screenwriter |

---

Generated: 2026-05-09
