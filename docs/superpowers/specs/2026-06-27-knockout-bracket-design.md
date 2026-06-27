# Tournament Knockout Bracket — Design

## Goal
A third fixed map-control button, **Tournament Knockout** (bracket icon), opens a
frosted right-side drawer (same style as Tournament Stats / Team Travel Map)
showing a Google-style knockout bracket. A carousel pages through stage-pairs;
the body scrolls vertically when a column overflows.

## Carousel pages (2 stages at a time)
1. Round of 32 · Round of 16  (8 ties)
2. Quarter-Final · Semi-Final (2 ties)
3. Final · 3rd-Place Final    (side by side, no connector)

Prev/next arrows + page dots. Page index in a `dcc.Store`.

## Layout: tie-based (robust alignment)
Each page (except the Final page) is a vertical list of **ties**. A tie =
one right-stage match + its two feeder matches, linked via the schedule's
`"Winner Match N"` placeholders. Rendering `[2 feeder cards | connector | 1
winner card]` per tie auto-centres the winner between its feeders and scrolls
naturally. The Final page renders the Final and Bronze Final as two cards.

## Match card (Google-like)
- Dimmed date/time header: "Today/Tomorrow, HH:MM" or "Tue, 30 Jun, HH:MM"
  (user timezone when known, else venue local).
- Two team rows: flag + name (+ score when played); winner bolded.
- Unresolved slot → grey shield + "TBD".

## Data — `src/data/bracket.py` (pure, tested)
- `BracketMatch`/`Slot` dataclasses; `KO_STAGES`, `STAGE_PAGES`.
- `build_bracket(ko_matches, standings, complete_groups, results)` resolves each
  slot, in match-number order so winners propagate into `"Winner Match N"`:
  - `results[number]` (from live `matches_on`, matched by kickoff) → real teams +
    scores; the higher score marks the winner and is recorded for propagation.
  - else resolve the label: `Group X winners/runners-up` from `standings` **only
    when that group is complete**; `Winner/Runner-up Match N` from recorded
    winners/losers; third-place slots stay unresolved (TBD).
- `stage_ties(bracket, left, right)` → `[(winner_match, [feeders…])]` via
  `feeder_numbers` parsed from the schedule labels.

## Wiring
- `map_view.build_map_controls`: add `knockout-control` button (top of stack).
- `layout`: add `build_knockout_drawer()`.
- `app.py`: toggle callback (open knockout, close others; others close knockout);
  carousel callback (prev/next → page store); render callback
  (page + live-store + user-tz → `knockout-body`). Live overlay builds
  `standings`, `complete_groups`, `results` from the snapshot + cached per-date
  matches.

## Constraints
- dash-mantine-components only; pandas for data; OOP dataclasses.
- TDD. Full-screen, no page scroll; bracket scrolls inside the drawer body.
- Responsive/mobile-friendly; reuse existing frosted-drawer + card idioms.
