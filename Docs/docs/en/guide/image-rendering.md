---
title: "Image Rendering"
date: 2026-08-23
description: "UniBot image rendering guide: enable image mode to render command output as polished image cards, combining renderer engine, template and resource extensions."
tags:
  - image rendering
  - renderer
  - templates
---

# Image Rendering

After setting `[image] mode` to `true` in `Config.toml`, the bot's command output will be sent in **image** form. Lists, fortune, status, and other commands render as beautifully designed image cards.

## Rendering System

Image rendering is provided by **rendering engine**, **template**, and **resource** extensions, all distributed as extensions via the **extension marketplace**. Install and combine them freely:

::: table title="Rendering System Components" copy="all"
| Component | Extension Type | Role |
|------|---------|------|
| **Rendering engine** | `renderer` extension | Renders a page into an image and determines the rendering implementation (e.g. Html2Pic) |
| **Template** | `template` extension | Determines the layout and style of the image; each template is an image style that can be switched at any time |
| **Resource** | `resources` extension | Provides static assets such as images and fonts, applied together with the template |
:::

The official marketplace provides a ready-to-use combination:

::: table title="Official Rendering Extensions" copy="all"
| Extension | Type | Notes |
|------|------|------|
| `Html2Pic` | Rendering engine | ==Lightweight, low resource usage, fast rendering== |
| `Playwright` | Rendering engine | Browser-based rendering, ==better quality==, but ==slower and more resource-intensive== |
| `Default` | Template & resource | Image templates and resource pack for built-in commands |
:::

Choose the rendering engine as needed: pick `Html2Pic` for speed and low resource usage, or `Playwright` for higher rendering quality. Switching engines requires a ==restart==; different engines can share the same template and resources.

## Enabling Image Mode

::: steps

1. **Install the rendering extensions**

   Install a rendering engine (`Html2Pic` or `Playwright`, choose as needed) and `Default` (default template & resources) from the WebUI marketplace. If they are missing when image mode is enabled, WebUI will guide you to download them automatically.

2. **Enable and choose the rendering configuration**

   Set `mode = true` in the `[image]` section of `Config.toml`, and specify the rendering engine and template to use:

   ```toml
   [image]
   mode = true
   renderer = "html2pic" # Rendering engine: html2pic or playwright (must match an installed renderer extension)
   template = "Default"  # Template pack (must match an installed template extension)
   # font = ""           # Optional: custom font path; if empty, Font.ttf is looked up in resource extensions
   ```

3. **Restart the bot**

   Changes to `mode` and `renderer` take effect after a ==**restart**==; `template` switching takes effect ==**immediately**== without restarting.

:::

You can also switch the rendering engine and template directly in **WebUI → Extensions**.

- ==Template auto-fallback==: when the selected template pack is missing or unavailable, it falls back to the default template (`Default` or the first available one).
- ==Rendering engine must be selected==: image mode requires an installed and selected rendering engine extension; if the engine is missing or unavailable, rendering reports an error.

## Adjusting Image Appearance

The background, colors, fonts, and other appearance of images are provided by **template extensions**, not configured in the core `Config.toml`:

- A template extension can declare appearance config items (such as primary color, font, layout, etc.) in its manifest.
- In **WebUI → Extensions**, select the corresponding template extension and edit it through the form; changes take effect **immediately** after saving. You can also edit `Config/Extensions/<template-id>.toml` directly.
- Switching the template pack changes the overall image style.

*Note: image mode slightly increases response time.*

## Commands with Image Rendering Support

::: table title="Commands with Image Rendering Support" copy="all"
| Command | Rendered Content |
|------|----------|
| `/list` | Online player list (including player avatars) |
| `/server` | Server connection status |
| `/luck` / `/luck rank` | Daily fortune card / fortune leaderboard |
| `/bound` | Whitelist binding information |
| `/help` | Help information |
| `/bot about` | About page |
| `/bot check` | Version check result |
:::
