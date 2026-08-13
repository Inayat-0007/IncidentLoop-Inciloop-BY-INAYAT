#!/usr/bin/env node
import { readFileSync, existsSync } from "node:fs";

function allow() {
  process.stdout.write(JSON.stringify({ permission: "allow" }));
  process.exit(0);
}

let payload = {};
try {
  const input = readFileSync(0, "utf8").trim();
  if (!input) allow();
  payload = JSON.parse(input);
} catch {
  allow();
}

const filePath = String(payload.file ?? payload.path ?? payload.filePath ?? "");
const content = String(payload.content ?? payload.newContent ?? payload.fileContent ?? "");

let text = content;
if (!text && filePath && existsSync(filePath)) {
  try {
    text = readFileSync(filePath, "utf8");
  } catch {
    text = "";
  }
}

const patterns = [
  /-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----/,
  /AKIA[0-9A-Z]{16}/,
  /ghp_[A-Za-z0-9]{20,}/,
  /github_pat_[A-Za-z0-9_]{20,}/,
  /xox[baprs]-[A-Za-z0-9-]{10,}/,
  /sk_live_[A-Za-z0-9]{16,}/,
];

const skip =
  filePath.includes(".env.example") ||
  filePath.includes("block-secrets") ||
  filePath.includes("check-no-secrets") ||
  filePath.includes("VIBE_CODING_STARTER_PACK");

if (!skip && text && patterns.some((re) => re.test(text))) {
  process.stdout.write(
    JSON.stringify({
      permission: "deny",
      agent_message: `Secret-like pattern in ${filePath || "edited file"}. Remove it; use env vars.`,
      user_message: "A secret-like pattern was blocked from being written.",
    }),
  );
  process.exit(0);
}

allow();
