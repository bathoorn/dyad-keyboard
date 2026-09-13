# Tools

## KiCad

- KiCad **10.0.6** (installed) — schematic + PCB, per PLAN.md §3/§5

- AI tooling

  **Where each one installs, and when.** Two of these go into Claude and two go into KiCad. None are needed before Phase 3 — Phase 1 is a breadboard and QMK, which needs no tooling beyond a shell.

  | Tool | Installs into | Install at |
  |---|---|---|
  | kicad-happy | **Claude Code** (plugin) | Phase 3, before the first review |
  | kicad-mcp | **Claude Code** (MCP server) | Phase 3, and only once a board exists — it bridges a *running* KiCad session, so it is inert before then |
  | marbastlib | KiCad (PCM) | Phase 3 |
  | kicad-kbplacer | KiCad (plugin) | Phase 3 |

  Hold the MCP server until it is actually useful: an MCP server's tool schemas sit in context permanently, whereas a plugin costs nothing until invoked.

  - **kicad-happy** skill — file-based review/audit: DRC/ERC cross-checks, schematic-vs-PCB net tracing, BOM extraction, EMC pre-compliance. No running KiCad session needed. Verified: it is packaged as a Claude Code plugin — `/plugin marketplace add aklofas/kicad-happy` then `/plugin install kicad-happy@kicad-happy`, both from an interactive terminal session. (Also ships as standalone zero-dependency Python 3.10+ scripts and a GitHub Action, if a non-agent path is ever wanted.) Use it as the automated pass for the §4 "MCU-section review checklist" (schematic diff against the minimal design example, decoupling coverage, ground-pour continuity) before ordering the controller module in Phase 4.5. https://github.com/aklofas/kicad-happy
  - **kicad-mcp** (Seeed-Studio) — live MCP bridge into an open KiCad 9+ session: inspect schematics/PCBs, trace nets, drive edits interactively. Complements kicad-happy rather than replacing it — this is for hands-on layout sessions, kicad-happy is the checklist gate. https://github.com/Seeed-Studio/kicad-mcp-server

- Placement/routing
  - **kicad-kbplacer** — KLE → footprint placement + routing. Actively maintained, CLI mode, and `schematic_builder` now handles stabilizers and rotary encoders directly (relevant: one EC11 per half). Confirmed pick in PLAN.md §0. **Gap:** it only understands KLE key units, so it won't place the solved knob-pod geometry in `hardware/layout/pods.json` — plan a small custom placement script layered on top for those. https://github.com/adamws/kicad-kbplacer
  - **kle2netlist** — netlist generation from the KLE source, paired with kbplacer per PLAN.md §0.

- Component libraries
  - **marbastlib** (ebastler) — the keyboard parts library. Replaces kicad-keyboard-parts.pretty, which was the same author's older, narrower library. 13 `.pretty` footprint libs and 6 `.kicad_sym` symbol libs. https://github.com/ebastler/marbastlib
    - Install via **KiCad PCM**, not a manual clone — it ships version-matched packages and this machine runs KiCad 10.0.6. Add this repository under PCM → Manage, then install marbastlib from it: `https://raw.githubusercontent.com/ebastler/ebastler-KiCad-repository/main/repository.json`. There is no `kicad-cli pcm` subcommand, so this step is GUI-only.
    - **Verified present:** MX/Choc hotswap sockets (`SW_MX_HS_CPG151101S11_*`, Kailh CPG151101S11), stabilizers (`STAB_MX_*`), USB-C receptacles (GCT USB4505/USB4510, HRO TYPE-C-31-M-*), WS2812_2020 both standalone and switch-integrated (`LED_MX_WS2812_2020`, which places the LED in the switch cutout for you).
    - **Gap — rotary encoder.** Has only the switch-integrated `ROT_Alps_EC11E-Switch.kicad_mod` + 3D model, and **no schematic symbol** for it in any of the 6 symbol libs. The no-switch `EC11N` variant — the one PLAN.md §2 actually wants — is a 3D STEP model only, no footprint. See open questions.
    - **Gap — per-key RGB.** Same shape of problem: `LED_SK6812MINI-E.step` exists as a 3D model, but there is **no SK6812MINI-E footprint** — only WS2812_2020, which is a 2.0 × 2.0 mm part against SK6812MINI-E's 3.5 × 3.5 mm reverse-mount. PLAN.md §3 currently specs SK6812MINI-E. Either source that footprint elsewhere, or switch the plan to WS2812_2020 and get the switch-integrated footprint for free. Decide before the Phase 3 main-PCB layout, since this is the reservation that cannot be retrofitted.
    - **Gap — no GC9A01 coverage** (see below).
  - Official Raspberry Pi Pico KiCad files, or **ncarandini/KiCad-RP-Pico** — RP2040 symbol/footprint reference, per PLAN.md §4.
  - **easyeda2kicad.py** / **JLC2KiCad_lib** — pull footprint + 3D model straight from the LCSC part number for the JLCPCB-PCBA'd parts (W25Q128JVSIQ, AP2112K-3.3, USBLC6-2SC6, the RP2040 itself) so the design-side footprint matches the assembly-side part exactly, rather than trusting a hand-picked generic footprint.
  - Install marbastlib and kicad-kbplacer through **KiCad PCM** rather than manual vendoring, where possible (marbastlib repository URL above).

## Case CAD

Parametric, driven by the same key-position data as the PCB (`hardware/layout/`), per PLAN.md §4/§6 Phase 4.

- **build123d** (pick) — Python, OCCT kernel (same as FreeCAD). Fillets/lofts/booleans handle the bearing race, ring-gear teeth (mechanism Option A, PLAN.md §2), and pod pockets much better than pure CSG.
- **FreeCAD** — same OCCT kernel, full GUI + sketcher + assembly workbench. Better for hand-iterating dimensions and consuming the STEP files KiCad exports (PLAN.md §3). Heavier than scripting alone; worth having installed regardless for STEP inspection.
- **OpenSCAD** — simplest scripting model, but CSG-only — the round bearing seat and ring-gear geometry get awkward without OCCT-style fillets. Probably not the pick here.

## Firmware (QMK)

- **QMK CLI** + **external userspace** — keymap lives outside the `qmk_firmware` tree, per PLAN.md §6 Phase 6.
- **Vial** (pick over VIA for this board) — the layout JSON compiles into firmware itself; no need to merge a keyboard definition into VIA's upstream repo or side-load unsigned JSON each session. Better fit while this board isn't upstreamed.
- **VIA** — reconsider only if the QMK keyboard definition actually gets upstreamed (PLAN.md §6 Phase 7 holds this as optional).
- **keymap-drawer** (+ `vial-to-keymap-drawer`) — renders the keymap for the build guide, Phase 7.

## Open questions

- GC9A01 breakout: no footprint in marbastlib (checked the library contents directly, not just the README). It's a generic round-LCD module with no standard KiCad library entry anywhere — plan to hand-draw a pin-header footprint once you've picked the exact module you're buying (pitch/pin-count vary by vendor).
- EC11 no-switch variant (EC11N — what PLAN.md §2 actually calls for, since the encoder's own click is deliberately unused): no footprint in either library, only an orphaned 3D model. Simplest path is probably to reuse the EC11E-Switch footprint body and just leave its switch pads unpopulated, rather than drawing a separate footprint — same mechanical part either way. Confirm that assumption once a specific supplier/datasheet is picked, since "E"/"N" suffixes aren't a reliably-documented standard across vendors.
- Pick one of the kicad-mcp implementations after a short hands-on trial (Seeed-Studio vs. mixelpixx vs. lamaalrajih) rather than committing from descriptions alone.
- Design the custom pod-placement script (kbplacer gap, above) before Phase 3 layout starts.
