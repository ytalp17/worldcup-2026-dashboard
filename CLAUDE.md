# CLAUDE.md — World Cup 2026 Dashboard

> Read this file before touching any code.

---

## Project

A Plotly Dash dashboard centred around an interactive map.
The map is the heart of the app — everything else supports it.
The map is restricted to the three 2026 host countries: **USA, Mexico, and Canada**.

---

## Hard Rules

- **UI components**: `dash-mantine-components` only. No Bootstrap, no raw `html.Button` etc.
  Before using any DMC component, fetch its current API via the **context7 MCP**.
- **Data**: `pandas` for all data wrangling.
- **OOP**: use Python classes/dataclasses wherever a data entity or service naturally fits.
- **TDD**: write tests before implementation. Run with `pytest tests/ -v`.
- **Design**: elegant, clean. Use best UI/UX principles. Dark/light mode switch always present.
- **Layout**: full-screen, no scrollbars — the app fits the viewport at all times.
- **Responsive**: works on mobile. No horizontal overflow.
- **Data files**: go in `assets/data/`. User provides them.

---

## Map

- Library: `dash-leaflet`
- Tiles: OpenStreetMap (no API key needed)
- Bounds: locked to USA + Mexico + Canada only
- Everything else about the map is decided as features are added.

---

## What's Decided Later

Everything not listed above. Ask before assuming.
