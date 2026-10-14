(async () => {
  const fs = require('node:fs');
  const os = require('node:os');
  const path = require('node:path');
  const {spawn, spawnSync} = require('node:child_process');
  const {pathToFileURL} = require('node:url');
  const manifest = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'context-carousel-chrome-'));
  const framesRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'context-carousel-frames-'));
  const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--remote-debugging-port=0',
      '--no-first-run', '--no-default-browser-check', '--disable-features=BackForwardCache',
      '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
      '--disable-backgrounding-occluded-windows', `--user-data-dir=${profile}`, 'about:blank'],
    {stdio: 'ignore'});
  let ws;
  let id = 0;
  const pending = new Map();
  const audit = [];
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  async function call(method, params = {}) {
    const key = ++id;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(key);
        reject(new Error(`CDP timeout: ${method}`));
      }, 60000);
      pending.set(key, {resolve, reject, timer});
      ws.send(JSON.stringify({id: key, method, params}));
    });
  }
  async function evaluate(expression) {
    const result = await call('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  async function shot(file, scale = 1) {
    const result = await call('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: false, optimizeForSpeed: true,
      clip: {x: 0, y: 0, width: 1080, height: 1350, scale}
    });
    fs.writeFileSync(file, Buffer.from(result.data, 'base64'));
  }
  const boundsCheck = `(() => {
    const errors = [];
    const footer = document.querySelector('.footer').getBoundingClientRect();
    for (const el of document.querySelectorAll('h1,.sub,.notes,.analogy,.resources,.recap,.footer,.kicker,.source,.code,.diagram')) {
      const r = el.getBoundingClientRect();
      if (r.left < 71 || r.right > 1009 || r.bottom > 1281) errors.push(el.className + ' outside safe area: bottom=' + r.bottom);
      if (!el.classList.contains('footer') && r.bottom > footer.top - 20) errors.push(el.className + ' hits footer');
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        if (!walker.currentNode.textContent.trim()) continue;
        const range = document.createRange();
        range.selectNodeContents(walker.currentNode);
        for (const rect of range.getClientRects()) {
          if (rect.left < 71 || rect.right > 1009) errors.push(walker.currentNode.textContent + ' text overflow');
        }
      }
    }
    for (const el of document.querySelectorAll('svg text')) {
      const r = el.getBoundingClientRect();
      const scene = el.closest('svg').getBoundingClientRect();
      if (r.left < 72 || r.right > 1008 || r.top < scene.top || r.bottom > scene.bottom) errors.push(el.textContent + ' outside scene');
      for (const span of el.querySelectorAll('tspan')) {
        if (parseFloat(getComputedStyle(span).fontSize) < 24) errors.push('small SVG label');
      }
    }
    for (const node of document.querySelectorAll('[data-node]')) {
      const x = Number(node.dataset.x), y = Number(node.dataset.y);
      const w = Number(node.dataset.w), h = Number(node.dataset.h);
      for (const label of node.querySelectorAll('text')) {
        const r = label.getBBox();
        if (r.x < x + 8 || r.x + r.width > x + w - 8 || r.y < y + 8 || r.y + r.height > y + h - 8) {
          errors.push(node.dataset.node + ': label outside node: ' + label.textContent);
        }
      }
    }
    for (const cell of document.querySelectorAll('[data-cell-end]')) {
      const r = cell.getBBox();
      if (r.x + r.width > Number(cell.dataset.cellEnd)) errors.push('row column overlap: ' + cell.textContent);
    }
    return errors;
  })()`;
  try {
    let port;
    for (let attempt = 0; attempt < 100; attempt++) {
      if (chrome.exitCode !== null) throw new Error('Chrome exited before ready');
      const file = path.join(profile, 'DevToolsActivePort');
      if (fs.existsSync(file)) {
        port = fs.readFileSync(file, 'utf8').split('\n')[0];
        break;
      }
      await sleep(100);
    }
    if (!port) throw new Error('Chrome did not become responsive');
    const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const tab = tabs.find(tab => tab.type === 'page');
    if (!tab) throw new Error('No responsive browser page');
    ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      ws.addEventListener('open', resolve, {once: true});
      ws.addEventListener('error', reject, {once: true});
    });
    ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      const request = pending.get(message.id);
      if (!request) return;
      clearTimeout(request.timer);
      pending.delete(message.id);
      message.error ? request.reject(new Error(JSON.stringify(message.error))) : request.resolve(message.result);
    });
    await call('Page.enable');
    await call('Runtime.enable');
    for (const slide of manifest.slides) {
      if (slide.number < Number(process.env.START_SLIDE || 1)) continue;
      if (process.env.ONLY_SLIDES && !process.env.ONLY_SLIDES.split(',').map(Number).includes(slide.number)) continue;
      await call('Emulation.setDeviceMetricsOverride', {
        width: 1080, height: 1350, deviceScaleFactor: 1, mobile: false
      });
      await call('Page.navigate', {url: pathToFileURL(slide.file).href});
      for (let tries = 0; tries < 100; tries++) {
        const ready = await evaluate(`location.href===${JSON.stringify(pathToFileURL(slide.file).href)} && document.readyState==='complete' && typeof window.renderFrame==='function'`);
        if (ready) break;
        if (tries === 99) throw new Error('Page readiness timed out');
        await sleep(30);
      }
      await evaluate('document.fonts.ready.then(()=>true)');
      await evaluate('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
      const errors = await evaluate(boundsCheck);
      if (process.env.AUDIT_ONLY) {
        console.log(`Slide ${slide.number}: ${errors.length ? errors.join('; ') : 'PASS'}`);
        continue;
      }
      if (errors.length) throw new Error(`Slide ${slide.number}: ${errors.join('; ')}`);
      await shot(path.join(manifest.out, `${slide.number}.png`), 2);
      audit.push({slide: slide.number, posterBounds: 'pass'});
      console.log(`PNG ${slide.number}/${manifest.slides.length}`);
      if (!slide.animated) continue;
      const dir = path.join(framesRoot, String(slide.number));
      fs.mkdirSync(dir);
      for (let frame = 0; frame < 60; frame++) {
        await evaluate(`window.renderFrame(${frame / 10}); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))`);
        const errors = await evaluate(boundsCheck);
        if (errors.length) throw new Error(`Slide ${slide.number} frame ${frame}: ${errors.join('; ')}`);
        await shot(path.join(dir, `${String(frame).padStart(4, '0')}.png`));
      }
      const result = spawnSync('ffmpeg', [
        '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '10',
        '-i', path.join(dir, '%04d.png'), '-filter_complex',
        '[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a',
        '-loop', '0', path.join(manifest.out, `${slide.number}.gif`)
      ], {encoding: 'utf8', timeout: 120000});
      if (result.status !== 0) throw new Error(result.stderr || String(result.error));
      audit[audit.length - 1].animationBounds = '60 frames pass';
      console.log(`GIF ${slide.number}: six seconds at 10 fps`);
    }
    if (!process.env.AUDIT_ONLY) {
      const auditFile = path.join(manifest.out, 'render-audit.json');
      const previous = fs.existsSync(auditFile) ? JSON.parse(fs.readFileSync(auditFile, 'utf8')).slides : [];
      const combined = new Map(previous.map(item => [item.slide, item]));
      for (const item of audit) combined.set(item.slide, item);
      fs.writeFileSync(auditFile, JSON.stringify({
        slides: [...combined.values()].sort((a, b) => a.slide - b.slide),
        temporaryFrames: framesRoot, pngSize: [2160, 2700], gifSize: [1080, 1350],
        durationMs: 6000, fps: 10
      }, null, 2) + '\n');
    }
    console.log(`Frames retained for review: ${framesRoot}`);
  } finally {
    if (ws && ws.readyState === WebSocket.OPEN) {
      try { await call('Browser.close'); } catch (error) { console.error(error.message); }
      ws.close();
    }
    if (chrome.exitCode === null) chrome.kill('SIGTERM');
    await sleep(500);
    fs.rmSync(profile, {recursive: true, force: true});
    if (fs.readdirSync(framesRoot).length === 0) fs.rmdirSync(framesRoot);
  }
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
