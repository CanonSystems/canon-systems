# Obsidian Mind — capability catalogue (Wave 5 absorption)

Enumerates synthesis / summary / transform surfaces under `/Users/edwardwalker/localwork/obsidian-mind` for platform planning. Each row: **path (repo-relative)** — **one-line description**.

Source layout verified from `/Users/edwardwalker/localwork/obsidian-mind/README.md`, `/Users/edwardwalker/localwork/obsidian-mind/vault-manifest.json`, and listed `.claude` assets.

---

## `agents/` (`.claude/agents/*.md`)

| Path | Description |
| --- | --- |
| `.claude/agents/brag-spotter.md` | Surfaces wins and evidence worth capturing in performance/brag notes. |
| `.claude/agents/context-loader.md` | Loads vault context for a topic (person, project, incident, team, concept) into a synthesized briefing. |
| `.claude/agents/cross-linker.md` | Maintains and suggests wikilinks / graph coherence across notes. |
| `.claude/agents/people-profiler.md` | Builds or updates people/org notes from interactions and context. |
| `.claude/agents/review-fact-checker.md` | Checks review-related claims against vault evidence. |
| `.claude/agents/review-prep.md` | Prepares structured review packets from vault state. |
| `.claude/agents/slack-archaeologist.md` | Deep-reads Slack threads/incidents into timelines and structured incident notes. |
| `.claude/agents/vault-librarian.md` | Organizes vault structure, indexes, and housekeeping conventions. |
| `.claude/agents/vault-migrator.md` | Assists upgrades/migrations between vault template versions. |

---

## `commands/` (`.claude/commands/om-*.md`)

| Path | Description |
| --- | --- |
| `.claude/commands/om-capture-1on1.md` | Captures 1:1 meeting content into org/work notes. |
| `.claude/commands/om-dump.md` | “Brain dump” unstructured input into multiple structured vault updates. |
| `.claude/commands/om-humanize.md` | Rewrites or softens text for human-readable notes. |
| `.claude/commands/om-incident-capture.md` | Ingests incident URLs/threads into full incident documentation. |
| `.claude/commands/om-intake.md` | Processes inbox/intake items into classified notes. |
| `.claude/commands/om-meeting.md` | General meeting capture workflow. |
| `.claude/commands/om-peer-scan.md` | Scans peer/context signals for standups or reviews. |
| `.claude/commands/om-prep-1on1.md` | Prepares 1:1 briefs from vault + tasks. |
| `.claude/commands/om-project-archive.md` | Archives completed projects with summary artifacts. |
| `.claude/commands/om-review-brief.md` | Generates review briefings for a period or theme. |
| `.claude/commands/om-review-peer.md` | Peer-review oriented note synthesis. |
| `.claude/commands/om-self-review.md` | Self-review / reflection structured output. |
| `.claude/commands/om-slack-scan.md` | Scans Slack for items to pull into the vault. |
| `.claude/commands/om-standup.md` | Morning standup: goals, tasks, git activity, priorities. |
| `.claude/commands/om-vault-audit.md` | Audits vault health, links, and template compliance. |
| `.claude/commands/om-vault-upgrade.md` | Guides vault upgrade steps across template versions. |
| `.claude/commands/om-weekly.md` | Weekly synthesis / planning pass. |
| `.claude/commands/om-wrap-up.md` | End-of-session wrap: links, indexes, brag spotting. |

---

## `scripts/` (`.claude/scripts/*`)

| Path | Description |
| --- | --- |
| `.claude/scripts/charcount.sh` | Utility character counting for hooks or limits. |
| `.claude/scripts/classify-message.py` | Classifies messages for routing (e.g., hook pipelines). |
| `.claude/scripts/find-python.sh` | Locates Python interpreter for portable hook execution. |
| `.claude/scripts/pre-compact.sh` | Pre-compaction hook helper for session lifecycle. |
| `.claude/scripts/session-start.sh` | Session-start shell hook setup. |
| `.claude/scripts/test_hooks.py` | Tests hook behavior. |
| `.claude/scripts/validate-write.py` | Validates writes (paths, frontmatter, policy) before commit to vault. |

---

## `skills/` (`.claude/skills/*/SKILL.md`)

| Path | Description |
| --- | --- |
| `.claude/skills/defuddle/SKILL.md` | HTML/content cleanup for readable markdown ingestion. |
| `.claude/skills/json-canvas/SKILL.md` | JSON Canvas graph note generation or manipulation. |
| `.claude/skills/obsidian-bases/SKILL.md` | Obsidian Bases (structured/tabular note views) workflows. |
| `.claude/skills/obsidian-cli/SKILL.md` | Obsidian CLI: notes, tasks, properties, vault automation. |
| `.claude/skills/obsidian-markdown/SKILL.md` | Obsidian-flavored markdown conventions and transforms. |
| `.claude/skills/qmd/SKILL.md` | QMD semantic search setup and query patterns over the vault. |

---

## Vault layout (`vault-manifest.json`)

Absolute manifest: `/Users/edwardwalker/localwork/obsidian-mind/vault-manifest.json`.

| Path / pattern | Description |
| --- | --- |
| `vault-manifest.json` | Template version, infrastructure file set, scaffold placeholders, user content roots, version fingerprints, frontmatter requirements. |
| `brain/*.md` | North Star, memories index, decisions, patterns, gotchas (goal and longitudinal context). |
| `work/active/`, `work/archive/`, `work/incidents/`, `work/1-1/` | Active work, archives, incidents, 1:1 series. |
| `work/Index.md` | Map of content (MOC) for work notes. |
| `org/people/`, `org/teams/`, `org/People & Context.md` | People and team context notes. |
| `perf/brag/`, `perf/evidence/`, `perf/competencies/`, `perf/Brag Doc.md` | Performance evidence, competencies, brag doc. |
| `reference/` | Long-lived reference material. |
| `thinking/README.md` | Thinking-space / scratch conventions. |
| `templates/**` | Note templates for structured capture. |
| `bases/**` | Bases definitions (tabular views). |
| `Home.md`, `CLAUDE.md` | Entry/dashboard and agent ground rules. |

---

## Summary counts (this snapshot)

| Area | Count |
| --- | ---: |
| `.claude/agents/*.md` | 9 |
| `.claude/commands/om-*.md` | 18 |
| `.claude/scripts/*` | 7 |
| `.claude/skills/*/SKILL.md` | 6 |
