Show each split pane's full public herdr ID, like `w1:p2`, on the right side
of its top border, so the ID that herdr's CLI and agents use to address a pane
is right there on screen.

It's a native setting, `ui.show_pane_ids_on_pane_borders`: a boolean, off by
default, documented in the config reference, hot-reloaded and saved from
Settings like herdr's other UI options. It stays independent of
`ui.show_agent_labels_on_pane_borders`. Settings > Pane Labels has two
checkbox rows, agent labels (detected agent names, on the left) and pane ids
(full pane IDs, on the right). Up/Down and `j`/`k` pick a row; Enter, Space or
a click toggles only that row and saves right away.

The ID is always the exact, complete one herdr gives the pane
(`public_pane_id_for_number` today), never rebuilt or shortened by hand, and
never truncated. Every bordered split pane shows it, plain shells with no
title included. The left title keeps upstream's rules for what it shows
(metadata title, then the manual pane name, then the detected agent label when
agent labels are on) and its focused/unfocused styling; the ID is drawn in the
theme's muted `overlay0` color and never bold.

When space is short the ID wins: reserve its full padded width first, keep at
least one border column between the two, and truncate the left title with
herdr's display-width-aware helpers (so CJK text cuts cleanly), dropping it
entirely if only the ID fits. If even the padded ID doesn't fit, leave it out.
With pane borders off the setting is kept but nothing is drawn, and with pane
IDs off the border looks exactly like upstream's.

Tests cover the default and parsed config, hot reload, saving from Settings,
the two rows toggled independently by keyboard and mouse, plain-shell IDs,
manual labels, focused styling, CJK truncation, narrow panes, complete IDs and
the disabled cases.

Once herdr ships its own setting that shows full pane IDs on borders this way,
this patch is done.
