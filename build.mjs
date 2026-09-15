import { stripTypeScriptTypes } from 'node:module';
import { readdir, readFile, writeFile, mkdir } from 'node:fs/promises';
await mkdir(new URL('./web/assets/', import.meta.url), { recursive: true });
for (const name of await readdir(new URL('./frontend/', import.meta.url))) {
  if (!name.endsWith('.ts')) continue;
  const source = await readFile(new URL('./frontend/' + name, import.meta.url), 'utf8');
  const js = stripTypeScriptTypes(source, { mode: 'strip' });
  await writeFile(new URL('./web/assets/' + name.replace(/\.ts$/, '.js'), import.meta.url), js);
}
console.log('Built frontend TypeScript. Python can now serve the bundled JavaScript.');
