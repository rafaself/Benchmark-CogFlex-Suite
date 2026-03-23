# Reports Layout

`reports/` is the implemented evidence surface for benchmark audits and live provider evidence. It is organized by context and target.

Canonical pattern:

- `reports/<context>/<target>/latest/<stable-name>.<ext>`
- `reports/<context>/<target>/latest/metadata.json` for canonical run provenance
- `reports/<context>/<target>/history/<stable-name>__<YYYYMMDD_HHMMSS>.<ext>`
- `reports/<context>/<target>/history/metadata__<YYYYMMDD_HHMMSS>.json` for immutable provenance snapshots
- `reports/<context>/<target>/samples/`

Current top-level groupings:

- `audit/`: deterministic benchmark audits, repairs, optimization summaries, and evidence-pass artifacts.
- `live/`: real-provider execution reports and provider-side diagnostic captures.

Current readiness interpretation:

- the active v1 readiness evidence path is Gemini;
- the current anchor evidence lives under `reports/live/gemini-first-panel/binary-vs-narrative/latest/`;
- the anchor evidence preserves the original requested model label `gemini-2.5-flash`;
- the next active evidence target is `gemini-2.5-flash-lite`;
- Anthropic and OpenAI local report paths exist, but they are outside the current v1 readiness gate.

Canonical live evidence should point to the `latest/` report, artifact, and metadata first. Flat top-level report aliases such as `reports/m1_binary_vs_narrative_robustness_report.*` are convenience mirrors and should stay byte-identical to the canonical `latest/` surfaces they reference.

Examples:

- `reports/live/gemini-first-panel/binary-only/history/report__legacy.md`
- `reports/live/gemini-first-panel/binary-vs-narrative/latest/report.md`
- `reports/live/gemini-first-panel/binary-vs-narrative/history/artifact__20260322_201900.json`
- `reports/live/gemini-first-panel/binary-vs-narrative/samples/raw_capture__20260323_120000.json`
- `reports/audit/evidence-pass/history/01_current_report.md`
