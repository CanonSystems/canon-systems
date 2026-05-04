import { Agent } from "@cursor/sdk";
import process from "node:process";

const requestedAt = new Date().toISOString();

function env(name, fallback = "") {
  return (process.env[name] ?? fallback).trim();
}

function requireEnv(name) {
  const value = env(name);
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function summarizeRuntime() {
  const runtime = env("CURSOR_POC_RUNTIME", "local");
  if (runtime === "local") {
    return {
      runtime,
      config: {
        cwd: env("CURSOR_POC_CWD", process.cwd())
      }
    };
  }
  if (runtime === "cloud") {
    return {
      runtime,
      config: {
        repos: [
          {
            url: requireEnv("CURSOR_POC_REPO_URL"),
            startingRef: env("CURSOR_POC_STARTING_REF", "main")
          }
        ],
        autoCreatePR: env("CURSOR_POC_AUTO_CREATE_PR", "0") === "1"
      }
    };
  }
  throw new Error(
    `Unsupported CURSOR_POC_RUNTIME=${runtime}. Expected "local" or "cloud".`
  );
}

function buildPrompt() {
  return env(
    "CURSOR_POC_PROMPT",
    "Create a short repository summary, identify one low-risk improvement, and stop without changing code."
  );
}

async function readAwsTaskMetadata() {
  const uri = env("ECS_CONTAINER_METADATA_URI_V4");
  if (!uri || typeof fetch !== "function") {
    return {};
  }
  try {
    const response = await fetch(`${uri}/task`, { signal: AbortSignal.timeout(2000) });
    if (!response.ok) {
      return { metadataStatus: response.status };
    }
    const payload = await response.json();
    return {
      cluster: payload.Cluster ?? "",
      taskArn: payload.TaskARN ?? "",
      family: payload.Family ?? "",
      revision: payload.Revision ?? ""
    };
  } catch (error) {
    return { metadataError: error instanceof Error ? error.message : String(error) };
  }
}

function sanitizeError(error) {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
      stack: error.stack
    };
  }
  return { message: String(error) };
}

function emit(payload, stream = process.stdout) {
  stream.write(`${JSON.stringify(payload)}\n`);
}

async function main() {
  const apiKey = requireEnv("CURSOR_API_KEY");
  const modelId = env("CURSOR_POC_MODEL", "composer-2");
  const { runtime, config } = summarizeRuntime();
  const prompt = buildPrompt();
  const aws = await readAwsTaskMetadata();
  const baseEvidence = {
    requestedAt,
    runtime,
    modelId,
    repoUrl: runtime === "cloud" ? config.repos?.[0]?.url ?? "" : "",
    startingRef: runtime === "cloud" ? config.repos?.[0]?.startingRef ?? "" : "",
    localCwd: runtime === "local" ? config.cwd ?? "" : "",
    aws
  };

  emit(
    {
      phase: "create_agent",
      ...baseEvidence,
      prompt
    },
    process.stderr
  );

  const agent = await Agent.create({
    apiKey,
    model: { id: modelId },
    [runtime]: config
  });

  const run = await agent.send(prompt);
  emit(
    {
      phase: "run_started",
      ...baseEvidence,
      cursorAgentId: run.agentId,
      cursorRunId: run.id
    },
    process.stderr
  );

  let eventCount = 0;
  for await (const event of run.stream()) {
    eventCount += 1;
    emit({ phase: "cursor_event", eventCount, event });
  }

  const result = await run.wait();
  emit({
    phase: "run_complete",
    ...baseEvidence,
    cursorAgentId: run.agentId,
    cursorRunId: run.id,
    eventCount,
    status: result.status ?? "",
    durationMs: result.durationMs ?? null,
    resultText: result.result ?? "",
    gitMetadata: result.git ?? {},
    result
  });
}

main().catch((error) => {
  emit(
    {
      phase: "error",
      requestedAt,
      error: sanitizeError(error)
    },
    process.stderr
  );
  process.exitCode = 1;
});
