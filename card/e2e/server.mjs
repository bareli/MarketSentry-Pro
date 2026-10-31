// Minimal static file server for Playwright's screenshot harness. Serves
// the whole repo root so the harness's relative import of the built card
// (../../custom_components/marketsentry/www/marketsentry-card.js) resolves
// over HTTP (ES module imports are blocked over file:// by CORS).

import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, "..", "..");
const port = Number(process.env.PORT) || 4173;

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
};

const server = createServer(async (req, res) => {
  try {
    const urlPath = decodeURIComponent(new URL(req.url, "http://localhost").pathname);
    const filePath = path.join(repoRoot, urlPath);
    if (!filePath.startsWith(repoRoot)) {
      res.writeHead(403).end("Forbidden");
      return;
    }
    const contents = await readFile(filePath);
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": MIME_TYPES[ext] || "application/octet-stream" });
    res.end(contents);
  } catch {
    res.writeHead(404).end("Not found");
  }
});

server.listen(port, () => {
  console.log(`e2e static server listening on http://localhost:${port}`);
});
