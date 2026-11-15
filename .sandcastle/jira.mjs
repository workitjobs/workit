#!/usr/bin/env node
// Sandcastle's bridge to Jira project KAN, over the Jira Cloud REST API.
//
//   node .sandcastle/jira.mjs list               open KAN issues labelled `sandcastle`, as JSON
//   node .sandcastle/jira.mjs view KAN-123       one issue, with its comments
//   node .sandcastle/jira.mjs done KAN-123 "..." comment, then swap the label to `sandcastle-done`
//   node .sandcastle/jira.mjs block KAN-123 "..." comment, then swap the label to `sandcastle-blocked`
//
// Only issues a person has labelled `sandcastle` are ever picked up. `done` does
// not move the issue to Done: the work still sits on an unmerged branch, so a
// person moves it once the PR merges. Swapping the label is what stops the loop
// picking the same issue again.
//
// Env (from .sandcastle/.env): JIRA_EMAIL, JIRA_API_TOKEN, and optionally
// JIRA_BASE_URL (defaults to the team site).

const BASE = (process.env.JIRA_BASE_URL || "https://workitsbu.atlassian.net").replace(/\/$/, "");
const LABEL = "sandcastle";
const { JIRA_EMAIL, JIRA_API_TOKEN } = process.env;

function fail(message) {
  console.error(`jira.mjs: ${message}`);
  process.exit(1);
}

if (!JIRA_EMAIL || !JIRA_API_TOKEN) {
  fail("set JIRA_EMAIL and JIRA_API_TOKEN in .sandcastle/.env (token: https://id.atlassian.com/manage-profile/security/api-tokens)");
}

const auth = "Basic " + Buffer.from(`${JIRA_EMAIL}:${JIRA_API_TOKEN}`).toString("base64");

async function jira(method, path, body) {
  const res = await fetch(`${BASE}/rest/api/3${path}`, {
    method,
    headers: { Authorization: auth, Accept: "application/json", "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) fail(`${method} ${path} -> ${res.status} ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

// Flatten Atlassian Document Format to plain text, keeping block breaks.
function adfToText(node) {
  if (!node) return "";
  if (node.type === "text") return node.text;
  if (node.type === "hardBreak") return "\n";
  const inner = (node.content || []).map(adfToText).join("");
  if (node.type === "listItem") return `- ${inner.trim()}\n`;
  if (node.type === "taskItem") return `- [${node.attrs?.state === "DONE" ? "x" : " "}] ${inner.trim()}\n`;
  if (node.type === "tableRow") return `| ${(node.content || []).map((c) => adfToText(c).trim()).join(" | ")} |\n`;
  if (["bulletList", "orderedList", "taskList", "table"].includes(node.type)) return `${inner}\n`;
  if (["paragraph", "heading", "codeBlock", "blockquote", "panel"].includes(node.type)) return `${inner}\n\n`;
  return inner;
}

function adfParagraphs(text) {
  return {
    type: "doc",
    version: 1,
    content: text.split(/\n{2,}/).map((p) => ({ type: "paragraph", content: [{ type: "text", text: p }] })),
  };
}

function openBlockers(fields) {
  return (fields.issuelinks || [])
    .filter((l) => l.type?.inward === "is blocked by" && l.inwardIssue)
    .filter((l) => l.inwardIssue.fields?.status?.statusCategory?.key !== "done")
    .map((l) => l.inwardIssue.key);
}

async function list() {
  const jql = `project = KAN AND labels = ${LABEL} AND statusCategory != Done ORDER BY priority DESC, created ASC`;
  const fields = "summary,description,issuetype,status,parent,issuelinks";
  const { issues } = await jira("GET", `/search/jql?jql=${encodeURIComponent(jql)}&fields=${fields}&maxResults=50`);
  const out = issues.map(({ key, fields: f }) => ({
    id: key,
    title: f.summary,
    type: f.issuetype?.name,
    status: f.status?.name,
    parent: f.parent?.key ?? null,
    blockedBy: openBlockers(f),
    body: adfToText(f.description).trim(),
  }));
  console.log(JSON.stringify(out, null, 2));
}

async function view(key) {
  const { fields: f } = await jira("GET", `/issue/${key}?fields=summary,description,issuetype,status,parent,issuelinks,comment`);
  const comments = (f.comment?.comments || [])
    .map((c) => `--- ${c.author?.displayName} (${c.created})\n${adfToText(c.body).trim()}`)
    .join("\n\n");
  console.log(
    [
      `${key}: ${f.summary}`,
      `Type: ${f.issuetype?.name}   Status: ${f.status?.name}   Parent: ${f.parent?.key ?? "none"}`,
      `Blocked by (open): ${openBlockers(f).join(", ") || "none"}`,
      "",
      adfToText(f.description).trim() || "(no description)",
      "",
      comments ? `Comments:\n\n${comments}` : "Comments: none",
    ].join("\n"),
  );
}

async function finish(key, message, newLabel) {
  if (!message) fail(`a message is required: node .sandcastle/jira.mjs ${process.argv[2]} ${key} "what happened"`);
  await jira("POST", `/issue/${key}/comment`, { body: adfParagraphs(message) });
  await jira("PUT", `/issue/${key}`, { update: { labels: [{ remove: LABEL }, { add: newLabel }] } });
  console.log(`${key}: commented and relabelled ${newLabel}`);
}

const [cmd, key, ...rest] = process.argv.slice(2);
const message = rest.join(" ");
if (cmd !== "list" && !/^KAN-\d+$/.test(key || "")) fail(`expected an issue key like KAN-123, got "${key ?? ""}"`);

switch (cmd) {
  case "list":
    await list();
    break;
  case "view":
    await view(key);
    break;
  case "done":
    await finish(key, message, "sandcastle-done");
    break;
  case "block":
    await finish(key, message, "sandcastle-blocked");
    break;
  default:
    fail("usage: jira.mjs list | view KEY | done KEY MESSAGE | block KEY MESSAGE");
}
