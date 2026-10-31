import { build } from "esbuild";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const outfile = path.join(
  __dirname,
  "..",
  "custom_components",
  "marketsentry",
  "www",
  "marketsentry-card.js"
);

await build({
  entryPoints: [path.join(__dirname, "src", "index.js")],
  bundle: true,
  format: "esm",
  minify: true,
  outfile,
  target: ["es2022"],
});

console.log(`Built ${outfile}`);
