/* Fail the build if JSX swallowed a space between an inserted number and the next word ("50%the", "0.82for"). */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const bad = [];
function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) { if (name !== "data") walk(p); continue; }
    if (!name.endsWith(".html")) continue;
    for (const m of readFileSync(p, "utf8").matchAll(/.{0,40}(?:[0-9%]<!-- -->[a-zA-Z]|[a-z]<!-- -->[0-9$])/g)) bad.push(`${p}: ${m[0]}`);
  }
}
walk("out");
if (bad.length) {
  console.error("Missing spaces around inserted values:\n" + bad.join("\n"));
  process.exit(1);
}
console.log("check-spacing: ok");
