#!/usr/bin/env node
// Thin npx wrapper for canon-memory-layer.
// Delegates to the pipx/pip-installed Python CLI if present; otherwise, runs
// via `python3 -m memory_layer.cli` if the package was installed as a Python
// dependency in a local venv.
//
// The actual memory-layer logic lives in the Python package. This wrapper
// exists so Node-native workflows can `npx canon-memory-layer <cmd>` without
// touching pipx explicitly.

"use strict";

const { spawnSync } = require("node:child_process");
const { existsSync } = require("node:fs");
const path = require("node:path");

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

function tryRun(cmd, args) {
  const r = spawnSync(cmd, args, { stdio: "inherit" });
  return r.status ?? 1;
}

function main() {
  const args = process.argv.slice(2);

  // 1) Native CLI installed globally via pipx / pip --user.
  const native = which("canon-memory-layer");
  if (native && !native.endsWith(path.basename(process.argv[1]))) {
    // Avoid infinite self-recursion if this very script is on PATH.
    process.exit(tryRun(native, args));
  }

  // 2) `python3 -m memory_layer.cli` (assumes memory_layer importable).
  const py = which("python3") || which("python");
  if (py) {
    const probe = spawnSync(py, ["-c", "import memory_layer"], {
      stdio: "ignore",
    });
    if (probe.status === 0) {
      process.exit(tryRun(py, ["-m", "memory_layer.cli", ...args]));
    }
  }

  // 3) Nothing available — instruct the user.
  console.error(
    [
      "canon-memory-layer is not installed on this machine.",
      "Install it with one of:",
      "  pipx install canon-memory-layer",
      "  python3 -m pip install --user canon-memory-layer",
      "  (or from source: pipx install /path/to/canon-memory-layer)",
      "",
      "Then re-run: npx canon-memory-layer " + args.join(" "),
    ].join("\n"),
  );
  process.exit(127);
}

main();
