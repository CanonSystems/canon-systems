const query = new URLSearchParams(window.location.search);

const state = {
  sessionId: query.get("session_id") || "",
};

const els = {
  sessionId: document.querySelector("#session-id"),
  loadSession: document.querySelector("#load-session"),
  refreshManifest: document.querySelector("#refresh-manifest"),
  heroTitle: document.querySelector("#hero-title"),
  heroSubtitle: document.querySelector("#hero-subtitle"),
  pendingItems: document.querySelector("#pending-items"),
  pendingHands: document.querySelector("#pending-hands"),
  referenceCount: document.querySelector("#reference-count"),
  transcriptCount: document.querySelector("#transcript-count"),
  meetingSpace: document.querySelector("#meeting-space"),
  meetingMode: document.querySelector("#meeting-mode"),
  meetingMedia: document.querySelector("#meeting-media"),
  meetingLink: document.querySelector("#meeting-link"),
  eventLog: document.querySelector("#event-log"),
  participantList: document.querySelector("#participant-list"),
  pendingItemList: document.querySelector("#pending-item-list"),
  pendingHandList: document.querySelector("#pending-hand-list"),
  recentReferenceList: document.querySelector("#recent-reference-list"),
  recentTranscriptList: document.querySelector("#recent-transcript-list"),
  transcriptForm: document.querySelector("#transcript-form"),
  referenceForm: document.querySelector("#reference-form"),
  referenceUploadForm: document.querySelector("#reference-upload-form"),
  referenceFile: document.querySelector("#reference-file"),
  referenceFileMeta: document.querySelector("#reference-file-meta"),
  itemForm: document.querySelector("#item-form"),
  confirmForm: document.querySelector("#confirm-form"),
  handForm: document.querySelector("#hand-form"),
  resolveHandForm: document.querySelector("#resolve-hand-form"),
  modeForm: document.querySelector("#mode-form"),
};

function setLog(payload) {
  els.eventLog.textContent = JSON.stringify(payload, null, 2);
}

function renderQueue(container, items, renderItem, emptyText) {
  container.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = emptyText;
    container.appendChild(empty);
    return;
  }
  for (const item of items) {
    const card = document.createElement("div");
    card.className = "queue-item";
    card.innerHTML = renderItem(item);
    container.appendChild(card);
  }
}

function renderParticipants(participants) {
  els.participantList.innerHTML = "";
  if (!participants.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No participants loaded.";
    els.participantList.appendChild(empty);
    return;
  }
  for (const participant of participants) {
    const chip = document.createElement("div");
    chip.className = "participant-chip";
    chip.innerHTML = `
      <strong>${participant.name || "Unknown participant"}</strong>
      <span>${participant.email || "No email provided"}</span>
      <div>${participant.voice_profile_status || "unknown"}</div>
    `;
    els.participantList.appendChild(chip);
  }
}

function updateFileMeta() {
  const file = els.referenceFile.files?.[0];
  if (!file) {
    els.referenceFileMeta.textContent = "No file selected.";
    return;
  }
  const sizeKb = Math.max(1, Math.round(file.size / 1024));
  els.referenceFileMeta.textContent = `${file.name} · ${sizeKb} KB`;
  const titleInput = els.referenceUploadForm.querySelector('input[name="title"]');
  if (titleInput && !titleInput.value.trim()) {
    titleInput.value = file.name.replace(/\.[^.]+$/, "").replace(/[-_]+/g, " ");
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
    ...options,
  });
  const json = await response.json();
  if (!response.ok) {
    throw new Error(json.error || `Request failed (${response.status})`);
  }
  return json;
}

function currentSessionId() {
  return (els.sessionId.value || "").trim();
}

function currentSessionPath(suffix) {
  return `/sessions/${currentSessionId()}/${suffix}`;
}

async function refreshManifest() {
  const sessionId = currentSessionId();
  if (!sessionId) {
    els.heroTitle.textContent = "No session loaded";
    els.heroSubtitle.textContent = "Enter a Canon session ID or open /app?session_id=<id>.";
    return;
  }
  const payload = await api(currentSessionPath("panel-manifest"));
  const manifest = payload.panel_manifest;
  state.sessionId = sessionId;

  els.heroTitle.textContent = manifest.plan_id;
  els.heroSubtitle.textContent = `Transport: ${manifest.meeting.transport_adapter}. Media attached: ${manifest.meeting.media_attached ? "yes" : "no"}. Verification stays visible until the room resolves it.`;
  els.pendingItems.textContent = String(manifest.status.pending_plan_items);
  els.pendingHands.textContent = String(manifest.status.pending_hand_raises);
  els.referenceCount.textContent = String(manifest.status.reference_count);
  els.transcriptCount.textContent = String(manifest.status.transcript_segment_count);
  els.meetingSpace.textContent = manifest.meeting.space || "Not bound";
  els.meetingMode.textContent = manifest.meeting.participant_mode || "unknown";
  els.meetingMedia.textContent = manifest.meeting.media_attached ? "Attached" : "Not attached";
  els.meetingLink.textContent = manifest.meeting.meeting_uri || "No meeting URL";
  els.meetingLink.href = manifest.meeting.meeting_uri || "#";
  els.modeForm.querySelector('select[name="mode"]').value = manifest.meeting.participant_mode || "prompted";

  renderParticipants(manifest.participants || []);
  renderQueue(
    els.pendingItemList,
    manifest.pending_items || [],
    (item) => `
      <code>${item.item_id}</code>
      <strong>${item.title}</strong>
      <div>${item.type} · ${item.status}</div>
      <p>${item.verification_prompt || ""}</p>
    `,
    "No pending items."
  );
  renderQueue(
    els.pendingHandList,
    manifest.pending_hand_raises || [],
    (item) => `
      <code>${item.hand_raise_id}</code>
      <strong>${item.reason}</strong>
      <div>${item.status}${item.item_id ? ` · ${item.item_id}` : ""}</div>
    `,
    "No pending hand raises."
  );
  renderQueue(
    els.recentReferenceList,
    manifest.recent_references || [],
    (item) => `
      <code>${item.ref_id}</code>
      <strong>${item.title}</strong>
      <div>${item.type} · ${item.meeting_chat_status}</div>
      <p>${item.path || item.uri || ""}</p>
    `,
    "No references yet."
  );
  renderQueue(
    els.recentTranscriptList,
    manifest.recent_transcript_segments || [],
    (item) => `
      <code>${item.segment_id}</code>
      <strong>${item.speaker}</strong>
      <p>${item.text}</p>
    `,
    "No transcript yet."
  );
  setLog(payload);
}

async function sendEvent(event) {
  const sessionId = currentSessionId();
  if (!sessionId) {
    throw new Error("Enter a session ID first.");
  }
  const payload = await api(currentSessionPath("events"), {
    method: "POST",
    body: JSON.stringify(event),
  });
  setLog(payload);
  await refreshManifest();
}

async function uploadReference(formData) {
  const sessionId = currentSessionId();
  if (!sessionId) {
    throw new Error("Enter a session ID first.");
  }
  const payload = await api(currentSessionPath("upload-reference"), {
    method: "POST",
    body: formData,
  });
  setLog(payload);
  await refreshManifest();
}

function commaList(value) {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

els.loadSession.addEventListener("click", async () => {
  try {
    await refreshManifest();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.refreshManifest.addEventListener("click", async () => {
  try {
    await refreshManifest();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.referenceFile.addEventListener("change", updateFileMeta);

els.transcriptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.transcriptForm);
  try {
    await sendEvent({
      type: "transcript.segment",
      payload: {
        speaker: form.get("speaker"),
        text: form.get("text"),
        source: "meeting-pane-ui",
      },
    });
    els.transcriptForm.reset();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.referenceUploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.referenceUploadForm);
  try {
    await uploadReference(form);
    els.referenceUploadForm.reset();
    updateFileMeta();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.referenceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.referenceForm);
  const path = String(form.get("path") || "");
  try {
    await sendEvent({
      type: "reference.add",
      payload: {
        type: form.get("type"),
        title: form.get("title"),
        path: path.startsWith("http") ? "" : path,
        uri: path.startsWith("http") ? path : "",
        summary: form.get("summary"),
        shared_to_meeting: form.get("shared_to_meeting") === "on",
        meeting_chat_status: form.get("shared_to_meeting") === "on" ? "posted" : "not_requested",
      },
    });
    els.referenceForm.reset();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.itemForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.itemForm);
  try {
    await sendEvent({
      type: "item.propose",
      payload: {
        item_type: form.get("item_type"),
        title: form.get("title"),
        content: form.get("content"),
        evidence_refs: commaList(String(form.get("evidence_refs") || "")),
        requires_confirmation: true,
      },
    });
    els.itemForm.reset();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.confirmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.confirmForm);
  try {
    await sendEvent({
      type: "item.confirm",
      payload: {
        item_id: form.get("item_id"),
        status: form.get("status"),
        title: form.get("title"),
        content: form.get("content"),
      },
    });
    els.confirmForm.reset();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.handForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.handForm);
  try {
    await sendEvent({
      type: "hand.raise",
      payload: {
        reason: form.get("reason"),
      },
    });
    els.handForm.reset();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.resolveHandForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.resolveHandForm);
  try {
    await sendEvent({
      type: "hand.resolve",
      payload: {
        hand_raise_id: form.get("hand_raise_id"),
        status: form.get("status"),
      },
    });
    els.resolveHandForm.reset();
  } catch (error) {
    setLog({ error: error.message });
  }
});

els.modeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(els.modeForm);
  try {
    await sendEvent({
      type: "mode.set",
      payload: {
        mode: form.get("mode"),
      },
    });
  } catch (error) {
    setLog({ error: error.message });
  }
});

if (state.sessionId) {
  els.sessionId.value = state.sessionId;
  refreshManifest().catch((error) => setLog({ error: error.message }));
}
