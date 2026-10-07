import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { join, resolve } from "node:path";

const projectRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const outDir = join(projectRoot, "out");
const uploadDir = join(projectRoot, "cloudflare-upload");
const nextAssets = join(outDir, "_next");
const prefixedAssetsRoot = join(outDir, "assets");
const prefixedAssets = join(prefixedAssetsRoot, "_next");

if (!existsSync(outDir)) {
  throw new Error("The out directory does not exist. Run next build first.");
}

if (existsSync(nextAssets)) {
  mkdirSync(prefixedAssetsRoot, { recursive: true });
  rmSync(prefixedAssets, { recursive: true, force: true });
  cpSync(nextAssets, prefixedAssets, { recursive: true });
}

rmSync(uploadDir, { recursive: true, force: true });
mkdirSync(uploadDir, { recursive: true });
cpSync(outDir, uploadDir, { recursive: true });

console.log(`Cloudflare upload folder prepared: ${uploadDir}`);
