// Renders seamless idle / talking loops of a project as PNG frames (for GIF overlays such as
// Discord reactive images). Every parameter is a periodic function of time, and the hair
// physics is warmed up for a few cycles first, so the last frame flows into the first.
// node _my_scripts/render_loops.mjs projects/<name> [idle|talk ...]
// Frames go to projects/<name>/work/gif/<clip>/frame_0000.png
import { readFile, writeFile, mkdir, rm, realpath } from 'node:fs/promises';
import { resolve, relative, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { chromium } from '@playwright/test';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

// seconds, frames per second, warm-up cycles before recording
export const CLIPS = {
  idle: { seconds: 8, fps: 15, warmup: 3 },
  talk: { seconds: 6, fps: 15, warmup: 3 },
};

async function main() {
  const [projectArg, ...names] = process.argv.slice(2);
  if (!projectArg) throw new Error('Usage: node _my_scripts/render_loops.mjs projects/<name> [idle|talk ...]');
  const project = await realpath(resolve(projectArg));
  if (relative(root, project).startsWith('..')) throw new Error('project must stay inside the repository');
  const clips = names.length ? names : Object.keys(CLIPS);
  const rig = JSON.parse(await readFile(resolve(project, 'rig.json'), 'utf8'));
  const built = resolve(project, 'built');
  const assets = {};
  const asset = async name => {
    assets[name] = `data:${name.endsWith('.png') ? 'image/png' : 'application/json'};base64,${(await readFile(resolve(built, name))).toString('base64')}`;
  };
  await asset('layers.json');
  const layers = JSON.parse(await readFile(resolve(built, 'layers.json'), 'utf8'));
  await Promise.all(['base', 'hairmask', ...Object.keys(layers.layers)].map(n => asset(`${n}.png`)));
  try {
    await asset('sprites/sprites.json');
    const sprites = JSON.parse(await readFile(resolve(built, 'sprites/sprites.json'), 'utf8'));
    await Promise.all(Object.keys(sprites.layers).map(n => asset(`sprites/${n}.png`)));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }

  const server = await createServer({ root, configFile: false, publicDir: false, appType: 'custom', cacheDir: 'node_modules/.vite-pose-review', optimizeDeps: { noDiscovery: true, entries: [] },
    plugins: [{ name: 'loop-page', configureServer(s) {
      s.middlewares.use((req, res, next) => {
        if (req.url !== '/__loops__') return next();
        res.setHeader('Content-Type', 'text/html');
        res.end('<!doctype html><html><body style="margin:0"><canvas id="avatar"></canvas></body></html>');
      });
    } }],
    server: { host: '127.0.0.1', port: 0, strictPort: false, hmr: false, watch: null, preTransformRequests: false }, logLevel: 'error' });
  let browser;
  try {
    await server.listen();
    const origin = `http://127.0.0.1:${server.httpServer.address().port}`;
    browser = await chromium.launch();
    const width = Math.ceil(rig.image.width * 1.2), height = Math.ceil(rig.image.height * 1.1);
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    let outDir = '';
    await page.exposeFunction('saveFrame', async (i, url) => {
      await writeFile(resolve(outDir, `frame_${String(i).padStart(4, '0')}.png`), Buffer.from(url.split(',')[1], 'base64'));
    });
    await page.goto(`${origin}/__loops__`);
    for (const name of clips) {
      const clip = CLIPS[name];
      if (!clip) throw new Error(`unknown clip ${name}`);
      outDir = resolve(project, 'work', 'gif', name);
      await rm(outDir, { recursive: true, force: true });
      await mkdir(outDir, { recursive: true });
      const count = await page.evaluate(renderClip, { rig, assets, name, clip, width, height });
      await writeFile(resolve(outDir, 'clip.json'), JSON.stringify(clip) + '\n');
      if (errors.length) throw new Error(errors.join('\n'));
      console.log(`${name}: ${count} frames -> ${relative(root, outDir)}`);
    }
  } finally {
    await browser?.close();
    await server.close();
  }
}

// Runs in the page.
async function renderClip({ rig, assets, name, clip, width, height }) {
  const { createMeshAvatar, PARAMS } = await import('/packages/runtime/src/index.ts');
  const canvas = document.getElementById('avatar');
  canvas.style.width = `${width}px`; canvas.style.height = `${height}px`;
  const defaults = Object.fromEntries(PARAMS.map(p => [p.id, p.def]));
  const av = await createMeshAvatar(canvas, { rig, assets, manual: true, padTop: 0.1, padSide: 0.1 });
  av.setAutoIdle(false); av.setAutoMotion(false);

  const T = clip.seconds, w = 2 * Math.PI / T;
  const S = k => t => Math.sin(k * w * t);
  const [s1, s2, s3] = [S(1), S(2), S(3)];

  // Eye openness for blinks starting at the given times (wraps around the loop). The eyes are
  // drawn sprites, so the blink steps half / closed / closed / half, one frame each, switching
  // half a frame before the captured frame.
  const frame = 1 / clip.fps;
  const blink = (t, starts) => {
    let open = 1;
    for (const b of starts) {
      const d = ((t - (b - frame / 2)) % T + T) % T;
      if (d < frame) open = Math.min(open, 0.5);
      else if (d < 3 * frame) open = 0;
      else if (d < 4 * frame) open = Math.min(open, 0.5);
    }
    return open;
  };

  // Talking: phrases of a few unhurried syllables (about 3 per second) with random lengths and
  // pauses. Only the a (half or full open) and o mouths: the wide i read as a grimace.
  const syllables = [], pauses = [];
  if (name === 'talk') {
    let seed = 11;
    const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
    let t = 0.2;
    while (t < T - 0.9) {
      const count = 2 + Math.floor(rnd() * 4);
      for (let k = 0; k < count && t < T - 0.6; k++) {
        const dur = 0.22 + rnd() * 0.18;
        const round = rnd() < 0.35;
        syllables.push({ t0: t, t1: t + dur, form: round ? 0.55 : 0, peak: round ? 0.75 : 0.45 + rnd() * 0.5 });
        t += dur + rnd() * 0.12;
      }
      const pause = 0.35 + rnd() * 0.45;
      pauses.push(t + pause / 2);
      t += pause;
    }
  }
  const mouth = t => {
    for (const s of syllables) {
      if (t >= s.t0 && t < s.t1) {
        const u = (t - s.t0) / (s.t1 - s.t0);
        return { open: s.peak * Math.sin(Math.PI * u) ** 0.8, form: s.form };
      }
    }
    return { open: 0, form: 0 };
  };
  // blink in the middle of a pause in the second half of the loop
  const talkBlink = pauses.find(p => p > T / 2 && p < T - 0.4) ?? T * 0.6;

  // All channels are zero at t = 0, so both loops start from the same rest pose.
  const pose = t => {
    if (name === 'idle') {
      const eye = blink(t, [2.2, 6.0]);
      return {
        angleX: 6 * s1(t) + 1.5 * s2(t), angleY: 2 * s1(t) - 1.2 * s2(t), angleZ: -3 * s1(t) + 0.8 * s3(t),
        bodyAngleX: 2.5 * s1(t), bodyAngleZ: 1.5 * s1(t) - 0.5 * s2(t),
        breath: 0.5 - 0.5 * Math.cos(2 * w * t),
        eyeLOpen: eye, eyeROpen: eye, gazeX: 0.3 * s1(t), gazeY: 0.15 * s2(t),
      };
    }
    const eye = blink(t, [talkBlink]);
    const m = mouth(t);
    // the head lifts a little with each open mouth
    return {
      angleX: 4 * s1(t) + s3(t), angleY: 1.5 * s2(t) + 0.8 * s3(t) + 1.2 * m.open, angleZ: -2 * s1(t) + 0.8 * s2(t),
      bodyAngleX: 2 * s1(t), bodyAngleZ: 1.5 * s1(t),
      breath: 0.5 - 0.5 * Math.cos(w * t),
      eyeLOpen: eye, eyeROpen: eye, gazeX: 0.2 * s1(t), gazeY: 0.1 * s2(t),
      mouthOpen: m.open, mouthForm: m.form,
    };
  };

  // simulate at 120 Hz, record every `step` ticks
  const sim = 120, step = sim / clip.fps, total = clip.seconds * clip.fps;
  let tick = 0;
  const advance = () => {
    for (let k = 0; k < step; k++) {
      av.setParameters({ ...defaults, ...pose(((tick + 1) / sim) % T) });
      av.advance(1 / sim, sim);
      tick++;
    }
  };
  for (let f = 0; f < clip.warmup * total; f++) advance();
  for (let f = 0; f < total; f++) {
    // the eye sprites cross-fade over 0.06 s, longer than a frame; a redraw without elapsed
    // time shows the drawing it is fading to, so no frame holds a double image
    av.advance(0);
    await window.saveFrame(f, canvas.toDataURL());
    advance();
  }
  av.destroy();
  return total;
}

main().catch(error => { console.error(`render_loops: ${error.message}`); process.exitCode = 1; });
