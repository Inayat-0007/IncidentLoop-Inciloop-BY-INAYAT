#!/usr/bin/env node
/**
 * beforeShellExecution: block destructive git, rm -rf, curl|sh, prod reset.
 * Unknown/non-JSON stdin → allow (host terminals). Parsed dangerous commands → deny.
 */
import { readFileSync } from "node:fs";

function allow() {
  process.stdout.write(JSON.stringify({ permission: "allow" }));
  process.exit(0);
}

function deny(agent, user) {
  process.stdout.write(
    JSON.stringify({
      permission: "deny",
      agent_message: agent,
      user_message: user,
    }),
  );
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

const command = String(payload.command ?? payload.commandLine ?? "");
if (!command) allow();

if (/rm\s+(-[a-z]*r[a-z]*f|[a-z]*f[a-z]*r)/i.test(command) || /rmdir\s+\/s/i.test(command)) {
  deny("Blocked recursive delete.", "Recursive delete is not allowed from the agent shell.");
}

if (/git\s+push\s+[^\n]*--force/i.test(command) || /git\s+push\s+[^\n]*\s-f(\s|$)/i.test(command)) {
  deny("Blocked git push --force.", "Force-push is forbidden.");
}

if (/curl\s[^|\n]*\|\s*(ba)?sh/i.test(command) || /wget\s[^|\n]*\|\s*(ba)?sh/i.test(command)) {
  deny("Blocked pipe-to-shell download.", "curl|sh / wget|sh is forbidden.");
}

if (/migrate\s+reset/i.test(command) || /drizzle-kit\s+[^\n]*reset/i.test(command)) {
  deny("Blocked migrate reset.", "Do not reset databases from the agent.");
}

if (
  /\b(npm|pnpm|yarn)\s+(add|i|install)\b/i.test(command) &&
  /--ignore-workspace-root-check|--no-lockfile/i.test(command)
) {
  deny("Blocked install without lockfile discipline.", "Installs must keep the lockfile.");
}

allow();
