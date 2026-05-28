import { build } from 'esbuild';
import { cp, mkdir, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, relative } from 'node:path';

const root = process.cwd();
const distDir = join(root, 'dist');
const assetsDir = join(distDir, 'assets');

await rm(distDir, { recursive: true, force: true });
await mkdir(assetsDir, { recursive: true });

const publicDir = join(root, 'public');
if (existsSync(publicDir)) {
  await cp(publicDir, distDir, { recursive: true });
}

const result = await build({
  entryPoints: [join(root, 'src', 'main.jsx')],
  bundle: true,
  format: 'esm',
  platform: 'browser',
  target: ['chrome111', 'edge111', 'firefox114', 'safari16'],
  outdir: assetsDir,
  entryNames: 'index-[hash]',
  chunkNames: 'chunks/[name]-[hash]',
  assetNames: '[name]-[hash]',
  metafile: true,
  minify: true,
  splitting: true,
  sourcemap: false,
  define: {
    'process.env.NODE_ENV': '"production"',
    'import.meta.env': JSON.stringify({
      BASE_URL: '/',
      MODE: 'production',
      DEV: false,
      PROD: true,
      VITE_HEDGEMATE_API_URL: process.env.VITE_HEDGEMATE_API_URL || '',
    }),
  },
  loader: {
    '.png': 'file',
    '.jpg': 'file',
    '.jpeg': 'file',
    '.gif': 'file',
    '.svg': 'file',
    '.webp': 'file',
  },
});

const outputs = Object.keys(result.metafile.outputs);
const jsFile = outputs.find((file) => file.endsWith('.js'));
const cssFiles = outputs.filter((file) => file.endsWith('.css'));

if (!jsFile) {
  throw new Error('Build completed without a JavaScript output.');
}

const toPublicPath = (file) => `/${relative(distDir, join(root, file)).replace(/\\/g, '/')}`;

const html = `<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HedgeMate</title>
    ${cssFiles.map((file) => `<link rel="stylesheet" href="${toPublicPath(file)}" />`).join('\n    ')}
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="${toPublicPath(jsFile)}"></script>
  </body>
</html>
`;

await writeFile(join(distDir, 'index.html'), html, 'utf8');

console.log(`built ${relative(root, distDir)} with ${outputs.length} outputs`);
