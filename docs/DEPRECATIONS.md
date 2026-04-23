# Sibling repository disposition (local machine) — FINAL

_Last updated: 2026-04-23 (E7-T2 close-out — moved-for-review variant)_

One-line **keep** | **absorb** | **delete** final disposition per sibling
for the Canon Memory Platform v1 consolidation. This document is **FINAL**.

Per operator direction at E7-T2, the three `absorb` targets (`mempalace`,
`obsidian-mind`, `total_recall`) were **not** deleted. Instead they were
moved to `/Users/edwardwalker/localwork/_deprecated/` as a holding area
for post-release review. Any final delete happens under a separate
operator action after review.

Paths below reflect **current** filesystem locations. `keep` / vendor
repos were untouched. Two canonical event types are recorded in
`.canon/memory/events.ndjson` as the durable record:
`sibling_disposition_finalized` (one per sibling; emitted at E7-T2 open)
and `sibling_moved_for_review` (one per moved sibling; emitted at
E7-T2 close after the physical move).

---

## canon-platform

- **Path:** `/Users/edwardwalker/localwork/canon-platform`
- **Final label:** **keep** (production-adjacent; outside v1 scope)
- **Justification:** Mature serverless product surface (Lambda, API Gateway,
  Amplify per `README.md`); not the home of `KNOWLEDGE_API_URL` / worker /
  memory-adapter backends audited in `docs/WAVE-0-AUDIT.md`.
- **Action taken:** none; integration boundaries preserved.

---

## canon-systems-v2

- **Path:** `/Users/edwardwalker/localwork/canon-systems-v2`
- **Final label:** **keep** (authoritative backend; already partially absorbed)
- **Justification:** Authoritative implementation and container definitions
  for `knowledge-api`, `knowledge-worker`, and `memory-adapter` source.
- **Action taken:** `infra/terraform/` absorbed into
  `canon-systems/infra/terraform/` @ E0-T4 (`ebecb91`). Remaining services
  stay in v2 as the primary backend repo; canon-systems references
  manifest-tracked deploy artefacts.

---

## mempalace

- **Original path:** `/Users/edwardwalker/localwork/mempalace`
- **Current path:** `/Users/edwardwalker/localwork/_deprecated/mempalace`
- **Original label:** absorb
- **Final label:** **absorbed + moved-for-review**
- **Absorption wave:** E4 (memory-adapter behavioural contract) /
  E5 (synthesis read paths).
- **Action taken:** MemPalace-style semantic search capabilities wrapped by
  the memory-adapter in canon-systems-v2. Sibling moved to
  `_deprecated/mempalace` on 2026-04-23 pending post-release review;
  delete gated by a separate operator action.

---

## obsidian-mind

- **Original path:** `/Users/edwardwalker/localwork/obsidian-mind`
- **Current path:** `/Users/edwardwalker/localwork/_deprecated/obsidian-mind`
- **Original label:** absorb
- **Final label:** **absorbed + moved-for-review**
- **Absorption wave:** E5 (catalogue → human synthesis plane) and E6
  (observability hooks).
- **Action taken:** Synthesis agent, command, script, and vault patterns
  folded into `backend/synthesis-web/`, `canon synth show`, `canon vault
  sync`, and `canon release publish-on-pass`. Sibling moved to
  `_deprecated/obsidian-mind` on 2026-04-23 pending post-release review.

---

## temporal

- **Path:** `/Users/edwardwalker/localwork/temporal`
- **Final label:** **keep (vendor baseline)**
- **Justification:** Upstream Temporal server OSS — pinned dependency for
  durable execution, not Canon-owned application code.
- **Action taken:** none; vendor baseline only.

---

## total_recall

- **Original path:** `/Users/edwardwalker/localwork/total_recall`
- **Current path:** `/Users/edwardwalker/localwork/_deprecated/total_recall`
- **Original label:** absorb
- **Final label:** **absorbed + moved-for-review**
- **Absorption wave:** E3 (graph-first retrieval) / E5 (synthesis read paths).
- **Action taken:** Session-recall concepts unified with canonical
  `retrieval_breakdown` events (E3) and the three synthesis read paths
  (E5). Sibling moved to `_deprecated/total_recall` on 2026-04-23 pending
  post-release review.

---

## Close-out

- **Deletions executed:** 0. No sibling reached the `delete` label.
- **Moves executed:** 3. `mempalace`, `obsidian-mind`, and `total_recall`
  were moved from `/Users/edwardwalker/localwork/` to
  `/Users/edwardwalker/localwork/_deprecated/` on 2026-04-23 pending
  post-release review. `canon-platform`, `canon-systems-v2`, and
  `temporal` were left in place per their `keep` labels.
- **Canonical events:** two event types in `.canon/memory/events.ndjson`:
  `sibling_disposition_finalized` (6, one per sibling) and
  `sibling_moved_for_review` (3, one per moved sibling).
- **Follow-ups:** operator review of `_deprecated/` determines whether the
  three moved siblings are restored, archived elsewhere, or deleted.
  canon-systems has no remaining runtime references to those paths.
