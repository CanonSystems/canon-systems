#!/usr/bin/env node
// Optional postinstall: if pipx is available and the Python CLI isn't yet
// installed, suggest (but don't auto-run) the pipx install. We do not
// auto-install into the user's Python environment without consent.

"use strict";

const { spawnSync } = require("node:child_process");

function which(cmd) {
  const r = spawnSync(process.platform === "win32" ? "where" : "which", [cmd], {
    stdio: ["ignore", "pipe", "ignore"],
    encoding: "utf-8",
  });
  if (r.status === 0 && r.stdout) {
    return r.stdout.split(/\r?\n/)[0].trim();
  }
  return "";
}

const hasNative = !!which("canon-memory-layer");
if (hasNative) {
  process.exit(0);
}

const hasPipx = !!which("pipx");
const hint = hasPipx
  ? "  pipx install canon-memory-layer"
  : "  python3 -m pip install --user canon-memory-layer";

console.error(
  [
    "",
    "canon-memory-layer (npx wrapper) installed.",
    "The underlying Python CLI is not on PATH yet. To install it:",
    hint,
    "",
    "Then run: canon-memory-layer --help",
    "",
  ].join("\n"),
);
