# workspace-scripts-archive

Full snapshot of `/home/z/my-project/scripts/` (75 entries, ~2MB) plus the
operational worklog (`WORKLOG-snapshot.md`, phone number redacted), preserved
so nothing built during the sessions is lost.

Provenance notes:
- Most entries are one-off forensic/probe scripts from the dependency-audit
  lifecycle (TASK-02D) against `omni-medical-suite` — kept for reproducibility.
- The active Telegram campaign tooling lives in the dedicated repo
  **[tg-campaign-toolkit](https://github.com/DrAbdulmalek/tg-campaign-toolkit)**
  (forwarder + link-harvest pipeline + recovery runbook).
- Secret scan: clean (no tokens / session strings / phone numbers).
- `addendum_gen/` and `report_gen/` subdirectories were dropped (empty
  scaffolding); `.txt/.out/.json` artifacts are historical outputs kept as-is.
