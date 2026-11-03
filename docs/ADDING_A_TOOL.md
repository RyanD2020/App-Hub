# Adding a tool to the App hub

The App hub is the one Databricks App for all of our team's tools. Each tool runs as a page inside it instead of being
its own app. This guide covers building a new tool and moving an existing app in. Follow it every time; the tests in
`tests/` check most of it.

## 1. Where a tool lives

```
tools/
  underwriting/                 a team id from config/hub.yaml (teams)
    __init__.py                 empty
    bracket_spell_check/        the tool's folder
      __init__.py               empty
      page.py                   defines render()
      report.py, ...            the tool's other files
```

Each team folder under `tools/` must be a team id in `config/hub.yaml`. Keep both `__init__.py` files free of imports,
so nothing loads until the tool's page is opened.

The tool's entry in `config/hub.yaml`:

```yaml
  - id: "bracket"                     # also its page address (/bracket) and its key prefix (bracket__)
    name: "Bracket Counter & Spell Check"
    team: "underwriting"
    mode: "embedded"
    module: "tools.underwriting.bracket_spell_check.page"
    url: ""                           # blank: embedded tools run inside the hub
    ...                               # the rest as for every tool (summary, stats, steps, ...)
```

A tool that is still its own Databricks App stays `mode: "external"` with its `url`; its Open button opens it in a new
tab.

## 2. The page: render()

`page.py` defines `render()`, and the hub calls it when someone opens the tool. The hub draws the header, the footer and
the page around it, so `render()` draws only the tool's own content. Nothing should run when the module is imported
except imports and constants.

```python
"""Bracket Counter & Spell Check: compares two versions of a contract."""
from pathlib import Path

import streamlit as st

from tools.underwriting.bracket_spell_check import report

HERE = Path(__file__).parent


def render() -> None:
    st.session_state.setdefault("bracket__analyzed", False)  # every key starts with the tool id
    file_a = st.file_uploader("Upload Version A", type=["docx", "pdf"], key="bracket__file_a")
    ...
```

Write keys as plain strings or f-strings that start with the prefix (`f"bracket__editor_{n}"`), so the tests can read
them.

## 3. The rules

### Only app.py calls st.set_page_config

The hub sets the title, icon and layout once, in `app.py`. Remove `st.set_page_config` from tool code: Streamlit allows
it only once per run.
Checked by `test_only_app_py_calls_set_page_config` and `test_no_set_page_config_anywhere_under_tools`.

### Every key starts with the tool id

All pages share one `st.session_state`, so two tools that both use `key="file_a"` or `st.session_state.docs` would
overwrite each other. Prefix every widget key and every session_state name with the tool id and two underscores:

| Instead of | Write |
|---|---|
| `key="file_a"` | `key="bracket__file_a"` |
| `key=f"spell_editor_{n}"` | `key=f"bracket__spell_editor_{n}"` |
| `st.session_state.docs` | `st.session_state["bracket__docs"]` |
| `"docs" in st.session_state` | `"bracket__docs" in st.session_state` |

Keys built from a variable (for example a defaults dict looped into session_state) can't be checked by the tests, so
prefix the dict's keys by hand.
Checked by `test_widget_and_session_state_keys_start_with_the_tool_id`.

### Import the tool's own files by package path

Write `from tools.underwriting.bracket_spell_check import report`, never `import report` or
`from report import build_pdf_report`. A bare import finds whichever `report.py` Python sees first, so two tools with
same-named files would load each other's code.
Checked by `test_tools_use_package_imports`.

### Find the tool's own files from its folder

Word lists, templates and other files that ship with the tool are found with `Path(__file__).parent`, never the working
directory: the hub runs from the repo root, not from the tool's folder.

```python
HERE = Path(__file__).parent
legal_terms = (HERE / "legal_terms.txt").read_text(encoding="utf-8")
```

Checked by `test_tools_find_their_files_from_their_own_folder` (no `os.getcwd`, `os.chdir` or `Path.cwd`).

### Never keep lasting data on the app's local disk

Databricks can wipe the app's disk on any restart or redeploy. Temporary files for one person's session are fine: use
`tempfile`, and delete them when done. Anything that must last (records, history, uploaded files someone needs later)
goes to Delta tables through `core/db.py`.

`core/db.py` doesn't exist yet: it comes with the hub's Part 2 (saving requests to Delta). Until then, a tool that needs
lasting data can't move into the hub. Talk to the admins first.
Checked in part by `test_tools_keep_no_local_database` (no `sqlite3`, `shelve` or `dbm`).

### Keep workspace values out of the code

Warehouse IDs, catalog and schema names, workspace URLs and app URLs live in `app.yaml` (as environment variables and
app resources) or `config/hub.yaml`, never in Python. Then the hub can move to another workspace with a redeploy and no
code change. A tool reads them with `os.environ`, using names that start with its id in capitals, for example
`BRACKET_CATALOG`. A SQL warehouse or other resource is added to the hub app, and `app.yaml` reads it with `valueFrom`.
Checked by `test_no_workspace_values_in_code`.

### Errors stay on the tool's page

The hub wraps `render()` (`core/embed.py` and `views/nav.py`). If the tool raises an error while it's imported or drawn,
its page shows a short message and an Email the team link, and the traceback goes to the app's logs. The header, the
footer and every other page keep working. So let errors reach the hub: don't catch exceptions just to hide them.

Two things run outside `render()`, so the hub can't catch their errors:

- Widget callbacks (`on_click`, `on_change`, `on_submit`). Streamlit runs them before the page, so an error there stops
  the whole page, header included. Prefer reading the widget's value inside `render()`. If a callback is needed, keep it
  to setting session_state, or catch its errors inside the callback and show them from `render()`.
- `st.fragment` reruns. A fragment that reruns on its own doesn't go through `render()`. Avoid fragments unless the
  admins agree.

`st.stop()`, `st.rerun()` and `st.switch_page()` work as usual.
Checked by `tests/test_embed.py` and `test_a_failing_tool_shows_a_message_on_its_own_page`.

### Merge the tool's requirements into requirements.txt

All tools share the hub's `requirements.txt`. Add each package the tool imports, pinned to one exact version
(`python-docx==1.1.2`, not `>=`). If the tool needs a different version of a package the hub already pins (Streamlit,
pandas and so on), stop and agree it with the admins first: changing a pin changes every tool. Streamlit in particular
stays at the version the hub's design is checked against.
Checked by `test_requirements_are_pinned_exactly_and_once` and `test_every_package_a_tool_imports_is_in_requirements`.

## 4. Moving an existing app into the hub

1. Make a branch from `main`. Never commit or push to `main`.
2. Get the code the app deploys from, without changing the original. If the app deploys from a Git repo, clone it to a
   temporary folder outside this repo. If it deploys from a workspace folder, export it with
   `databricks workspace export-dir` to a temporary folder.
3. Copy it into `tools/<team>/<tool folder>/`. Change only what the rules above require, plus turning the top-level
   script into `render()`. Leave the tool's logic alone.
4. In `config/hub.yaml`, set the tool's `team`, `mode: "embedded"` and `module`, and blank its `url`.
5. Merge its requirements (see above).
6. Prove nothing changed: run the same sample files through the original code and the new page, and check that every
   result matches (counts, findings, report contents). Use sample files, never real client documents.
7. Run `tests/run_tests.py` in Databricks, deploy the branch to app-hub-test and try the tool there. Then open a pull
   request. Deployment steps are in `docs/DEPLOY.md`.
8. Once it works in app-hub, retire the old app as `docs/DEPLOY.md` describes.

## 5. Checks

| File | What it checks |
|---|---|
| `tests/test_tools.py` | Folder layout: team folders are team ids, each tool folder is a package with `page.py` and `render()`, each is an embedded tool in hub.yaml, and its module imports |
| `tests/test_tool_rules.py` | The rules in section 3, on every embedded tool's code |
| `tests/test_embed.py` | The error guard catches a failing tool and lets Streamlit's own control flow through |
| `tests/test_app.py` | The whole hub runs headless: every page, team pages, a failing tool, and no tool imported at startup |

Run them all in Databricks with `tests/run_tests.py` (open it from the hub's Git folder and click Run all).
