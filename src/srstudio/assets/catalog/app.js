/* The catalog app: hash routes over catalog.json, in plain JavaScript (ADR 0046).
   Every view is rendered from the document, so only that view's images and videos exist in the page. The base page's
   own sections (the six packages, the engine inventory) are shown by route, and its script runs the first time one
   of them is opened. Text from the document is escaped; only the fields named *_html are curated markup. */
(function () {
  'use strict';

  const KINDS = {
    character: {route: 'personagens', label: 'Personagens', one: 'Personagem'},
    location: {route: 'locacoes', label: 'Locações', one: 'Locação'},
    prop: {route: 'objetos', label: 'Objetos', one: 'Objeto'},
    graphic: {route: 'graficos', label: 'Gráficos', one: 'Gráfico'},
  };
  const KIND_OF_ROUTE = Object.fromEntries(Object.entries(KINDS).map(([kind, k]) => [k.route, kind]));
  const BASE_SECTIONS = {
    '': ['.hero', 'footer'],
    pacotes: ['#episodios', '#elenco', '#usado', '#comparativo'],
    motor: ['#motor', '#pipeline', '#audio'],
  };
  const NONE = 'nenhum'; // the filter value for "no style"

  const app = document.getElementById('app');
  const base = document.getElementById('base');
  const search = document.getElementById('search');
  let C = null;
  let videos = new Map();
  let parts = new Map();
  let styles = new Map();
  let baseRan = false;
  let lastRoute = '#/';
  let current = location.hash;
  let fresh = false;
  const scrolled = new Map();

  const esc = s => String(s).replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`);
  const norm = s => String(s).normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
  const seconds = t => t.toFixed(1).replace('.', ',') + ' s';
  const clock = t => `${Math.floor(t / 60)}:${(t % 60).toFixed(2).padStart(5, '0')}`;
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const videoCount = n => plural(n, 'vídeo', 'vídeos');
  const slugLink = s => encodeURIComponent(s);
  const partHref = p => `#/${KINDS[p.kind].route}/${slugLink(p.name)}`;
  const videoHref = v => `#/videos/${slugLink(v.slug)}`;
  const styleHref = s => `#/estilos/${slugLink(s.slug)}`;

  function styleTag(slug) {
    const s = styles.get(slug);
    return s ? `<span class="style-tag ${esc(s.slug)}">${esc(s.name)}</span>` : '';
  }
  function firstStill(p) {
    if (p.gallery.length) return p.gallery[0].still;
    return p.sheet.length ? p.sheet[0] : null;
  }
  function image(src, alt, width, height) {
    return `<img src="${esc(src)}" alt="${esc(alt)}" width="${width}" height="${height}" loading="lazy" decoding="async">`;
  }

  // -- cards ----------------------------------------------------------------------------------------------
  function videoTags(v) {
    const tags = [];
    if (v.source === 'package') tags.push('<span class="tag">pacote</span>');
    if (v.source === 'no-render') tags.push('<span class="tag warn">sem render</span>');
    if (!v.measured) tags.push('<span class="tag warn">não medido</span>');
    return tags.join('');
  }
  function videoCard(v) {
    const frame = v.poster
      ? image(v.poster, v.title, v.width, v.height)
      : esc(v.source === 'package' ? 'pacote em SVG' : 'sem render');
    const facts = [v.number, v.duration ? seconds(v.duration) : ''].filter(Boolean).join(' · ');
    return `<a class="card" href="${videoHref(v)}" data-video="${esc(v.slug)}"><div class="frame">${frame}</div>` +
      `<b>${esc(v.title)}</b><small>${esc(facts)}</small><div class="tags">${styleTag(v.style)}${videoTags(v)}</div></a>`;
  }
  function usageLabel(p) {
    if (!C.measured) return '<small>uso não medido</small>';
    return `<small>${videoCount(p.videos.length)}</small>`;
  }
  function partCard(p) {
    const s = firstStill(p);
    const frame = s ? image(s.src, p.title, s.width, s.height) : 'sem imagem';
    const tags = [styleTag(p.style)];
    if (C.measured && !p.videos.length) tags.push('<span class="tag warn">não usado</span>');
    if (!s) tags.push('<span class="tag warn">sem still</span>');
    return `<a class="card" href="${partHref(p)}" data-part="${esc(p.name)}"><div class="frame">${frame}</div>` +
      `<b>${esc(p.title)}</b><code>${esc(p.name)}</code>${usageLabel(p)}<div class="tags">${tags.join('')}</div></a>`;
  }
  function styleCard(s) {
    const first = s.videos.map(slug => videos.get(slug)).find(v => v.poster);
    const frame = first ? image(first.poster, s.name, first.width, first.height) : 'sem imagem';
    return `<a class="card" href="${styleHref(s)}" data-style="${esc(s.slug)}"><div class="frame">${frame}</div>` +
      `<b>${esc(s.name)}</b><small>${videoCount(s.videos.length)} · ${plural(s.parts.length, 'peça', 'peças')}</small></a>`;
  }
  const grid = (cards, id) => `<div class="grid"${id ? ` id="${id}"` : ''}>${cards.join('')}</div>`;

  // -- the indexes ----------------------------------------------------------------------------------------
  function filters(route, items, chosen, noneLabel) {
    const present = new Set(items.map(x => x.style));
    const link = (value, label) => {
      const href = value ? `#/${route}?estilo=${encodeURIComponent(value)}` : `#/${route}`;
      return `<a href="${href}" aria-current="${chosen === value}">${esc(label)}</a>`;
    };
    const chips = [link('', 'Todos')];
    C.styles.filter(s => present.has(s.slug)).forEach(s => chips.push(link(s.slug, s.name)));
    if (present.has('')) chips.push(link(NONE, noneLabel));
    return `<div class="filters" aria-label="Filtrar por estilo">${chips.join('')}</div>`;
  }
  const chosen = (items, value) =>
    value ? items.filter(x => x.style === (value === NONE ? '' : value)) : items;

  function head(title, lede) {
    return `<div class="view-head"><h2>${esc(title)}</h2>${lede ? `<p class="lede">${lede}</p>` : ''}</div>`;
  }
  function viewVideos(id, params) {
    if (id) return viewVideo(id);
    const value = params.get('estilo') || '';
    const shown = chosen(C.videos, value);
    const lede = `${videoCount(shown.length)} de ${C.videos.length}. Clique para abrir o player, as falas e as peças.`;
    return {
      title: 'Vídeos',
      html: head('Vídeos', esc(lede)) + filters('videos', C.videos, value, 'Sem estilo') +
        grid(shown.map(videoCard), 'index'),
    };
  }
  function viewParts(kind, id, params) {
    if (id) return viewPart(kind, id);
    const k = KINDS[kind];
    const all = C.parts.filter(p => p.kind === kind);
    const value = params.get('estilo') || '';
    const shown = chosen(all, value);
    const unused = all.filter(p => !p.videos.length).length;
    const lede = `${shown.length} de ${all.length}` + (C.measured ? `; ${unused} sem uso medido.` : '.');
    return {
      title: k.label,
      html: head(k.label, esc(lede)) + filters(k.route, all, value, 'Compartilhadas') +
        grid(shown.map(partCard), 'index'),
    };
  }
  function viewStyles(id) {
    if (id) return viewStyle(id);
    return {title: 'Estilos', html: head('Estilos', `${C.styles.length} estilos nomeados.`) + grid(C.styles.map(styleCard), 'index')};
  }

  // -- the details ----------------------------------------------------------------------------------------
  const missing = what => ({title: 'Não encontrado', html: head('Não encontrado', `${esc(what)} não está no catálogo. <a href="#/">Voltar ao início</a>.`)});

  function groupedParts(names) {
    return Object.entries(KINDS).map(([kind, k]) => {
      const own = names.map(n => parts.get(n)).filter(p => p.kind === kind);
      if (!own.length) return '';
      const shared = title => own.filter(p => p.title === title).length > 1; // one gallery item can show several
      const pills = own.map(p =>
        `<a href="${partHref(p)}" data-part="${esc(p.name)}">${esc(shared(p.title) ? p.name : p.title)}</a>`);
      return `<div class="sub">${k.label} (${own.length})</div><div class="pills">${pills.join('')}</div>`;
    }).join('');
  }
  function unmeasuredNote() {
    return C.unmeasured.length ? `<p class="notice">Não medidos: ${C.unmeasured.map(esc).join(', ')}. Eles podem usar peças que esta lista não mostra.</p>` : '';
  }
  function viewVideo(slug) {
    const v = videos.get(slug);
    if (!v) return missing(`O vídeo ${slug}`);
    const spoken = v.lines.filter(x => !x.sfx);
    const voices = [...new Set(v.lines.map(x => x.voice).filter(Boolean))].sort().join(', ') || '—';
    const facts = [
      [v.duration ? seconds(v.duration) : '—', 'duração'], [v.format || '—', 'formato'],
      [v.fps ? `${v.fps} fps` : '—', 'quadros'], [spoken.length, 'falas'], [v.effects, 'efeitos'], [voices, 'vozes'],
    ].map(([value, key]) => `<div class="fact"><b>${esc(value)}</b><span>${key}</span></div>`).join('');
    const rows = v.lines.map(x =>
      `<button type="button" class="line" data-t="${x.t.toFixed(3)}"><span class="t">${clock(x.t)}</span>` +
      `<span class="who">${esc(x.who)}<small>${esc(x.voice)}</small></span>` +
      `<span class="txt">${x.sfx ? `<span class="sfx">${esc(x.text)}</span>` : esc(x.text)}</span></button>`).join('');
    const ratio = v.width && v.height ? ` style="aspect-ratio:${v.width}/${v.height}"` : '';
    let player;
    if (v.src) {
      player = `<div class="phone"${ratio}><video controls playsinline preload="none" poster="${esc(v.poster)}" ` +
        `src="${esc(v.src)}" aria-label="${esc(v.title)}"></video></div>`;
    } else if (v.source === 'package') {
      player = `<p class="notice">Pacote original, tocado como SVG. <a href="#/pacotes/${slugLink(v.slug)}">Abrir no player</a>.</p>`;
    } else {
      player = '<p class="notice">Este projeto não tem render, então não há vídeo para tocar.</p>';
    }
    const highlights = v.highlights_html.length ? `<ul class="hl">${v.highlights_html.map(h => `<li>${h}</li>`).join('')}</ul>` : '';
    const used = v.measured
      ? (v.parts.length ? groupedParts(v.parts) : '<p class="notice">A medição não encontrou peças registradas neste vídeo.</p>')
      : '<p class="notice" id="not-measured">Não medido: <code>srstudio usage</code> não reconstruiu este episódio, então não se sabe que peças ele usa.</p>';
    const style = styles.get(v.style);
    return {
      title: v.title,
      html: `<article class="detail" data-video="${esc(v.slug)}"><div class="view-head"><a href="#/videos">Vídeos</a>` +
        `<h2>${esc(v.title)}</h2><div class="tags">${styleTag(v.style)}${videoTags(v)}</div>` +
        `<p class="lede">${esc(v.lede)}</p>` +
        (style ? `<a href="${styleHref(style)}" data-style-link="${esc(style.slug)}">Estilo ${esc(style.name)}</a>` : '') +
        `</div><div class="detail-grid"><div>${player}</div><div class="ep-info"><div class="facts">${facts}</div>${highlights}` +
        (rows ? `<div class="dialog lib-dialog">${rows}</div>` : '') +
        `</div></div><section class="used">${used}</section></article>`,
    };
  }
  function figure(s, alt, lead) {
    const from = s.video && videos.has(s.video) ? ` · <a href="${videoHref(videos.get(s.video))}">${esc(videos.get(s.video).title)}</a>` : '';
    const caption = [esc(s.label)].filter(Boolean).join('') + (lead ? from : '');
    return `<figure>${image(s.src, alt, s.width, s.height)}${caption ? `<figcaption>${caption}</figcaption>` : ''}</figure>`;
  }
  function viewPart(kind, name) {
    const p = parts.get(name);
    const k = KINDS[kind];
    if (!p || p.kind !== kind) return missing(`${k.one} ${name}`);
    const gallery = p.gallery.map(g =>
      `<div class="stills lead">${figure(g.still, g.name, true)}</div>` +
      (g.voice ? `<p>voz ${esc(g.voice)} (ElevenLabs)</p>` : '') + `<p class="note">${g.note_html}</p>` +
      (g.poses.length ? `<div class="stills">${g.poses.map(s => figure(s, `${g.name}, ${s.label}`, false)).join('')}</div>` : '')).join('');
    const sheet = p.sheet.length
      ? `<div class="sub">Folha de poses</div><div class="stills" id="pose-sheet">${p.sheet.map(s => figure(s, `${p.title}, pose ${s.label}`, false)).join('')}</div>`
      : '';
    const noStill = !p.gallery.length && !p.sheet.length ? '<p class="notice" id="no-still">Nenhum item da galeria mostra esta peça ainda.</p>' : '';
    let used;
    if (!C.measured) used = '<p class="notice">Uso não medido: o catálogo foi gerado sem o relatório de <code>srstudio usage</code>.</p>';
    else if (!p.videos.length) used = `<p class="notice" id="unused">Não usado: nenhum episódio medido chama esta peça.</p>${unmeasuredNote()}`;
    else used = grid(p.videos.map(slug => videoCard(videos.get(slug))), 'part-videos') + unmeasuredNote();
    return {
      title: p.title,
      html: `<article class="detail" data-part="${esc(p.name)}"><div class="view-head"><a href="#/${k.route}">${k.label}</a>` +
        `<h2>${esc(p.title)}</h2><code>${esc(p.name)}</code><div class="tags">${styleTag(p.style)}</div>` +
        `<p class="lede">${esc(p.summary)}</p></div>${noStill}${gallery}${sheet}` +
        `<div class="sub">Aparece em ${C.measured ? videoCount(p.videos.length) : ''}</div>${used}</article>`,
    };
  }
  function viewStyle(slug) {
    const s = styles.get(slug);
    if (!s) return missing(`O estilo ${slug}`);
    const byKind = Object.entries(KINDS).map(([kind, k]) => {
      const own = s.parts.map(n => parts.get(n)).filter(p => p.kind === kind);
      return own.length ? `<div class="sub">${k.label} (${own.length})</div>${grid(own.map(partCard))}` : '';
    }).join('');
    return {
      title: s.name,
      html: `<article class="detail" data-style="${esc(s.slug)}"><div class="view-head"><a href="#/estilos">Estilos</a>` +
        `<h2>${esc(s.name)}</h2><b>${esc(s.title)}</b><p class="lede">${s.text_html}</p>` +
        (s.text_html === esc(s.summary) ? '' : `<p>${esc(s.summary)}</p>`) + '</div>' +
        `<div class="sub">Vídeos (${s.videos.length})</div>${grid(s.videos.map(v => videoCard(videos.get(v))), 'style-videos')}` +
        byKind + '</article>',
    };
  }

  // -- the registry and the usage lists -------------------------------------------------------------------
  function viewRegistry() {
    const links = names => names.map(n => `<a href="#/videos/${slugLink(n)}">${esc(n)}</a>`).join(', ') || '—';
    const rows = [...C.parts].sort((a, b) => a.name < b.name ? -1 : 1).map(p =>
      `<tr><td><a href="${partHref(p)}"><code>${esc(p.name)}</code></a></td>` +
      `<td>${esc(styles.has(p.style) ? styles.get(p.style).name : 'todos')}</td><td>${KINDS[p.kind].one}</td>` +
      `<td>${esc(p.summary)}</td><td>${links(p.videos)}</td></tr>`).join('');
    const blocks = Object.entries(KINDS).map(([kind, k]) => {
      const all = C.parts.filter(p => p.kind === kind);
      const used = all.filter(p => p.videos.length);
      const unused = all.filter(p => !p.videos.length);
      const item = p => `<li><a href="${partHref(p)}"><code>${esc(p.name)}</code></a> <small>${esc(p.summary)}</small></li>`;
      return `<div class="lib-usage-kind" id="usage-${kind}"><h3>${k.label}</h3>` +
        `<p><b>${used.length}</b> usados · <b>${unused.length}</b> não usados</p><ul>` +
        used.map(p => `<li><a href="${partHref(p)}"><code>${esc(p.name)}</code></a> <small>${esc(p.videos.join(', '))}</small></li>`).join('') +
        `</ul><p><b>Não usados</b></p><ul>${unused.map(item).join('') || '<li>nenhum</li>'}</ul></div>`;
    }).join('');
    const measured = C.videos.filter(v => v.measured).map(v => esc(v.slug)).join(', ');
    const notMeasured = C.unmeasured.length ? ` Sem script, não medidos: ${C.unmeasured.map(esc).join(', ')}.` : '';
    const usage = C.measured
      ? `<div class="sub">Peças usadas e não usadas</div><div class="lib-usage" id="lib-usage"><p>Medido por ` +
        `<code>srstudio usage</code>, que reconstrói cada episódio e registra as peças chamadas: ${measured}.${notMeasured}</p>${blocks}</div>`
      : '<p class="notice">Uso não medido: o catálogo foi gerado sem o relatório de <code>srstudio usage</code>.</p>';
    return {
      title: 'Registro',
      html: head('Registro de peças', `${C.parts.length} peças registradas.`) +
        `<div class="tbl"><table class="lib-registry"><thead><tr><th>Peça</th><th>Estilo</th><th>Tipo</th><th>Resumo</th>` +
        `<th>Episódios</th></tr></thead><tbody>${rows}</tbody></table></div>${usage}`,
    };
  }

  // -- search ---------------------------------------------------------------------------------------------
  function viewSearch(query) {
    const q = norm(query);
    const hit = names => names.some(n => norm(n).includes(q));
    const found = {
      Estilos: C.styles.filter(s => hit([s.name, s.slug, s.title])).map(styleCard),
      Vídeos: C.videos.filter(v => hit([v.title, v.slug, v.number])).map(videoCard),
    };
    Object.entries(KINDS).forEach(([kind, k]) => {
      found[k.label] = C.parts.filter(p => p.kind === kind && hit([p.title, p.name, ...p.gallery.map(g => g.name)])).map(partCard);
    });
    const topics = C.engine.filter(t => hit([t])).map(t => `<a href="#/motor">${esc(t)}</a>`);
    const total = Object.values(found).reduce((n, cards) => n + cards.length, 0) + topics.length;
    const sections = ['Estilos', 'Personagens', 'Locações', 'Objetos', 'Gráficos', 'Vídeos']
      .filter(label => found[label].length)
      .map(label => `<div class="sub">${label} (${found[label].length})</div>${grid(found[label])}`).join('');
    const engine = topics.length ? `<div class="sub">Motor (${topics.length})</div><div class="pills">${topics.join('')}</div>` : '';
    return {
      title: `Busca: ${query}`,
      html: head('Busca', `${plural(total, 'resultado', 'resultados')} para “${esc(query)}”.`) +
        `<div id="results">${sections}${engine}</div>`,
    };
  }

  function viewHome() {
    const count = kind => C.parts.filter(p => p.kind === kind).length;
    const tiles = [
      ['#/estilos', C.styles.length, 'Estilos'], ['#/personagens', count('character'), 'Personagens'],
      ['#/locacoes', count('location'), 'Locações'], ['#/objetos', count('prop'), 'Objetos'],
      ['#/graficos', count('graphic'), 'Gráficos'], ['#/videos', C.videos.length, 'Vídeos'],
      ['#/pacotes', C.videos.filter(v => v.source === 'package').length, 'Pacotes'],
      ['#/registro', C.parts.length, 'Registro de peças'], ['#/motor', C.engine.length, 'Temas do motor'],
    ];
    return {title: '', html: `<div class="tiles-nav">${tiles.map(([href, n, label]) => `<a href="${href}"><b>${n}</b><span>${label}</span></a>`).join('')}</div>`};
  }

  // -- the router -----------------------------------------------------------------------------------------
  function decode(s) {
    try { return decodeURIComponent(s); } catch (err) { return s; }
  }
  function parseHash() {
    const raw = location.hash.replace(/^#\/?/, '');
    const cut = raw.indexOf('?');
    const path = cut < 0 ? raw : raw.slice(0, cut);
    const [section = '', ...rest] = path.split('/').filter(Boolean).map(decode);
    return {section, id: rest.join('/'), params: new URLSearchParams(cut < 0 ? '' : raw.slice(cut + 1))};
  }
  function viewOf(route) {
    const {section, id, params} = route;
    if (section === '') return viewHome();
    if (section === 'videos') return viewVideos(id, params);
    if (section === 'estilos') return viewStyles(id);
    if (section === 'registro') return viewRegistry();
    if (section === 'busca') return viewSearch(id);
    if (section === 'pacotes') return {title: 'Pacotes', html: ''};
    if (section === 'motor') return {title: 'Motor', html: ''};
    if (KIND_OF_ROUTE[section]) return viewParts(KIND_OF_ROUTE[section], id, params);
    return missing(`A página ${section}`);
  }
  function stopMedia() {
    app.querySelectorAll('video').forEach(v => { v.pause(); v.removeAttribute('src'); v.load(); });
  }
  function showBase(section) {
    Array.from(base.children).forEach(el => { if (el !== app) el.classList.remove('on'); });
    (BASE_SECTIONS[section] || []).forEach(selector => {
      const el = base.querySelector(`:scope > ${selector}`);
      if (el) el.classList.add('on');
    });
    if (BASE_SECTIONS[section] && section && !baseRan && window.srstudioBase) {
      baseRan = true;
      window.srstudioBase();
    }
  }
  function render() {
    const route = parseHash();
    if (route.section !== 'busca') {
      lastRoute = location.hash || '#/';
      search.value = '';
    } else if (norm(search.value.trim()) !== norm(route.id)) {
      search.value = route.id;
    }
    document.querySelectorAll('.nav-links a').forEach(a => {
      if (a.getAttribute('href') === `#/${route.section}`) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    stopMedia();
    showBase(route.section);
    const view = viewOf(route);
    app.innerHTML = view.html;
    document.title = view.title ? `${view.title} · Catálogo Scene-Render` : 'Catálogo Scene-Render';
  }
  function afterRender() {
    const route = parseHash();
    const target = route.section === 'pacotes' && route.id ? document.getElementById(`ep-${route.id}`) : null;
    if (target) target.scrollIntoView();
    else window.scrollTo(0, fresh ? 0 : scrolled.get(location.hash) || 0);
    fresh = false;
  }

  document.addEventListener('click', event => {
    if (event.target.closest && event.target.closest('a[href^="#/"]')) fresh = true;
  });
  window.addEventListener('hashchange', () => {
    scrolled.set(current, window.scrollY);
    current = location.hash;
    if (!C) return;
    render();
    afterRender();
  });
  search.addEventListener('input', () => {
    const q = search.value.trim();
    if (!q) {
      location.hash = lastRoute;
      return;
    }
    const target = `#/busca/${encodeURIComponent(q)}`;
    if (parseHash().section === 'busca') {
      history.replaceState(null, '', target);
      current = location.hash;
      render();
    } else {
      location.hash = target;
    }
  });

  // A line seeks its video. With nothing preloaded a video has no timeline before its metadata, so the seek waits for
  // it; play() is what starts the loading. Clicks in a row each queue a seek, in order, so the last one stands.
  app.addEventListener('click', event => {
    const line = event.target.closest('.line');
    const video = app.querySelector('video');
    if (!line || !video) return;
    const t = parseFloat(line.dataset.t);
    if (video.readyState >= 1) video.currentTime = t;
    else video.addEventListener('loadedmetadata', () => { video.currentTime = t; }, {once: true});
    video.play().catch(() => {});
  });
  app.addEventListener('timeupdate', event => {
    const lines = Array.from(app.querySelectorAll('.line'));
    const now = event.target.currentTime;
    let active = null;
    lines.forEach(b => { if (!b.querySelector('.sfx') && parseFloat(b.dataset.t) <= now + 0.05) active = b; });
    lines.forEach(b => b.classList.toggle('active', b === active));
  }, true);

  function fail(message) {
    app.innerHTML = `<p class="notice" id="load-error">${esc(message)}</p>`;
  }

  history.scrollRestoration = 'manual';
  showBase(parseHash().section);
  fetch('catalog.json', {cache: 'no-cache'})
    .then(response => {
      if (!response.ok) throw new Error(`catalog.json: HTTP ${response.status}`);
      return response.json();
    })
    .then(doc => {
      if (!/^1\./.test(doc.schema_version)) throw new Error(`catalog.json: schema ${doc.schema_version}`);
      C = doc;
      videos = new Map(C.videos.map(v => [v.slug, v]));
      parts = new Map(C.parts.map(p => [p.name, p]));
      styles = new Map(C.styles.map(s => [s.slug, s]));
      render();
      afterRender();
    })
    .catch(err => fail(`Não foi possível ler o catálogo (${err.message}). Abra o site com srstudio serve.`));
})();
