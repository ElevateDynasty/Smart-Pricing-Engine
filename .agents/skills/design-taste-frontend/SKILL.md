---
name: design-taste-frontend
description: "Use when building high-agency frontend interfaces with strict design taste, calibrated color, responsive layout, and motion rules."
category: frontend
risk: safe
---
# High-Agency Frontend Skill

## When to Use
- Use when building or reviewing frontend UI with strong design taste and anti-generic constraints.
- Overrides common LLM UI biases such as centered heroes, purple gradients, card overuse, poor states, and fragile layouts.

## 1. ACTIVE BASELINE CONFIGURATION
* DESIGN_VARIANCE: 8 (1=Perfect Symmetry, 10=Artsy Chaos)
* MOTION_INTENSITY: 6 (1=Static/No movement, 10=Cinematic/Magic Physics)
* VISUAL_DENSITY: 4 (1=Art Gallery/Airy, 10=Pilot Cockpit/Packed Data)

## 2. ANTI-SLOP CORE PRINCIPLES
* **ANTI-EMOJI POLICY [CRITICAL]:** NEVER use emojis in code, markup, text content, or alt text. Replace symbols with high-quality icons or clean SVG primitives. Emojis are BANNED.
* **THE LILA BAN:** The "AI Purple/Blue" aesthetic is strictly BANNED. No purple button glows, no neon gradients. Use absolute neutral bases (Zinc/Slate/Obsidian) with high-contrast, singular accents (e.g. Electric Cyan, Emerald, or Signal Amber).
* **ANTI-CARD OVERUSE:** Avoid boxing every metric in a floating card. Use architectural grouping: clean dividers (`divide-x`, `border-t`), negative space, and typographic scale.
* **DETERMINISTIC TYPOGRAPHY:**
  - Display: High-character sans (Outfit, Satoshi, Cabinet Grotesk), tight tracking (`tracking-tight`).
  - Monospace for Data: JetBrains Mono or SF Mono for numbers, currencies, timestamps, and percentages.
  - Zero generic Serif fonts in software dashboards.
* **LIQUID GLASS REFRACTION:**
  - 1px border `rgba(255, 255, 255, 0.08)`.
  - Inner specular highlight: `box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08)`.
* **SKELETAL LOADERS:** Replace generic spinners with layout-matching skeletal shimmer bars.
* **TACTILE MICRO-PHYSICS:** `:active { transform: translateY(1px) scale(0.98); }` with spring easing `cubic-bezier(0.16, 1, 0.3, 1)`.
