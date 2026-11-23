/* Next 16's static export writes route prefetch data to `<route>/__next.<segment>/__PAGE__.txt`, but the client
   asks for `<route>/__next.<segment>.__PAGE__.txt`, so client-side navigation gets 404s and falls back to full
   page loads. Copy each file to the name the client requests. */
import { copyFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

let copied = 0;
function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (!statSync(p).isDirectory()) continue;
    if (name.startsWith("__next.")) {
      const page = join(p, "__PAGE__.txt");
      try {
        statSync(page);
        copyFileSync(page, join(dir, `${name}.__PAGE__.txt`));
        copied++;
      } catch {}
    }
    if (name !== "data") walk(p);
  }
}
walk("out");
console.log(`fix-prefetch: copied ${copied} file(s)`);
