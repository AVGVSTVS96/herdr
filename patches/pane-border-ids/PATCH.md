---
format: patch-md/v0.1
id: pane-border-ids
summary: Show full public pane IDs on the right side of pane borders through a native Pane Labels setting.
baseline: 5600197f00e871764465d4e3d9ba5e6aa6fd9547
patch_file: pane-border-ids.patch
patch_sha256: 42247fa93c4886e2a4e1794a86bb70984e3a7dfcc43b23c0edfef02b344b8ba9
---

## Intent

Add an independent native Pane Labels setting that displays each split
pane's full public Herdr ID, such as `w1:p2`, on the right side of its
top border.

The option is `ui.show_pane_ids_on_pane_borders`. It is a boolean,
defaults to false, hot-reloads, persists through Settings, and remains
independent of `ui.show_agent_labels_on_pane_borders`.

Settings > Pane Labels exposes two checkbox rows:

- agent labels — show detected agent names on the left
- pane ids — show full pane IDs on the right

Up/Down and `j`/`k` select a row. Enter, Space, and a left click toggle
only the selected row and save immediately.

## Invariants

1. Use the exact full ID produced by
   `public_pane_id_for_number(&ws.id, pane_number)`. Never reconstruct or
   shorten the public format independently.
2. Keep existing left-title precedence: metadata title, manual pane name,
   then detected agent label when agent labels are enabled.
3. Show IDs for every bordered split pane, including plain shells with no
   left title.
4. Render the existing title on the left and the pane ID on the right.
5. Reserve the full padded ID width first. Never truncate an ID.
6. Leave at least one visible border column between left and right titles.
7. Truncate the left title with Herdr's display-width-aware utilities.
   Omit the left title if only the ID fits; omit the ID if its full padded
   segment cannot fit.
8. Keep the left title's existing focused/unfocused styling. Render the ID
   with `palette.overlay0` and never bold it.
9. When pane borders are disabled, retain the setting without drawing it.
10. When pane IDs are disabled, preserve the existing left-only output.

## Verification

Keep tests for default and parsed config values, hot reload, Settings
persistence, independent keyboard and mouse toggles, two-row rendering,
plain-shell IDs, manual labels, focused styling, CJK truncation, narrow
panes, complete IDs, and disabled behavior.

Run `just check`.

## Removal

Remove this patch only when upstream Herdr provides an equivalent
independent native setting with the same full-ID, persistence, Settings,
layout-priority, and styling behavior.
