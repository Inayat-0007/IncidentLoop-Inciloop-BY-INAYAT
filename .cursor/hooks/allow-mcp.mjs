#!/usr/bin/env node
import { readFileSync } from "node:fs";

function allow() {
  process.stdout.write(JSON.stringify({ permission: "allow" }));
  process.exit(0);
}

const allowed = new Set(["github", "gitlab"]);
let payload = {};
try {
  const input = readFileSync(0, "utf8").trim();
  if (!input) allow();
  payload = JSON.parse(input);
} catch {
  allow();
}

const server = String(payload.server ?? payload.mcpServer ?? payload.serverName ?? "").toLowerCase();

if (server && !allowed.has(server)) {
  process.stdout.write(
    JSON.stringify({
      permission: "deny",
      agent_message: `MCP server "${server}" is not allowlisted.`,
      user_message: "Only github and gitlab MCP servers are allowed in this repo.",
    }),
  );
  process.exit(0);
}

allow();
