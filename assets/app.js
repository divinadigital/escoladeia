/* Escola de IA — núcleo compartilhado por todas as páginas (vanilla, sem dependências). */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = matchMedia('(hover: hover) and (pointer: fine)').matches;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const moeda = v => (+v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
  const brl = v => v > 0 ? moeda(v) : 'Grátis';
  const qs = k => new URLSearchParams(location.search).get(k);

  /* ---------- API ---------- */
  async function api(rota, dados, metodo) {
    const m = metodo || (dados ? 'POST' : 'GET');
    let url = '/api/' + rota;
    const opt = { method: m, headers: {}, credentials: 'same-origin' };
    if (m === 'GET' && dados) url += '?' + new URLSearchParams(dados);
    else if (dados) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(dados); }
    let r;
    try { r = await fetch(url, opt); } catch (e) { throw Object.assign(new Error('Sem conexão com o servidor. Abra o site pelo server.py.'), { status: 0 }); }
    let j = {};
    try { j = await r.json(); } catch (e) { throw Object.assign(new Error('O servidor não respondeu como esperado. Rode "python server.py".'), { status: r.status }); }
    if (!r.ok) throw Object.assign(new Error(j.erro || 'Algo deu errado.'), { status: r.status });
    return j;
  }

  /* ---------- sessão ---------- */
  let euPromise;
  const eu = () => (euPromise ||= api('eu').then(j => j.usuario).catch(() => null));
  const PAINEL = { aluno: 'aluno.html', professor: 'professor.html', parceiro: 'parceiro.html', admin: 'admin.html' };
  const PAPEL_NOME = { aluno: 'Aluno', professor: 'Professor', parceiro: 'Parceiro', admin: 'Coordenação' };
  async function exigir(...papeis) {
    const u = await eu();
    if (!u) { location.replace('entrar.html?perfil=' + (papeis[0] || 'aluno') + '&volta=' + encodeURIComponent(location.pathname + location.search)); return new Promise(() => {}); }
    if (papeis.length && !papeis.includes(u.papel)) { location.replace(PAINEL[u.papel]); return new Promise(() => {}); }
    return u;
  }
  async function sair() { await api('sair', {}); location.href = 'index.html'; }

  /* ---------- afiliado: guarda ?ref= por 30 dias ---------- */
  const ref = qs('ref');
  if (ref) {
    try { localStorage.setItem('eia-ref', JSON.stringify({ ref, ate: Date.now() + 30 * 864e5 })); } catch (e) {}
    api('clique', { ref, curso_id: null }).catch(() => {});
  }
  const refAtual = () => { try { const o = JSON.parse(localStorage.getItem('eia-ref')); return o && o.ate > Date.now() ? o.ref : ''; } catch (e) { return ''; } };

  /* ---------- avatar ---------- */
  const CORES = ['#d4ff3a', '#ff8a6b', '#7cc4ff', '#ff8fc2', '#b5a3ff', '#ffc55a'];
  const hash = s => { let h = 2166136261; for (const ch of String(s)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  const iniciais = n => String(n || '?').trim().split(/\s+/).map(p => p[0]).slice(0, 2).join('').toUpperCase();
  const avatar = (nome, size = 30) => `<span class="av" style="width:${size}px;height:${size}px;background:${CORES[hash(nome) % CORES.length]}">${esc(iniciais(nome))}</span>`;

  /* ---------- capa generativa do curso (SVG determinístico pelo slug) ---------- */
  const PALETAS = {
    lima: ['#0e1208', '#d4ff3a', '#8fd400'], coral: ['#170c09', '#ff6a4d', '#ffb199'], ceu: ['#07101a', '#3aa6ff', '#9ad3ff'],
    rosa: ['#170912', '#ff5fa8', '#ffb3d6'], violeta: ['#0e0b1a', '#8b6cff', '#c9bcff'], ambar: ['#151005', '#ffb020', '#ffe08a'],
  };
  function rng(seed) { let s = seed || 1; return () => (s = Math.imul(s ^ (s >>> 15), 2246822507) + 0x9e3779b9 | 0, ((s >>> 0) % 10000) / 10000); }
  function capa(slug, cor, titulo) {
    const [bg, a, b] = PALETAS[cor] || PALETAS.lima;
    const r = rng(hash(slug));
    const tipo = hash(slug) % 4;
    const id = 'g' + (hash(slug) % 99999);
    let shapes = '';
    if (tipo === 0) { // rede neural
      const nodes = Array.from({ length: 16 }, () => [30 + r() * 340, 20 + r() * 210]);
      nodes.forEach((p, i) => nodes.slice(i + 1).forEach(q => { const d = Math.hypot(p[0] - q[0], p[1] - q[1]); if (d < 110) shapes += `<line x1="${p[0]}" y1="${p[1]}" x2="${q[0]}" y2="${q[1]}" stroke="${a}" stroke-opacity="${(1 - d / 110) * .7}" stroke-width="1"/>`; }));
      nodes.forEach((p, i) => shapes += `<circle cx="${p[0]}" cy="${p[1]}" r="${i % 4 ? 2.5 : 5}" fill="${i % 4 ? b : a}"/>`);
    } else if (tipo === 1) { // ondas
      for (let k = 0; k < 14; k++) {
        const y = 30 + k * 15, amp = 8 + r() * 26, f = .015 + r() * .02, ph = r() * 6;
        let d = `M0 ${y}`; for (let x = 0; x <= 400; x += 10) d += ` L${x} ${(y + Math.sin(x * f + ph) * amp).toFixed(1)}`;
        shapes += `<path d="${d}" fill="none" stroke="${k % 3 ? b : a}" stroke-opacity="${.25 + k / 20}" stroke-width="${k % 3 ? 1 : 2}"/>`;
      }
    } else if (tipo === 2) { // grade de pontos com foco
      const cx = 120 + r() * 160, cy = 60 + r() * 130;
      for (let x = 14; x < 400; x += 18) for (let y = 14; y < 250; y += 18) {
        const d = Math.hypot(x - cx, y - cy), s = Math.max(.6, 5 - d / 34);
        shapes += `<circle cx="${x}" cy="${y}" r="${s.toFixed(2)}" fill="${d < 60 ? a : b}" fill-opacity="${Math.max(.15, 1 - d / 220).toFixed(2)}"/>`;
      }
    } else { // órbitas
      const cx = 200 + (r() - .5) * 120, cy = 125;
      for (let k = 1; k < 9; k++) shapes += `<ellipse cx="${cx}" cy="${cy}" rx="${k * 26}" ry="${k * 12}" fill="none" stroke="${k % 2 ? a : b}" stroke-opacity="${.9 - k * .08}" transform="rotate(${-18 + r() * 8} ${cx} ${cy})"/>`;
      for (let k = 0; k < 7; k++) { const t = r() * 6.28, rr = 30 + r() * 180; shapes += `<circle cx="${cx + Math.cos(t) * rr}" cy="${cy + Math.sin(t) * rr * .46}" r="${2 + r() * 4}" fill="${a}"/>`; }
      shapes += `<circle cx="${cx}" cy="${cy}" r="16" fill="${a}"/>`;
    }
    const mono = esc(String(titulo || '').split(/\s+/).slice(0, 1)[0] || '').toUpperCase();
    return `<svg viewBox="0 0 400 250" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><defs><radialGradient id="${id}" cx="75%" cy="20%" r="80%"><stop offset="0" stop-color="${a}" stop-opacity=".35"/><stop offset="1" stop-color="${bg}" stop-opacity="0"/></radialGradient></defs><rect width="400" height="250" fill="${bg}"/><rect width="400" height="250" fill="url(#${id})"/>${shapes}<text x="20" y="232" font-family="Geist Mono, monospace" font-size="11" letter-spacing="2" fill="${b}" fill-opacity=".7">${mono} · ESCOLA DE IA</text></svg>`;
  }

  /* ---------- card de curso ---------- */
  const horas = m => m >= 60 ? `${Math.floor(m / 60)}h${m % 60 ? String(m % 60).padStart(2, '0') : ''}` : `${m} min`;
  function cardCurso(c, i = 0, extra = '') {
    if (typeof extra !== 'string') extra = ''; // quando usado direto em .map()
    return `<article class="ccard spot fade-in" style="--i:${i}">
      <div class="ccard__cover">${capa(c.slug, c.cor, c.titulo)}<div class="ccard__tags"><span class="tag">${esc(c.categoria)}</span><span class="tag">${esc(c.nivel)}</span></div></div>
      <div class="ccard__body">
        <div class="ccard__by">${avatar(c.autor.nome, 22)} ${esc(c.autor.nome)} · <span>${esc(c.autor.selo)}</span></div>
        <h3><a class="ccard__link" href="curso.html?c=${encodeURIComponent(c.slug)}">${esc(c.titulo)}</a></h3>
        <p>${esc(c.resumo)}</p>
        ${extra}
        <div class="ccard__foot"><span>${c.aulas} aulas · ${horas(c.minutos)}</span><span class="ccard__price">${brl(c.preco)}</span></div>
      </div></article>`;
  }
  const skeletonCards = n => Array.from({ length: n }, () => `<div class="ccard ccard--sk"><div class="ccard__cover sk" style="border-radius:0"></div><div class="ccard__body"><div class="sk" style="height:14px;width:50%"></div><div class="sk" style="height:22px;width:85%"></div><div class="sk" style="height:14px;width:95%"></div><div class="sk" style="height:14px;width:70%"></div></div></div>`).join('');

  /* ---------- markdown simples e seguro (para o conteúdo das aulas) ---------- */
  function md(src) {
    const linhas = String(src || '').replace(/\r/g, '').split('\n');
    let out = '', lista = null, i = 0;
    const inline = t => esc(t).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="text-decoration:underline">$1</a>');
    const fechaLista = () => { if (lista) { out += `</${lista}>`; lista = null; } };
    while (i < linhas.length) {
      const l = linhas[i];
      if (l.startsWith('```')) {
        fechaLista(); const buf = []; i++;
        while (i < linhas.length && !linhas[i].startsWith('```')) buf.push(linhas[i++]);
        out += `<pre><button class="copy" type="button">Copiar</button><code>${esc(buf.join('\n'))}</code></pre>`; i++; continue;
      }
      let m;
      if ((m = l.match(/^(#{2,3})\s+(.*)/))) { fechaLista(); out += `<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`; }
      else if ((m = l.match(/^>\s?(.*)/))) { fechaLista(); out += `<blockquote><p>${inline(m[1])}</p></blockquote>`; }
      else if ((m = l.match(/^\s*[-*]\s+(.*)/))) { if (lista !== 'ul') { fechaLista(); out += '<ul>'; lista = 'ul'; } out += `<li>${inline(m[1])}</li>`; }
      else if ((m = l.match(/^\s*\d+[.)]\s+(.*)/))) { if (lista !== 'ol') { fechaLista(); out += '<ol>'; lista = 'ol'; } out += `<li>${inline(m[1])}</li>`; }
      else if (!l.trim()) fechaLista();
      else { fechaLista(); out += `<p>${inline(l)}</p>`; }
      i++;
    }
    fechaLista();
    return out;
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('pre .copy'); if (!b) return;
    navigator.clipboard?.writeText(b.nextElementSibling.textContent).then(() => { b.textContent = 'Copiado'; setTimeout(() => b.textContent = 'Copiar', 1400); });
  });

  /* ---------- toast ---------- */
  function toast(msg, tipo) {
    let box = $('.toasts'); if (!box) { box = document.createElement('div'); box.className = 'toasts'; box.setAttribute('role', 'status'); document.body.appendChild(box); }
    const t = document.createElement('div'); t.className = 'toast' + (tipo === 'erro' ? ' toast--bad' : '');
    t.innerHTML = `<span>${esc(msg)}</span>`; box.appendChild(t);
    setTimeout(() => { t.classList.add('out'); setTimeout(() => t.remove(), 320); }, 3200);
  }

  /* ---------- confete (transitions.dev: confetti burst) ---------- */
  function confete(x = innerWidth / 2, y = innerHeight / 2, n = 120) {
    if (reduce) return;
    const cv = document.createElement('canvas'); cv.className = 'fx-layer'; document.body.appendChild(cv);
    const dpr = Math.min(2, devicePixelRatio || 1); cv.width = innerWidth * dpr; cv.height = innerHeight * dpr;
    const g = cv.getContext('2d'); g.scale(dpr, dpr);
    const cores = ['#d4ff3a', '#ff6a4d', '#3aa6ff', '#ff5fa8', '#8b6cff', '#ffb020'];
    const ps = Array.from({ length: n }, () => { const a = Math.random() * Math.PI * 2, v = 4 + Math.random() * 9; return { x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 6, r: Math.random() * 6.28, vr: (Math.random() - .5) * .4, w: 6 + Math.random() * 6, h: 3 + Math.random() * 5, c: cores[n % 6 + Math.floor(Math.random() * 6)] || cores[0], life: 0 }; });
    const t0 = performance.now();
    (function tick(t) {
      g.clearRect(0, 0, innerWidth, innerHeight);
      ps.forEach(p => { p.vy += .32; p.vx *= .985; p.x += p.vx; p.y += p.vy; p.r += p.vr; g.save(); g.translate(p.x, p.y); g.rotate(p.r); g.fillStyle = p.c; g.globalAlpha = Math.max(0, 1 - (t - t0) / 2600); g.fillRect(-p.w / 2, -p.h / 2, p.w, p.h); g.restore(); });
      if (t - t0 < 2600) requestAnimationFrame(tick); else cv.remove();
    })(t0);
  }

  /* ---------- click spark (reactbits: ClickSpark) ---------- */
  if (!reduce) document.addEventListener('pointerdown', e => {
    if (!e.target.closest('.btn--primary, [data-spark]')) return;
    const n = 8, R = 26, wrap = document.createElement('div'); wrap.className = 'fx-layer';
    for (let k = 0; k < n; k++) {
      const s = document.createElement('i'), a = k / n * Math.PI * 2;
      s.style.cssText = `position:absolute;left:${e.clientX}px;top:${e.clientY}px;width:2px;height:9px;border-radius:2px;background:var(--lime);transform-origin:50% 0;transform:rotate(${a + Math.PI / 2}rad)`;
      s.animate([{ transform: `rotate(${a + Math.PI / 2}rad) translateY(4px) scaleY(1)`, opacity: 1 }, { transform: `rotate(${a + Math.PI / 2}rad) translateY(${R}px) scaleY(.2)`, opacity: 0 }], { duration: 480, easing: 'cubic-bezier(.22,1,.36,1)' });
      wrap.appendChild(s);
    }
    document.body.appendChild(wrap); setTimeout(() => wrap.remove(), 520);
  });

  /* ---------- cabeçalho e rodapé ---------- */
  const LOGO = `<svg class="logo__mark" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="9" fill="currentColor"/><g fill="none" stroke="var(--bg)" stroke-width="2.2" stroke-linecap="round"><path d="M9 21.5 16 9l7 12.5"/><path d="M11.6 17h8.8"/></g><circle cx="24.5" cy="8" r="2.6" fill="var(--lime)"/></svg>`;
  const I = {
    sun: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>',
    moon: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>',
    menu: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h10"/></svg>',
  };
  function header() {
    const el = $('#topo'); if (!el) return;
    const pag = location.pathname.split('/').pop() || 'index.html';
    const links = [['cursos.html', 'Cursos'], ['index.html#perfis', 'Para quem'], ['index.html#parceiros', 'Seja parceiro'], ['index.html#duvidas', 'Dúvidas']];
    el.innerHTML = `<header class="nav" id="nav"><div class="wrap nav__in">
      <a href="index.html" class="logo" aria-label="Escola de IA, início">${LOGO}<span class="logo__word">Escola de <em>IA</em></span></a>
      <nav aria-label="Principal"><ul class="nav__links">${links.map(([h, t]) => `<li><a href="${h}"${pag === h ? ' aria-current="page"' : ''}>${t}</a></li>`).join('')}<li class="nav__pill" aria-hidden="true"></li></ul></nav>
      <div class="nav__actions">
        <button class="icon-btn theme-toggle" type="button" aria-label="Alternar tema claro ou escuro"><span class="i-sun">${I.sun}</span><span class="i-moon">${I.moon}</span></button>
        <span id="navUser" class="nav__user"><a class="btn btn--ghost btn--sm hide-m" href="entrar.html">Entrar</a><a class="btn btn--primary btn--sm hide-m" href="entrar.html?perfil=aluno&modo=cadastro">Começar grátis</a></span>
        <button class="icon-btn nav__burger" type="button" aria-label="Abrir menu" aria-expanded="false">${I.menu}</button>
      </div></div></header>
      <div class="drawer" id="drawer"><div class="drawer__bg" data-close></div><div class="drawer__panel" role="dialog" aria-label="Menu">
        ${links.map(([h, t]) => `<a href="${h}">${t}</a>`).join('')}<a href="entrar.html">Entrar</a>
        <a class="btn btn--primary" style="margin-top:18px;font-size:15px;border:0" href="entrar.html?perfil=aluno&modo=cadastro">Começar grátis</a></div></div>`;
    // tema
    const syncIcon = () => { const dark = document.documentElement.dataset.theme === 'dark' || (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches); $$('.i-sun').forEach(i => i.hidden = !dark); $$('.i-moon').forEach(i => i.hidden = dark); };
    syncIcon();
    $('.theme-toggle').addEventListener('click', () => {
      const d = document.documentElement;
      const cur = d.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      const apply = () => { d.dataset.theme = cur === 'dark' ? 'light' : 'dark'; try { localStorage.setItem('eia-tema', d.dataset.theme); } catch (e) {} syncIcon(); };
      if (document.startViewTransition && !reduce) document.startViewTransition(apply); else apply();
    });
    // nav com fundo ao rolar
    const nav = $('#nav'); const onS = () => nav.classList.toggle('is-scrolled', scrollY > 8); onS(); addEventListener('scroll', onS, { passive: true });
    // pílula que segue o mouse (transitions.dev: tabs sliding)
    const pill = $('.nav__pill'), ul = $('.nav__links');
    $$('.nav__links a').forEach(a => a.addEventListener('pointerenter', () => { pill.style.opacity = 1; pill.style.width = a.offsetWidth + 'px'; pill.style.transform = `translateX(${a.offsetLeft}px)`; }));
    ul.addEventListener('pointerleave', () => pill.style.opacity = 0);
    // gaveta mobile
    const dr = $('#drawer'), bur = $('.nav__burger');
    bur.addEventListener('click', () => { dr.classList.add('is-open'); bur.setAttribute('aria-expanded', 'true'); });
    dr.addEventListener('click', e => { if (e.target.closest('[data-close], a')) { dr.classList.remove('is-open'); bur.setAttribute('aria-expanded', 'false'); } });
    // usuário logado
    eu().then(u => {
      if (!u) return;
      const box = $('#navUser');
      box.innerHTML = `<div class="menu"><button class="user-chip" type="button" aria-haspopup="true">${avatar(u.nome)}<span class="hide-m">${esc(u.nome.split(' ')[0])}</span><span class="role-tag">${PAPEL_NOME[u.papel]}</span></button>
        <div class="menu__pop" role="menu"><a href="${PAINEL[u.papel]}" role="menuitem">Meu painel</a>${u.papel === 'aluno' ? '<a href="cursos.html" role="menuitem">Explorar cursos</a>' : ''}${u.papel === 'professor' || u.papel === 'parceiro' ? '<a href="editor.html" role="menuitem">Criar curso</a>' : ''}<hr><button type="button" data-sair role="menuitem">Sair</button></div></div>`;
      const menu = $('.menu', box);
      $('.user-chip', box).addEventListener('click', e => { e.stopPropagation(); menu.classList.toggle('is-open'); });
      document.addEventListener('click', () => menu.classList.remove('is-open'));
      $('[data-sair]', box).addEventListener('click', sair);
      const dl = $$('#drawer .drawer__panel a'); dl[dl.length - 2].textContent = 'Meu painel'; dl[dl.length - 2].href = PAINEL[u.papel]; dl[dl.length - 1].remove();
    });
  }
  function footer() {
    const el = $('#rodape'); if (!el) return;
    el.innerHTML = `<footer class="foot"><div class="wrap"><div class="foot__grid">
      <div><a href="index.html" class="logo">${LOGO}<span class="logo__word">Escola de <em>IA</em></span></a><p style="max-width:34ch;margin-top:14px">Aulas práticas de inteligência artificial, com professores da casa e criadores parceiros.</p></div>
      <div><h4>Estudar</h4><ul><li><a href="cursos.html">Todos os cursos</a></li><li><a href="entrar.html?perfil=aluno">Área do aluno</a></li><li><a href="curso.html?c=fundamentos-de-ia-sem-complicacao">Curso grátis</a></li></ul></div>
      <div><h4>Ensinar</h4><ul><li><a href="entrar.html?perfil=professor">Área do professor</a></li><li><a href="entrar.html?perfil=parceiro">Área do parceiro</a></li><li><a href="index.html#parceiros">Programa de afiliados</a></li></ul></div>
      <div><h4>Escola</h4><ul><li><a href="index.html#duvidas">Dúvidas</a></li><li><a href="entrar.html?perfil=admin">Coordenação</a></li></ul></div>
      </div><div class="foot__bottom"><span>© ${new Date().getFullYear()} Escola de IA</span><span class="mono">feito com IA, revisado por pessoas</span></div></div></footer>`;
  }

  /* ---------- efeitos de entrada ---------- */
  function efeitos(root = document) {
    // split text palavra a palavra (reactbits: SplitText)
    $$('[data-split]:not([data-split-ok])', root).forEach(el => {
      el.dataset.splitOk = 1;
      const walk = (node, out) => node.childNodes.forEach(n => {
        if (n.nodeType === 3) n.textContent.split(/(\s+)/).forEach(p => { if (!p) return; if (/^\s+$/.test(p)) { out.appendChild(document.createTextNode(' ')); return; } const w = document.createElement('span'); w.className = 'w'; const s = document.createElement('span'); s.textContent = p; w.appendChild(s); out.appendChild(w); });
        else if (n.nodeType === 1 && n.hasAttribute('data-decrypt')) { const w = document.createElement('span'); w.className = 'w'; const s = document.createElement('span'); s.appendChild(n.cloneNode(true)); w.appendChild(s); out.appendChild(w); }
        else if (n.nodeType === 1) { const c = n.cloneNode(false); walk(n, c); out.appendChild(c); }
      });
      el.setAttribute('aria-label', el.textContent.trim());
      const f = document.createElement('span'); f.setAttribute('aria-hidden', 'true'); walk(el, f); el.textContent = ''; el.appendChild(f);
      $$('.w > span', el).forEach((s, i) => s.style.setProperty('--i', i));
    });
    const io = new IntersectionObserver(es => es.forEach(en => { if (!en.isIntersecting) return; en.target.classList.add('in'); en.target.dispatchEvent(new Event('reveal')); io.unobserve(en.target); }), { rootMargin: '0px 0px -8% 0px', threshold: .1 });
    const novosCont = $$('[data-count]:not([data-cok])', root);
    novosCont.forEach(el => el.dataset.cok = 1);
    // contadores (reactbits: CountUp)
    novosCont.forEach(el => el.addEventListener('reveal', () => {
      const end = +el.dataset.count, pre = el.dataset.pre || '', suf = el.dataset.suf || '';
      if (reduce) { el.textContent = pre + end.toLocaleString('pt-BR') + suf; return; }
      const t0 = performance.now(), dur = 1400;
      (function tick(t) { const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 4); el.textContent = pre + Math.round(end * e).toLocaleString('pt-BR') + suf; if (p < 1) requestAnimationFrame(tick); })(t0);
    }, { once: true }));
    $$('[data-reveal]:not(.in), [data-split]:not(.in)', root).forEach(el => io.observe(el));
    novosCont.forEach(el => io.observe(el));
    // o que já está na primeira tela entra na hora, sem depender do observer
    setTimeout(() => $$('[data-reveal]:not(.in), [data-split]:not(.in), [data-count]', root).forEach(el => {
      if (el.getBoundingClientRect().top < innerHeight && !el.classList.contains('in')) { el.classList.add('in'); el.dispatchEvent(new Event('reveal')); io.unobserve(el); }
    }), 60);
    // texto que se decifra (reactbits: DecryptedText)
    $$('[data-decrypt]', root).forEach(el => {
      const final = el.textContent, chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ01#$%&*<>/';
      const run = () => {
        if (reduce) return; let k = 0;
        const iv = setInterval(() => { el.textContent = final.split('').map((c, i) => i < k || c === ' ' ? c : chars[Math.floor(Math.random() * chars.length)]).join(''); k += .5; if (k > final.length) { clearInterval(iv); el.textContent = final; } }, 38);
      };
      el.setAttribute('aria-label', final); setTimeout(run, +el.dataset.decrypt || 600);
      el.addEventListener('pointerenter', run);
    });
    // spotlight que segue o mouse (reactbits: SpotlightCard)
    if (fine && root === document) root.addEventListener('pointermove', e => { const c = e.target.closest?.('.spot'); if (!c) return; const r = c.getBoundingClientRect(); c.style.setProperty('--mx', e.clientX - r.left + 'px'); c.style.setProperty('--my', e.clientY - r.top + 'px'); });
    // botões magnéticos (reactbits: Magnet)
    if (fine && !reduce) $$('.magnetic:not([data-mag])', root).forEach(b => {
      b.dataset.mag = 1;
      b.addEventListener('pointermove', e => { const r = b.getBoundingClientRect(); b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * .25}px, ${(e.clientY - r.top - r.height / 2) * .35}px)`; });
      b.addEventListener('pointerleave', () => b.style.transform = '');
    });
  }

  /* ---------- abas com pílula ---------- */
  function abas(el, onChange) {
    const pill = document.createElement('span'); pill.className = 'tabs__pill'; pill.setAttribute('aria-hidden', 'true'); el.prepend(pill);
    const bts = $$('button', el);
    const place = b => { pill.style.width = b.offsetWidth + 'px'; pill.style.transform = `translateX(${b.offsetLeft - 4}px)`; pill.style.top = b.offsetTop + 'px'; };
    const sel = (b, silent) => { bts.forEach(x => x.setAttribute('aria-selected', x === b)); place(b); if (!silent) onChange?.(b.dataset.v, b); };
    bts.forEach(b => b.addEventListener('click', () => sel(b)));
    const atual = () => bts.find(b => b.getAttribute('aria-selected') === 'true') || bts[0];
    requestAnimationFrame(() => { pill.style.transition = 'none'; place(atual()); requestAnimationFrame(() => pill.style.transition = ''); });
    document.fonts?.ready.then(() => place(atual()));
    addEventListener('resize', () => place(atual()));
    return { set: v => { const b = bts.find(x => x.dataset.v === v); if (b) sel(b, true); } };
  }

  /* ---------- rede neural interativa (canvas) ---------- */
  function rede(cv, opt = {}) {
    const g = cv.getContext('2d'); let W, H, pts = [], mouse = { x: -999, y: -999 }, raf;
    const dpr = Math.min(2, devicePixelRatio || 1);
    const cor = () => opt.cor || getComputedStyle(document.documentElement).getPropertyValue('--lime').trim() || '#d4ff3a';
    const tinta = () => opt.tinta || getComputedStyle(document.documentElement).getPropertyValue('--text').trim();
    const resize = () => {
      const r = cv.getBoundingClientRect(); W = r.width; H = r.height; cv.width = W * dpr; cv.height = H * dpr; g.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.round(Math.min(110, W * H / (opt.densidade || 11000)));
      pts = Array.from({ length: n }, () => ({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .3, vy: (Math.random() - .5) * .3, p: Math.random() * 6.28 }));
    };
    const host = opt.host || cv.parentElement;
    host.addEventListener('pointermove', e => { const r = cv.getBoundingClientRect(); mouse.x = e.clientX - r.left; mouse.y = e.clientY - r.top; });
    host.addEventListener('pointerleave', () => { mouse.x = mouse.y = -999; });
    const pulses = [];
    const draw = t => {
      g.clearRect(0, 0, W, H);
      const c = cor(), k = tinta(), D = opt.dist || 130;
      for (const p of pts) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > W) p.vx *= -1; if (p.y < 0 || p.y > H) p.vy *= -1;
        const dx = p.x - mouse.x, dy = p.y - mouse.y, dm = Math.hypot(dx, dy);
        if (dm < 160) { p.x += dx / dm * .8; p.y += dy / dm * .8; }
      }
      g.lineWidth = 1;
      for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i], b = pts[j], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < D) {
          const near = Math.hypot((a.x + b.x) / 2 - mouse.x, (a.y + b.y) / 2 - mouse.y) < 170;
          g.strokeStyle = near ? c : k; g.globalAlpha = (1 - d / D) * (near ? .8 : .14); g.beginPath(); g.moveTo(a.x, a.y); g.lineTo(b.x, b.y); g.stroke();
          if (!reduce && Math.random() < .0009) pulses.push({ a, b, t: 0 });
        }
      }
      for (let i = pulses.length - 1; i >= 0; i--) {
        const q = pulses[i]; q.t += .02; if (q.t >= 1) { pulses.splice(i, 1); continue; }
        g.globalAlpha = 1 - q.t; g.fillStyle = c; g.beginPath(); g.arc(q.a.x + (q.b.x - q.a.x) * q.t, q.a.y + (q.b.y - q.a.y) * q.t, 2.2, 0, 6.28); g.fill();
      }
      for (const p of pts) {
        const near = Math.hypot(p.x - mouse.x, p.y - mouse.y) < 170;
        g.globalAlpha = near ? 1 : .45; g.fillStyle = near ? c : k; g.beginPath(); g.arc(p.x, p.y, near ? 2.6 : 1.6 + Math.sin(t / 800 + p.p) * .4, 0, 6.28); g.fill();
      }
      g.globalAlpha = 1;
      raf = requestAnimationFrame(draw);
    };
    resize(); addEventListener('resize', resize);
    if (reduce) { draw(0); cancelAnimationFrame(raf); return; }
    const vis = new IntersectionObserver(([e]) => { cancelAnimationFrame(raf); if (e.isIntersecting) raf = requestAnimationFrame(draw); });
    vis.observe(cv);
  }

  /* ---------- modal ---------- */
  function modal(html) {
    const m = document.createElement('div'); m.className = 'modal'; m.innerHTML = `<div class="modal__box" role="dialog" aria-modal="true">${html}</div>`;
    document.body.appendChild(m); requestAnimationFrame(() => m.classList.add('is-open'));
    const fechar = () => { m.classList.remove('is-open'); setTimeout(() => m.remove(), 300); };
    m.addEventListener('click', e => { if (e.target === m || e.target.closest('[data-fechar]')) fechar(); });
    addEventListener('keydown', function k(e) { if (e.key === 'Escape') { fechar(); removeEventListener('keydown', k); } });
    return { el: m, fechar };
  }

  const dataBR = ts => new Date(ts * 1000).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });

  header(); footer();
  document.addEventListener('DOMContentLoaded', () => efeitos());
  if (document.readyState !== 'loading') efeitos();

  window.EIA = { $, $$, api, eu, exigir, sair, esc, brl, moeda, qs, avatar, capa, cardCurso, skeletonCards, md, toast, confete, efeitos, abas, rede, modal, horas, dataBR, refAtual, PAINEL, PAPEL_NOME, reduce };
})();
