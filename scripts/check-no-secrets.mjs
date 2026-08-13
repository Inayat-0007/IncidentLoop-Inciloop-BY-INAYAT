#!/usr/bin/env node
import { execSync } from "node:child_process";

const patterns = [
  "-----BEGIN .*PRIVATE KEY-----",
  "AKIA[0-9A-Z]{16}",
  "ghp_[A-Za-z0-9]{20,}",
  "github_pat_[A-Za-z0-9_]{20,}",
  "xox[baprs]-",
  "sk_live_[A-Za-z0-9]{16,}",
];

let files = "";
try {
  files = execSync("git diff --cached --name-only --diff-filter=ACM", {
    encoding: "utf8",
  });
} catch {
  process.exit(0);
}

const skip = new Set([
  ".env.example",
  "scripts/check-no-secrets.mjs",
  "scripts/check-no-secrets.sh",
  ".cursor/hooks/block-secrets.mjs",
]);

for (const file of files.split(/\r?\n/).filter(Boolean)) {
  if (skip.has(file.replaceAll("\\", "/"))) continue;
  if (file.endsWith(".env")) {
    console.error(`Refusing to commit ${file}`);
    process.exit(1);
  }
  let content = "";
  try {
    content = execSync(`git show :"${file}"`, { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] });
  } catch {
    continue;
  }
  for (const source of patterns) {
    if (new RegExp(source).test(content)) {
      console.error(`Secret-like pattern in ${file}`);
      process.exit(1);
    }
  }
}

process.exit(0);
