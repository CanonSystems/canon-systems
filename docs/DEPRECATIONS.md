# Sibling repository disposition (local machine)

One-line **keep** | **absorb** | **delete** recommendation per sibling for the Canon Memory Platform v1 consolidation. Paths are absolute on this workstation.

---

## canon-platform

- **Path:** `/Users/edwardwalker/localwork/canon-platform`
- **Label:** **keep**
- **Justification:** Mature serverless product surface (Lambda, API Gateway, Amplify per `README.md`); not the home of `KNOWLEDGE_API_URL` / worker / memory-adapter backends audited in `docs/WAVE-0-AUDIT.md`.
- **Recommended wave:** E1+ (integration boundaries only; no merge into v2 backend tree without explicit program decision).

---

## canon-systems-v2

- **Path:** `/Users/edwardwalker/localwork/canon-systems-v2`
- **Label:** **keep**
- **Justification:** Authoritative implementation and container definitions for knowledge-api, knowledge-worker, and memory-adapter source (`services/*`, `deploy/manifest.json`, `deploy/docker/*`).
- **Recommended wave:** E0–E2 (continue as primary backend repo).

---

## mempalace

- **Path:** `/Users/edwardwalker/localwork/mempalace`
- **Label:** **absorb**
- **Justification:** Local semantic-memory engine; `memory-adapter` in v2 wraps MemPalace-style search—capabilities should fold into the unified memory platform rather than stay a separate operational concern.
- **Recommended wave:** E4–E5 (adapter + storage semantics).

---

## obsidian-mind

- **Path:** `/Users/edwardwalker/localwork/obsidian-mind`
- **Label:** **absorb**
- **Justification:** Agent, command, script, and vault patterns for synthesis and session memory—explicit Wave 5 absorption target (see `docs/OBSIDIAN-MIND-CATALOGUE.md`).
- **Recommended wave:** E5 (catalogue) → E6–E7 (platform hooks).

---

## temporal

- **Path:** `/Users/edwardwalker/localwork/temporal`
- **Label:** **keep**
- **Justification:** Upstream Temporal server OSS (`README.md`); dependency for durable execution, not Canon-owned application code to delete or merge.
- **Recommended wave:** N/A (vendor baseline; pin/version only).

---

## total_recall

- **Path:** `/Users/edwardwalker/localwork/total_recall`
- **Label:** **absorb**
- **Justification:** Repo-scoped Cursor session recall design (`docs/total-recall-whitepaper.md`); concepts overlap Canon Memory Platform goals—merge into platform design rather than maintain a parallel product.
- **Recommended wave:** E3–E5 (ingestion + retrieval alignment).
