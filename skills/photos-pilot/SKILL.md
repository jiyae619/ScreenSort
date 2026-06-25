---
name: photos-pilot
description: Process a batch of Apple Photos screenshots into organized knowledge notes — dedup, privacy pre-filter, AI triage, a browser sorter to confirm, then integrate kept items and stage junk for deletion. Trigger when the user says "run the screenshot pilot for <batch>", "process <batch> screenshots", or "/photos-pilot <batch>".
---

# photos-pilot

Drive the screenshot→notes pipeline for one **batch** (a year like `2023`, or an album/date-range label). Scripts live in `~/photos-pilot/` (adjust if installed elsewhere). You orchestrate the local stdlib scripts and the AI triage on the user's tokens; **you never need Photos access** — only the user's FDA Terminal does, for export and tagging.

## Ground rules (privacy + safety)
- **Never paste PROTECT / sensitive OCR text into the chat.** Refer to such items by uuid/filename only.
- **You never delete photos.** Deletion happens only when the user runs `pilot-tag` and presses `⌘⌫` in Photos (30-day undo).
- **Never drop a kept item** when integrating notes — fold in every kept screenshot's content (merge by topic, not dated blocks).
- Sensitive items are excluded from triage by `sensitive.py`; favorites and PROTECT are never auto-deleted.

## Steps

Resolve `<batch>` from the user's message (default mode comes from `config.json`'s `batch_unit`). Then:

1. **Orient.** Run `python3 ~/photos-pilot/status.py <batch>` to see which artifacts exist and what's next. Resume from there — don't redo completed steps.

2. **Require the export.** If `export.json` is missing, stop and tell the user to run **`pilot <batch>`** in their **Full Disk Access Terminal** (you can't do OCR/Photos access). Wait for them. **If their images are loose files on disk (not in Apple Photos)** — e.g. `~/Downloads` — they (or you) run `python3 ~/photos-pilot/export_folder.py <folder> <batch>` instead (local OCR, no Photos/FDA). For a loose-file batch, skip the Photos steps: `tag.py` doesn't apply and DELETE means removing those files (`delete.txt`).

3. **Dedup + privacy pre-filter** (pure local):
   - `python3 ~/photos-pilot/dedup.py <batch>` — near-duplicate detection → `dups.json`.
   - `python3 ~/photos-pilot/sensitive.py <batch>` — flags sensitive items → `sensitive.json`, excluded from triage.

4. **AI triage** (the speed lever):
   - **Cold start (new user, no prior labeled batch):** first run `python3 ~/photos-pilot/seed_sample.py <batch>` — the user labels ~15 sample screenshots and Downloads `pilot-<batch>-seed.json`. `make_triage` then calibrates from those labels (instead of generic). Skip this once they have any applied batch to calibrate from.
   - `python3 ~/photos-pilot/make_triage.py <batch>` — writes `_triage/rubric.md` + `chunk_NN.json` (dups + sensitive already excluded). If it reports `no_cloud` mode, skip triage entirely and go to step 5 (keyword seeding only).
   - **Fan out one subagent per chunk, in parallel.** Each reads `_triage/rubric.md` + its `_triage/chunk_NN.json` and writes `_triage/part_NN.json` (a JSON array of `{u,cat,conf,why}`, one per input item, valid JSON only). Calibrate to the rubric's examples; bias toward KEEP when unsure.
   - `python3 ~/photos-pilot/merge_seed.py <batch>` — merges parts → `seed.json`; unclassified/invalid items become REVIEW (never dropped) and are listed in `_triage/missing.json`. If REVIEW/missing is non-trivial, re-run small chunks for those until it's near zero.

5. **Build the sorter.** `python3 ~/photos-pilot/recat.py <batch>`, then reveal the HTML in Finder (`open -R <path>`). Tell the user: review with **🔎 needs-review only** ON (verifies the uncertain + the delete pile; high-confidence keepers are hidden), correct categories in the lightbox (one-key filing), then **⬇ Download decisions**. Wait for them to say they're done / "apply".

6. **Apply + integrate** (after the user confirms):
   - `python3 ~/photos-pilot/apply.py <batch>` — snapshots decisions, writes `fulltext.txt` (per note-category) + `delete.txt`.
   - Read `fulltext.txt` and **integrate every kept item into the consolidated topic notes** in the configured output folder — merge into the relevant section by topic (bilingual), never date-appended blocks, nothing dropped. Refresh each touched note's TL;DR / Key insights / Keywords digest, and the INDEX map.
   - `python3 ~/photos-pilot/archive.py <batch>` — lossless raw-text archive (excludes PROTECT/DELETE).
   - **Portable output (non-Obsidian):** `build_notes.py <batch>` writes templated per-category notes to `<output>/<batch>/`; then fill each note's **Key insights** (and refine the rough auto-keywords) by summarizing its items. `summary_viewer.py [folder]` renders any notes folder into one offline HTML with Export-to-PDF.

7. **Hand off deletion.** Tell the user to run **`pilot-tag <batch>`** in the FDA Terminal, then in Photos open the **`📦 Delete (<batch> pilot)`** album → Select All → **`⌘⌫`** (Delete from Library, *not* plain `⌫`) → Recently Deleted (30-day undo).

Report a short summary at the end (counts per category, kept vs deleted, notes touched).

## Changing categories
If the user wants to add/rename/recolor/remove categories: run `python3 ~/photos-pilot/config_editor.py` to open the browser editor. When they've downloaded the new file and say something like *"apply my new categories"*, run `python3 ~/photos-pilot/apply_config.py` (validates + installs `~/Downloads/config.json` to `config.json`, keeping a `.bak`), then re-run `recat.py <batch>` so the sorter reflects the new set.
