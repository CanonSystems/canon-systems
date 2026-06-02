(function () {
  const HOST_ID = "canon-meet-companion-host";
  const BRIDGE_BASE = "http://127.0.0.1:8765";

  if (document.getElementById(HOST_ID)) {
    return;
  }

  const host = document.createElement("div");
  host.id = HOST_ID;
  document.documentElement.appendChild(host);
  const shadow = host.attachShadow({ mode: "open" });

  const meetingCode = window.location.pathname.split("/").filter(Boolean)[0] || "";
  const storageKey = `canon.meet.session.${meetingCode || "default"}`;

  const state = {
    open: true,
    sessionId: window.localStorage.getItem(storageKey) || "",
    manifest: null,
    busy: false,
    error: "",
    bridgeOk: false,
    uploadName: "",
    transcriptCaptureEnabled: window.localStorage.getItem(`${storageKey}.transcriptCapture`) === "on",
    transcriptStatus: "Idle",
    captionFingerprints: new Set(),
  };

  const UI_NOISE = new Set([
    "People",
    "Take notes with Gemini",
    "Gemini",
    "Meeting details",
    "Chat with everyone",
    "Meeting tools",
    "Host controls",
    "Turn off microphone",
    "Turn off camera",
    "Share screen",
    "Send a reaction",
    "Turn on captions",
    "More options",
    "Leave call",
    "Meeting Dock",
    "Canon Meet Companion",
    "Bridge online",
    "Bridge offline",
  ]);

  const styles = `
    :host {
      all: initial;
    }
    .shell {
      position: fixed;
      top: 18px;
      right: 18px;
      z-index: 2147483647;
      font-family: "Inter", "Avenir Next", sans-serif;
      color: #17242a;
    }
    .toggle {
      position: absolute;
      right: 0;
      top: 18px;
      transform: translateX(100%);
      border: none;
      border-radius: 0 18px 18px 0;
      background: linear-gradient(135deg, #0f766e, #155e75);
      color: #fff;
      padding: 12px 14px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      box-shadow: 0 14px 32px rgba(15, 118, 110, 0.25);
    }
    .panel {
      width: 360px;
      max-height: calc(100vh - 36px);
      overflow: auto;
      background: rgba(255, 250, 242, 0.96);
      border: 1px solid rgba(17, 35, 42, 0.12);
      border-radius: 28px;
      box-shadow: 0 28px 70px rgba(16, 32, 40, 0.25);
      backdrop-filter: blur(20px);
      padding: 16px;
    }
    .panel.closed {
      display: none;
    }
    .eyebrow,
    .label {
      margin: 0;
      font-size: 11px;
      line-height: 1;
      letter-spacing: 0.11em;
      text-transform: uppercase;
      color: #155e75;
      font-weight: 800;
    }
    h1, h2, h3, p {
      margin: 0;
    }
    h1, h2, h3 {
      font-family: "Fraunces", Georgia, serif;
      letter-spacing: -0.02em;
    }
    h1 {
      font-size: 26px;
      line-height: 0.95;
      margin-top: 6px;
    }
    h2 {
      font-size: 18px;
      line-height: 1.05;
    }
    h3 {
      font-size: 16px;
      line-height: 1.08;
    }
    .muted, .subtle {
      color: #5f6d72;
    }
    .stack {
      display: grid;
      gap: 10px;
    }
    .section {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid rgba(17, 35, 42, 0.1);
    }
    .hero {
      display: grid;
      gap: 10px;
      padding: 14px;
      border-radius: 22px;
      background:
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.12), transparent 36%),
        rgba(255, 255, 255, 0.72);
      border: 1px solid rgba(17, 35, 42, 0.08);
    }
    .toolbar,
    .stats,
    .actions,
    .queue-actions {
      display: grid;
      gap: 8px;
    }
    .toolbar {
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: end;
    }
    .stats {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .stat {
      padding: 10px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.65);
      border: 1px solid rgba(21, 94, 117, 0.08);
    }
    .stat strong {
      display: block;
      font-size: 18px;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 13px;
      font-weight: 700;
    }
    input, textarea, select, button {
      font: inherit;
    }
    input, textarea, select {
      width: 100%;
      min-height: 42px;
      padding: 10px 12px;
      border-radius: 14px;
      border: 1px solid rgba(17, 35, 42, 0.14);
      background: rgba(255, 255, 255, 0.85);
      color: #17242a;
    }
    textarea {
      min-height: 84px;
      resize: vertical;
    }
    input[type="file"] {
      padding: 8px;
      background: rgba(15, 118, 110, 0.06);
    }
    .checkbox {
      display: grid;
      grid-template-columns: auto 1fr;
      align-items: center;
      gap: 10px;
    }
    .checkbox input {
      width: 18px;
      min-height: 18px;
      margin: 0;
    }
    button {
      min-height: 42px;
      border: none;
      border-radius: 999px;
      padding: 0 14px;
      cursor: pointer;
      font-weight: 800;
    }
    .primary {
      background: linear-gradient(135deg, #0f766e, #155e75);
      color: #fff;
    }
    .ghost {
      background: rgba(15, 118, 110, 0.1);
      color: #155e75;
    }
    .danger {
      background: rgba(124, 45, 18, 0.12);
      color: #7c2d12;
    }
    .queue {
      display: grid;
      gap: 8px;
    }
    .queue-item {
      padding: 12px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.66);
      border: 1px solid rgba(21, 94, 117, 0.08);
    }
    code {
      display: inline-block;
      margin-bottom: 6px;
      padding: 4px 8px;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.1);
      color: #155e75;
      font-size: 11px;
      font-family: "SFMono-Regular", Menlo, monospace;
    }
    .queue-actions {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      margin-top: 8px;
    }
    .actions {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .actions .full {
      grid-column: 1 / -1;
    }
    .status-line {
      min-height: 18px;
      font-size: 12px;
      color: #5f6d72;
    }
    .status-line.error {
      color: #7c2d12;
    }
    .bridge-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 24px;
      padding: 0 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: rgba(15, 118, 110, 0.1);
      color: #155e75;
    }
    .bridge-pill.offline {
      background: rgba(124, 45, 18, 0.12);
      color: #7c2d12;
    }
    .empty {
      color: #5f6d72;
      font-size: 13px;
    }
  `;

  function escapeHtml(value) {
    return String(value || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  async function api(path, options = {}) {
    const response = await fetch(`${BRIDGE_BASE}${path}`, options);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || `Request failed (${response.status})`);
    }
    return payload;
  }

  function saveSessionId(value) {
    state.sessionId = value.trim();
    if (state.sessionId) {
      window.localStorage.setItem(storageKey, state.sessionId);
    } else {
      window.localStorage.removeItem(storageKey);
    }
  }

  function saveTranscriptCaptureEnabled(value) {
    state.transcriptCaptureEnabled = value;
    window.localStorage.setItem(`${storageKey}.transcriptCapture`, value ? "on" : "off");
  }

  async function refresh() {
    if (!state.sessionId) {
      state.manifest = null;
      state.busy = false;
      if (meetingCode) {
        try {
          const payload = await api(`/resolve-session?meeting_code=${encodeURIComponent(meetingCode)}`);
          if (payload?.match?.session_id) {
            saveSessionId(payload.match.session_id);
          }
        } catch (error) {
          state.bridgeOk = false;
          state.error = "Set a session ID to connect this meeting.";
          render();
          return;
        }
      } else {
        state.bridgeOk = false;
        state.error = "Set a session ID to connect this meeting.";
        render();
        return;
      }
    }
    try {
      const payload = await api(`/sessions/${encodeURIComponent(state.sessionId)}/panel-manifest`);
      state.bridgeOk = true;
      state.manifest = payload.panel_manifest;
      state.error = "";
      state.busy = false;
    } catch (error) {
      state.bridgeOk = false;
      state.error = error.message;
      state.busy = false;
    }
    render();
  }

  async function postJson(path, body) {
    state.busy = true;
    state.error = "";
    render();
    try {
      await api(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await refresh();
    } catch (error) {
      state.error = error.message;
      state.busy = false;
      render();
    }
  }

  async function sendEvent(event, { silent = false } = {}) {
    if (!silent) {
      state.busy = true;
      state.error = "";
      render();
    }
    try {
      await api(`/sessions/${encodeURIComponent(state.sessionId)}/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(event),
      });
      await refresh();
    } catch (error) {
      state.error = error.message;
      state.busy = false;
      render();
    }
  }

  async function uploadReference(form) {
    if (!state.sessionId) {
      state.error = "Set a session ID first.";
      render();
      return;
    }
    state.busy = true;
    state.error = "";
    render();
    try {
      await api(`/sessions/${encodeURIComponent(state.sessionId)}/upload-reference`, {
        method: "POST",
        body: form,
      });
      await refresh();
    } catch (error) {
      state.error = error.message;
      state.busy = false;
      render();
    }
  }

  function normalizeText(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .replace(/\u200B/g, "")
      .trim();
  }

  function inferCaptionSegment(text) {
    const lines = String(text || "")
      .split("\n")
      .map((line) => normalizeText(line))
      .filter(Boolean);
    if (!lines.length) {
      return null;
    }
    if (lines.length >= 2 && lines[0].length <= 48) {
      return {
        speaker: lines[0],
        text: lines.slice(1).join(" "),
      };
    }
    return {
      speaker: "Meeting caption",
      text: lines.join(" "),
    };
  }

  function isLikelyCaptionNode(node) {
    if (!(node instanceof HTMLElement)) {
      return false;
    }
    if (host.contains(node)) {
      return false;
    }
    const rect = node.getBoundingClientRect();
    if (!rect.width || !rect.height) {
      return false;
    }
    if (rect.bottom < window.innerHeight * 0.35 || rect.top > window.innerHeight * 0.96) {
      return false;
    }
    if (rect.width > window.innerWidth * 0.9) {
      return false;
    }
    return true;
  }

  function isLikelyCaptionText(text) {
    const normalized = normalizeText(text);
    if (!normalized || normalized.length < 6 || normalized.length > 280) {
      return false;
    }
    if (UI_NOISE.has(normalized)) {
      return false;
    }
    if (normalized.startsWith("https://") || normalized.startsWith("meet.google.com/")) {
      return false;
    }
    if (/^[0-9: AMPamp\-]+$/.test(normalized)) {
      return false;
    }
    return true;
  }

  async function captureTranscriptFromMeet() {
    if (!state.transcriptCaptureEnabled || !state.sessionId) {
      return;
    }
    const liveNodes = [...document.querySelectorAll('[aria-live="polite"], [aria-live="assertive"], [role="alert"]')]
      .filter(isLikelyCaptionNode);
    let sent = 0;
    for (const node of liveNodes) {
      const raw = normalizeText(node.innerText || node.textContent || "");
      if (!isLikelyCaptionText(raw)) {
        continue;
      }
      const segment = inferCaptionSegment(raw);
      if (!segment || !isLikelyCaptionText(segment.text)) {
        continue;
      }
      const fingerprint = `${segment.speaker}::${segment.text}`;
      if (state.captionFingerprints.has(fingerprint)) {
        continue;
      }
      state.captionFingerprints.add(fingerprint);
      if (state.captionFingerprints.size > 250) {
        const [first] = state.captionFingerprints;
        state.captionFingerprints.delete(first);
      }
      await sendEvent({
        type: "transcript.segment",
        payload: {
          speaker: segment.speaker,
          text: segment.text,
          source: "meet-caption-capture",
        },
      }, { silent: true });
      sent += 1;
    }
    const nextStatus = sent ? `Captured ${sent} segment${sent === 1 ? "" : "s"}` : "Listening for captions";
    if (state.transcriptStatus !== nextStatus) {
      state.transcriptStatus = nextStatus;
      render();
    }
  }

  setInterval(() => {
    captureTranscriptFromMeet().catch((error) => {
      state.transcriptStatus = `Capture error: ${error.message}`;
      render();
    });
  }, 2000);

  function pendingItemMarkup(item) {
    return `
      <div class="queue-item">
        <code>${escapeHtml(item.item_id)}</code>
        <strong>${escapeHtml(item.title)}</strong>
        <div class="subtle">${escapeHtml(item.type)} · ${escapeHtml(item.status)}</div>
        <p class="subtle">${escapeHtml(item.verification_prompt || "")}</p>
        <div class="queue-actions">
          <button class="primary" data-action="confirm-item" data-item-id="${escapeHtml(item.item_id)}" data-status="confirmed">Confirm</button>
          <button class="danger" data-action="confirm-item" data-item-id="${escapeHtml(item.item_id)}" data-status="rejected">Reject</button>
        </div>
      </div>
    `;
  }

  function pendingHandMarkup(item) {
    return `
      <div class="queue-item">
        <code>${escapeHtml(item.hand_raise_id)}</code>
        <strong>${escapeHtml(item.reason)}</strong>
        <div class="subtle">${escapeHtml(item.status)}${item.item_id ? ` · ${escapeHtml(item.item_id)}` : ""}</div>
        <div class="queue-actions">
          <button class="primary" data-action="resolve-hand" data-hand-id="${escapeHtml(item.hand_raise_id)}" data-status="approved">Approve</button>
          <button class="ghost" data-action="resolve-hand" data-hand-id="${escapeHtml(item.hand_raise_id)}" data-status="dismissed">Dismiss</button>
        </div>
      </div>
    `;
  }

  function recentReferenceMarkup(item) {
    return `
      <div class="queue-item">
        <code>${escapeHtml(item.ref_id)}</code>
        <strong>${escapeHtml(item.title)}</strong>
        <div class="subtle">${escapeHtml(item.type)} · ${escapeHtml(item.meeting_chat_status)}</div>
      </div>
    `;
  }

  function recentTranscriptMarkup(item) {
    return `
      <div class="queue-item">
        <code>${escapeHtml(item.segment_id)}</code>
        <strong>${escapeHtml(item.speaker)}</strong>
        <div class="subtle">${escapeHtml(item.text)}</div>
      </div>
    `;
  }

  function render() {
    const manifest = state.manifest;
    const meeting = manifest?.meeting || {};
    const status = manifest?.status || {};
    const pendingItems = manifest?.pending_items || [];
    const pendingHands = manifest?.pending_hand_raises || [];
    const recentReferences = manifest?.recent_references || [];
    const recentTranscriptSegments = manifest?.recent_transcript_segments || [];
    const bridgeClass = state.bridgeOk ? "bridge-pill" : "bridge-pill offline";

    shadow.innerHTML = `
      <style>${styles}</style>
      <div class="shell">
        <button class="toggle" data-action="toggle">${state.open ? "Hide Canon" : "Canon"}</button>
        <div class="panel ${state.open ? "" : "closed"}">
          <div class="hero">
            <p class="eyebrow">Canon Meet Companion</p>
            <h1>Meeting Dock</h1>
            <p class="muted">Bridge the live room to Canon memory, verified tasks, and the Cursor handoff path.</p>
            <span class="${bridgeClass}">${state.bridgeOk ? "Bridge online" : "Bridge offline"}</span>
          </div>

          <div class="section stack">
            <div class="toolbar">
              <label>
                <span class="label">Session ID</span>
                <input id="session-id" type="text" value="${escapeHtml(state.sessionId)}" placeholder="meeting-..." />
              </label>
              <button class="primary" data-action="connect">Connect</button>
            </div>
            <div class="status-line ${state.error ? "error" : ""}">${escapeHtml(state.error || "")}</div>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Meeting State</p>
              <h2>${escapeHtml(manifest?.plan_id || "No plan loaded")}</h2>
              <p class="muted">${escapeHtml(meeting.meeting_uri || window.location.href)}</p>
            </div>
            <div class="stats">
              <div class="stat">
                <strong>${status.pending_plan_items || 0}</strong>
                <span class="subtle">Pending items</span>
              </div>
              <div class="stat">
                <strong>${status.pending_hand_raises || 0}</strong>
                <span class="subtle">Hands</span>
              </div>
              <div class="stat">
                <strong>${status.reference_count || 0}</strong>
                <span class="subtle">Evidence</span>
              </div>
            </div>
            <div class="actions">
              <button class="ghost" data-action="refresh">Refresh</button>
              <button class="ghost" data-action="open-console">Open full console</button>
            </div>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Quick Upload</p>
              <h3>Send visible evidence</h3>
            </div>
            <form id="upload-form" class="stack">
              <label>
                <span class="label">File</span>
                <input id="upload-file" name="file" type="file" required />
              </label>
              <label>
                <span class="label">Title</span>
                <input name="title" type="text" placeholder="Error screenshot" />
              </label>
              <label>
                <span class="label">Summary</span>
                <textarea name="summary" placeholder="Why this artifact matters."></textarea>
              </label>
              <label class="checkbox">
                <input name="shared_to_meeting" type="checkbox" checked />
                <span>Already visible to the meeting</span>
              </label>
              <input name="type" type="hidden" value="image" />
              <button class="primary" type="submit">${state.busy ? "Working..." : "Upload to Canon"}</button>
            </form>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Transcript</p>
              <h3>Capture the room</h3>
            </div>
            <form id="transcript-form" class="stack">
              <label>
                <span class="label">Speaker</span>
                <input name="speaker" type="text" placeholder="Edward Walker" />
              </label>
              <label>
                <span class="label">Text</span>
                <textarea name="text" placeholder="Paste a verbatim segment or room summary."></textarea>
              </label>
              <div class="actions">
                <button class="primary" type="submit">Add transcript</button>
                <button class="ghost" type="button" data-action="toggle-transcript-capture">${state.transcriptCaptureEnabled ? "Stop caption capture" : "Start caption capture"}</button>
              </div>
              <div class="status-line">${escapeHtml(state.transcriptStatus)}</div>
            </form>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Plan Item</p>
              <h3>Propose wording</h3>
            </div>
            <form id="item-form" class="stack">
              <label>
                <span class="label">Type</span>
                <select name="item_type">
                  <option value="task">Task</option>
                  <option value="decision">Decision</option>
                  <option value="open_question">Open question</option>
                  <option value="assumption">Assumption</option>
                </select>
              </label>
              <label>
                <span class="label">Title</span>
                <input name="title" type="text" placeholder="Split auth and UI work" required />
              </label>
              <label>
                <span class="label">Content</span>
                <textarea name="content" placeholder="Exact wording for the read-back." required></textarea>
              </label>
              <label>
                <span class="label">Evidence refs</span>
                <input name="evidence_refs" type="text" placeholder="ref-001, ref-002" />
              </label>
              <button class="primary" type="submit">Propose item</button>
            </form>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">AI Voice</p>
              <h3>Raise hand or switch mode</h3>
            </div>
            <form id="hand-form" class="stack">
              <label>
                <span class="label">Reason</span>
                <input name="reason" type="text" placeholder="Need to clarify scope." required />
              </label>
              <div class="actions">
                <button class="primary" type="submit">Raise hand</button>
                <button class="ghost" type="button" data-action="set-mode" data-mode="prompted">Prompted</button>
                <button class="ghost full" type="button" data-action="set-mode" data-mode="independent-hand-raise">Independent hand raise</button>
              </div>
            </form>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Pending Items</p>
              <h3>Verification queue</h3>
            </div>
            <div class="queue">
              ${pendingItems.length ? pendingItems.map(pendingItemMarkup).join("") : '<p class="empty">No pending items.</p>'}
            </div>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Pending Hands</p>
              <h3>Bot interjections</h3>
            </div>
            <div class="queue">
              ${pendingHands.length ? pendingHands.map(pendingHandMarkup).join("") : '<p class="empty">No pending hand raises.</p>'}
            </div>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Recent Evidence</p>
              <h3>What Canon last captured</h3>
            </div>
            <div class="queue">
              ${recentReferences.length ? recentReferences.map(recentReferenceMarkup).join("") : '<p class="empty">No recent references.</p>'}
            </div>
          </div>

          <div class="section stack">
            <div>
              <p class="eyebrow">Recent Transcript</p>
              <h3>What Canon heard</h3>
            </div>
            <div class="queue">
              ${recentTranscriptSegments.length ? recentTranscriptSegments.map(recentTranscriptMarkup).join("") : '<p class="empty">No transcript segments yet.</p>'}
            </div>
          </div>
        </div>
      </div>
    `;

    shadow.querySelector('[data-action="toggle"]').addEventListener("click", () => {
      state.open = !state.open;
      render();
    });

    shadow.querySelector('[data-action="connect"]').addEventListener("click", async () => {
      const next = shadow.querySelector("#session-id").value;
      saveSessionId(next);
      await refresh();
    });

    shadow.querySelector('[data-action="refresh"]').addEventListener("click", refresh);
    shadow.querySelector('[data-action="open-console"]').addEventListener("click", () => {
      const target = `${BRIDGE_BASE}/app?session_id=${encodeURIComponent(state.sessionId || "")}`;
      window.open(target, "_blank", "noopener,noreferrer");
    });

    shadow.querySelector("#upload-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      await uploadReference(form);
      event.currentTarget.reset();
    });

    shadow.querySelector("#transcript-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      await sendEvent({
        type: "transcript.segment",
        payload: {
          speaker: form.get("speaker") || "Meeting participant",
          text: form.get("text"),
          source: "meet-dock-manual",
        },
      });
      event.currentTarget.reset();
    });

    shadow.querySelector("#item-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      await sendEvent({
        type: "item.propose",
        payload: {
          item_type: form.get("item_type"),
          title: form.get("title"),
          content: form.get("content"),
          evidence_refs: String(form.get("evidence_refs") || "")
            .split(",")
            .map((entry) => entry.trim())
            .filter(Boolean),
          requires_confirmation: true,
        },
      });
      event.currentTarget.reset();
    });

    shadow.querySelector("#hand-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = new FormData(event.currentTarget);
      await postJson(`/sessions/${encodeURIComponent(state.sessionId)}/events`, {
        type: "hand.raise",
        payload: { reason: form.get("reason") },
      });
      event.currentTarget.reset();
    });

    for (const button of shadow.querySelectorAll('[data-action="set-mode"]')) {
      button.addEventListener("click", async () => {
        await postJson(`/sessions/${encodeURIComponent(state.sessionId)}/events`, {
          type: "mode.set",
          payload: { mode: button.dataset.mode },
        });
      });
    }

    shadow.querySelector('[data-action="toggle-transcript-capture"]').addEventListener("click", () => {
      saveTranscriptCaptureEnabled(!state.transcriptCaptureEnabled);
      state.transcriptStatus = state.transcriptCaptureEnabled ? "Listening for captions" : "Caption capture paused";
      render();
    });

    for (const button of shadow.querySelectorAll('[data-action="confirm-item"]')) {
      button.addEventListener("click", async () => {
        await postJson(`/sessions/${encodeURIComponent(state.sessionId)}/events`, {
          type: "item.confirm",
          payload: {
            item_id: button.dataset.itemId,
            status: button.dataset.status,
          },
        });
      });
    }

    for (const button of shadow.querySelectorAll('[data-action="resolve-hand"]')) {
      button.addEventListener("click", async () => {
        await postJson(`/sessions/${encodeURIComponent(state.sessionId)}/events`, {
          type: "hand.resolve",
          payload: {
            hand_raise_id: button.dataset.handId,
            status: button.dataset.status,
          },
        });
      });
    }
  }

  render();
  refresh();
})();
