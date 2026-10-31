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
    '': ['footer'],
    pacotes: ['#episodios', '#elenco', '#usado', '#comparativo'],
    motor: ['#motor', '#pipeline', '#audio'],
  };
  const NONE = 'nenhum'; // the filter value for "no style"
  const byTitle = (a, b) => a.title.localeCompare(b.title, 'pt');
  const VIDEO_SORTS = {
    '': {label: 'Catálogo'},
    titulo: {label: 'Título', by: byTitle},
    duracao: {label: 'Mais longos', by: (a, b) => b.duration - a.duration},
    pecas: {label: 'Mais peças', by: (a, b) => b.parts.length - a.parts.length},
  };
  const PART_SORTS = {
    '': {label: 'Catálogo'},
    titulo: {label: 'Título', by: byTitle},
    uso: {label: 'Mais usados', by: (a, b) => videosOf(b).length - videosOf(a).length},
  };

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
  const minutes = t => `${Math.round(t / 60)} min`;
  const clock = t => `${Math.floor(t / 60)}:${(t % 60).toFixed(2).padStart(5, '0')}`;
  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
  const videoCount = n => plural(n, 'vídeo', 'vídeos');
  const slugLink = s => encodeURIComponent(s);
  const COPY_ICON = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" ' +
    'aria-hidden="true"><rect x="5.5" y="5.5" width="8" height="8" rx="1.5"/><path d="M10.5 3.5v-1h-8v8h1"/></svg>';
  const copyButton = (text, what) =>
    `<button type="button" class="copy" data-copy="${esc(text)}" title="Copiar ${esc(what)}" ` +
    `aria-label="Copiar ${esc(what)}">${COPY_ICON}</button>`;
  const named = (name, what = 'nome') => `<span class="named"><code>${esc(name)}</code>${copyButton(name, what)}</span>`;
  function plainText(markup) {
    const holder = document.createElement('template');
    holder.innerHTML = markup;
    return holder.content.textContent;
  }
  const script = lines => lines.map(x => x.sfx ? `[${x.text.replace(/^\[|\]$/g, '')}]` : `${x.who}: ${x.text}`).join('\n');
  const partHref = p => `#/${KINDS[p.kind].route}/${slugLink(p.name)}`;
  const videoHref = v => `#/videos/${slugLink(v.slug)}`;
  const styleHref = s => `#/estilos/${slugLink(s.slug)}`;

  function styleTag(slug) {
    const s = styles.get(slug);
    return s ? `<span class="style-tag ${esc(s.slug)}">${esc(s.name)}</span>` : '';
  }
  function image(src, alt, width, height) {
    return `<img src="${esc(src)}" alt="${esc(alt)}" width="${width}" height="${height}" loading="lazy" decoding="async">`;
  }

  // -- cards ----------------------------------------------------------------------------------------------
  // The series of the pilots (ADR 0054), by folder name; one the table does not know shows as its folder name.
  const SERIES = {mind: "There's a Name for That", maps: 'Maps', news: 'News Compiler', host: 'The Unwritten Rules'};
  function videoTags(v) {
    const tags = [];
    if (v.series) tags.push(`<span class="tag series">piloto · ${esc(SERIES[v.series] || v.series)}</span>`);
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
  // A later version is a drawing in the registry, not another part: an index lists its character once, and the
  // character answers for every version it has.
  const listed = kind => C.parts.filter(p => p.kind === kind && !p.version_of);
  const drawingsOf = p => [p, ...p.versions.filter(v => v.part && v.part !== p.name).map(v => parts.get(v.part))];
  const videosOf = p => [...new Set(drawingsOf(p).flatMap(d => d.videos))];
  // A lone version that only says the drawing stood as it was when versions began is not a history.
  const hasHistory = p => p.versions.length > 1 ||
    p.versions.some(v => v.status === 'proposed' || v.approval || v.proof || v.proof_path || v.pins.length || v.rig);
  function defaultDrawing(p) {
    const v = p.versions.find(x => x.default);
    return v && v.part ? parts.get(v.part) : p;
  }
  function versionTags(p) {
    const proposed = p.versions.filter(v => v.status === 'proposed').length;
    return (p.versions.length > 1 ? `<span class="tag">${plural(p.versions.length, 'versão', 'versões')}</span>` : '') +
      (proposed ? `<span class="tag warn">${plural(proposed, 'proposta', 'propostas')}</span>` : '');
  }
  function usageLabel(p) {
    if (!C.measured) return '<small>uso não medido</small>';
    return `<small>${videoCount(videosOf(p).length)}</small>`;
  }
  function partCard(p) {
    const drawn = defaultDrawing(p);
    const s = drawn.specimen; // the part alone, drawn by the engine; a refused part has none, and says why
    const frame = s ? image(s.src, p.title, s.width, s.height) : esc(drawn.refused);
    const tags = [styleTag(p.style), versionTags(p)];
    if (C.measured && !videosOf(p).length) tags.push('<span class="tag warn">não usado</span>');
    if (!s) tags.push('<span class="tag warn">sem desenho isolado</span>');
    return `<a class="card" href="${partHref(p)}" data-part="${esc(p.name)}"><div class="frame specimen">${frame}</div>` +
      `<b>${esc(p.title)}</b><code>${esc(p.name)}</code>${usageLabel(p)}<div class="tags">${tags.join('')}</div></a>`;
  }
  function styleCard(s) {
    const first = s.videos.map(slug => videos.get(slug)).find(v => v.poster);
    const frame = first ? image(first.poster, s.name, first.width, first.height) : 'sem imagem';
    return `<a class="card" href="${styleHref(s)}" data-style="${esc(s.slug)}"><div class="frame">${frame}</div>` +
      `<b>${esc(s.name)}</b><small>${videoCount(s.videos.length)} · ${plural(s.parts.length, 'peça', 'peças')}</small></a>`;
  }
  const grid = (cards, id) => `<div class="grid"${id ? ` id="${id}"` : ''}>${cards.join('')}</div>`;
  function table(heads, rows, id) {
    const th = heads.map(h => `<th${h.num ? ' class="num"' : ''}>${esc(h.label || '')}</th>`).join('');
    return `<div class="tbl"${id ? ` id="${id}"` : ''}><table class="rows"><thead><tr>${th}</tr></thead>` +
      `<tbody>${rows.join('')}</tbody></table></div>`;
  }
  const thumb = (src, alt, width, height, kind = '') =>
    `<td class="pic${kind}">${src ? image(src, alt, width, height) : ''}</td>`;
  function videoRow(v) {
    return `<tr class="row" data-video="${esc(v.slug)}">${thumb(v.poster, v.title, v.width, v.height)}` +
      `<td><a href="${videoHref(v)}"><b>${esc(v.title)}</b></a>${named(v.slug)}</td>` +
      `<td>${styleTag(v.style)}${videoTags(v)}</td><td>${esc(v.number)}</td><td>${esc(v.format)}</td>` +
      `<td class="num">${v.duration ? seconds(v.duration) : '—'}</td><td class="num">${v.parts.length}</td></tr>`;
  }
  function partRow(p) {
    const s = defaultDrawing(p).specimen;
    return `<tr class="row" data-part="${esc(p.name)}">${s ? thumb(s.src, p.title, s.width, s.height, ' specimen') : thumb()}` +
      `<td><a href="${partHref(p)}"><b>${esc(p.title)}</b></a>${named(p.name)}</td>` +
      `<td>${styleTag(p.style)}${versionTags(p)}</td><td class="num">${C.measured ? videosOf(p).length : '—'}</td>` +
      `<td class="summary">${esc(p.summary)}${p.refused ? `<small>${esc(p.refused)}</small>` : ''}</td></tr>`;
  }
  const VIDEO_HEADS = [{}, {label: 'Vídeo'}, {label: 'Estilo'}, {label: 'Nº'}, {label: 'Formato'},
    {label: 'Duração', num: true}, {label: 'Peças', num: true}];
  const PART_HEADS = [{}, {label: 'Peça'}, {label: 'Estilo'}, {label: 'Vídeos', num: true}, {label: 'Resumo'}];

  // -- the indexes ----------------------------------------------------------------------------------------
  function query(params, change) {
    const next = new URLSearchParams(params);
    Object.entries(change).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
    const text = next.toString();
    return text ? `?${text}` : '';
  }
  function filters(route, items, params, noneLabel) {
    const value = params.get('estilo') || '';
    const link = (slug, label, n) =>
      `<a href="#/${route}${query(params, {estilo: slug})}" aria-current="${value === slug}">${esc(label)}<small>${n}</small></a>`;
    const of = slug => items.filter(x => x.style === slug).length;
    const chips = [link('', 'Todos', items.length)];
    C.styles.filter(s => of(s.slug)).forEach(s => chips.push(link(s.slug, s.name, of(s.slug))));
    if (of('')) chips.push(link(NONE, noneLabel, of('')));
    return `<div class="filters" aria-label="Filtrar por estilo">${chips.join('')}</div>`;
  }
  function segmented(route, params, key, options, label) {
    const value = params.get(key) || '';
    const links = options.map(([option, text]) =>
      `<a href="#/${route}${query(params, {[key]: option})}" aria-current="${value === option}">${esc(text)}</a>`);
    return `<div class="seg" role="group" aria-label="${esc(label)}">${links.join('')}</div>`;
  }
  function sorter(route, params, sorts) {
    const value = params.get('ordem') || '';
    const options = Object.entries(sorts).map(([key, sort]) =>
      `<option value="#/${route}${query(params, {ordem: key})}"${key === value ? ' selected' : ''}>${esc(sort.label)}</option>`);
    return `<label class="sort">Ordenar <select id="sort">${options.join('')}</select></label>`;
  }
  const chosen = (items, value) =>
    value ? items.filter(x => x.style === (value === NONE ? '' : value)) : items;
  function sorted(items, sorts, params) {
    const sort = sorts[params.get('ordem') || ''];
    return sort && sort.by ? [...items].sort(sort.by) : items;
  }
  const VIEWS = [['', 'Grade'], ['lista', 'Lista']];

  function head(title, lede) {
    return `<div class="view-head"><h2>${esc(title)}</h2>${lede ? `<p class="lede">${lede}</p>` : ''}</div>`;
  }
  function toolbar(filter, tools) {
    return `<div class="toolbar">${filter}<div class="tools">${tools.join('')}</div></div>`;
  }
  function viewVideos(id, params) {
    if (id) return viewVideo(id);
    const shown = sorted(chosen(C.videos, params.get('estilo') || ''), VIDEO_SORTS, params);
    const body = params.get('ver') === 'lista'
      ? table(VIDEO_HEADS, shown.map(videoRow), 'index')
      : grid(shown.map(videoCard), 'index');
    return {
      title: 'Vídeos',
      html: head('Vídeos', esc(shown.length === C.videos.length ? videoCount(shown.length) : `${shown.length} de ${C.videos.length}`)) +
        toolbar(filters('videos', C.videos, params, 'Sem estilo'),
          [sorter('videos', params, VIDEO_SORTS), segmented('videos', params, 'ver', VIEWS, 'Exibição')]) + body,
    };
  }
  function viewParts(kind, id, params) {
    if (id) return viewPart(kind, id);
    const k = KINDS[kind];
    const all = listed(kind);
    const use = params.get('uso') || '';
    const used = {'': () => true, sim: p => videosOf(p).length, nao: p => !videosOf(p).length}[use] || (() => true);
    const shown = sorted(chosen(all, params.get('estilo') || '').filter(used), PART_SORTS, params);
    const body = params.get('ver') === 'lista'
      ? table(PART_HEADS, shown.map(partRow), 'index')
      : grid(shown.map(partCard), 'index');
    const tools = [sorter(k.route, params, PART_SORTS), segmented(k.route, params, 'ver', VIEWS, 'Exibição')];
    if (C.measured) tools.unshift(segmented(k.route, params, 'uso', [['', 'Todos'], ['sim', 'Usados'], ['nao', 'Sem uso']], 'Uso'));
    return {
      title: k.label,
      html: head(k.label, esc(shown.length === all.length ? `${all.length} no total` : `${shown.length} de ${all.length}`)) +
        toolbar(filters(k.route, all, params, 'Compartilhadas'), tools) + body,
    };
  }
  function viewStyles(id, params) {
    if (id) return viewStyle(id, params);
    return {title: 'Estilos', html: head('Estilos', `${C.styles.length} estilos nomeados.`) + grid(C.styles.map(styleCard), 'index')};
  }

  // -- the details ----------------------------------------------------------------------------------------
  const missing = what => ({title: 'Não encontrado', html: head('Não encontrado', `${esc(what)} não está no catálogo. <a href="#/">Voltar ao início</a>.`)});

  function groupedParts(names) {
    return Object.entries(KINDS).map(([kind, k]) => {
      const own = names.map(n => parts.get(n)).filter(p => p.kind === kind);
      if (!own.length) return '';
      const shared = title => own.filter(p => p.title === title).length > 1; // a title from a summary can repeat
      const pills = own.map(p =>
        `<a href="${partHref(p)}" data-part="${esc(p.name)}">${esc(shared(p.title) ? p.name : p.title)}</a>`);
      return `<div class="sub">${k.label} (${own.length})</div><div class="pills">${pills.join('')}</div>`;
    }).join('');
  }
  const crumbs = (href, label, title) =>
    `<nav class="crumbs" aria-label="Caminho"><a href="${href}">${esc(label)}</a><span>/</span><span>${esc(title)}</span></nav>`;
  function ficha(rows) {
    const items = rows.filter(([, value]) => value !== '').map(([key, value]) => `<dt>${esc(key)}</dt><dd>${value}</dd>`);
    return `<dl class="ficha">${items.join('')}</dl>`;
  }
  function styleLink(slug) {
    const s = styles.get(slug);
    return s ? `<a href="${styleHref(s)}" data-style-link="${esc(s.slug)}">${esc(s.name)}</a>` : '';
  }
  function unmeasuredNote() {
    return C.unmeasured.length ? `<p class="notice">Não medidos: ${C.unmeasured.map(esc).join(', ')}. Eles podem usar peças que esta lista não mostra.</p>` : '';
  }
  function viewVideo(slug) {
    const v = videos.get(slug);
    if (!v) return missing(`O vídeo ${slug}`);
    const spoken = v.lines.filter(x => !x.sfx);
    const voices = [...new Set(v.lines.map(x => x.voice).filter(Boolean))].sort().join(', ') || '—';
    const rows = v.lines.map(x =>
      `<div class="line-row"><button type="button" class="line" data-t="${x.t.toFixed(3)}"><span class="t">${clock(x.t)}</span>` +
      `<span class="who">${esc(x.who)}<small>${esc(x.voice)}</small></span>` +
      `<span class="txt">${x.sfx ? `<span class="sfx">${esc(x.text)}</span>` : esc(x.text)}</span></button>` +
      `${x.sfx ? '' : copyButton(x.text, 'fala')}</div>`).join('');
    const ratio = v.width && v.height ? ` style="aspect-ratio:${v.width}/${v.height}"` : '';
    let player;
    if (v.src) {
      player = `<div class="phone"${ratio}><video controls playsinline preload="none" poster="${esc(v.poster)}" ` +
        `src="${esc(v.src)}" aria-label="${esc(v.title)}"></video></div>` +
        (v.source === 'package' ? `<p class="aside">Pacote original: <a href="#/pacotes/${slugLink(v.slug)}">abrir no player SVG</a>.</p>` : '');
    } else if (v.source === 'package') {
      player = `<p class="notice">Pacote original, tocado como SVG. <a href="#/pacotes/${slugLink(v.slug)}">Abrir no player</a>.</p>`;
    } else {
      player = '<p class="notice">Este projeto não tem render, então não há vídeo para tocar.</p>';
    }
    const highlights = v.highlights_html.length ? `<ul class="hl">${v.highlights_html.map(h => `<li>${h}${copyButton(plainText(h), 'destaque')}</li>`).join('')}</ul>` : '';
    const used = v.measured
      ? (v.parts.length ? groupedParts(v.parts) : '<p class="notice">A medição não encontrou peças registradas neste vídeo.</p>')
      : '<p class="notice" id="not-measured">Não medido: <code>srstudio usage</code> não reconstruiu este episódio, então não se sabe que peças ele usa.</p>';
    const sheet = ficha([
      ['Nome', named(v.slug)], ['Estilo', styleLink(v.style)], ['Número', esc(v.number)], ['Duração', v.duration ? seconds(v.duration) : '—'],
      ['Formato', esc(v.format || '—')], ['Quadros', v.fps ? `${v.fps} fps` : '—'], ['Falas', spoken.length],
      ['Efeitos', v.effects], ['Vozes', esc(voices)],
    ]);
    return {
      title: v.title,
      html: `<article class="detail" data-video="${esc(v.slug)}">${crumbs('#/videos', 'Vídeos', v.title)}` +
        `<div class="view-head"><h2>${esc(v.title)}${copyButton(v.title, 'título')}</h2><div class="tags">${styleTag(v.style)}${videoTags(v)}</div>` +
        `<p class="lede">${esc(v.lede)}${copyButton(v.lede, 'descrição')}</p></div><div class="detail-grid video"><div class="player-col">${player}</div>` +
        `<div class="ep-info">${highlights}` + (rows ? `<div class="sub">Falas (${v.lines.length})${copyButton(script(v.lines), 'roteiro')}</div><div class="dialog lib-dialog">${rows}</div>` : '') +
        `</div><aside class="side">${sheet}<section class="used">${used}</section></aside></div></article>`,
    };
  }
  function figure(s, alt, lead) {
    const from = s.video && videos.has(s.video) ? `<a href="${videoHref(videos.get(s.video))}">${esc(videos.get(s.video).title)}</a>` : '';
    const caption = [esc(s.label), lead ? from : ''].filter(Boolean).join(' · ');
    return `<figure>${image(s.src, alt, s.width, s.height)}${caption ? `<figcaption>${caption}</figcaption>` : ''}</figure>`;
  }
  const day = iso => iso.split('-').reverse().join('/');
  function versionPins(v) {
    if (v.status === 'proposed') return '';
    if (!C.pinned) return '<p class="pins">Fixações não lidas: o catálogo foi gerado sem os arquivos de release.</p>';
    if (!v.pins.length) return '<p class="pins">Nenhum reel fixa esta versão.</p>';
    const reels = v.pins.map(slug => (videos.has(slug) ? `<a href="${videoHref(videos.get(slug))}">${esc(videos.get(slug).title)}</a>` : `<code>${esc(slug)}</code>`));
    return `<div class="pins"><p>Fixada por ${plural(v.pins.length, 'reel', 'reels')}:</p><div class="pills">${reels.join('')}</div></div>`;
  }
  function proofLink(proof, path) {
    if (proof) return `<p><a class="proof" href="${esc(proof)}" target="_blank" rel="noopener">Abrir a prova</a></p>`;
    return path ? `<p class="aside">A prova não está nesta máquina: <code>${esc(path)}</code></p>` : '';
  }
  function rigEntry(rig) {
    if (!rig) return '';
    const tag = rig.status === 'proposed' ? '<span class="tag warn">Proposta</span>' : '<span class="tag">Aprovada</span>';
    const approval = rig.approval ? `<p class="approval">Aprovação do operador em ${esc(day(rig.approval.date))}: “${esc(rig.approval.words)}”</p>` : '';
    return `<div class="rig"><h4>Rig da cabeça</h4><div class="tags">${tag}</div><small>${esc(day(rig.date))}</small>` +
      `<p>${esc(rig.note)}</p>${approval}${proofLink(rig.proof, rig.proof_path)}</div>`;
  }
  function versionEntry(p, v, at) {
    const drawing = v.part ? parts.get(v.part) : null;
    let picture = '';
    if (p.versions.length > 1) { // with one version the picture is the one at the top of the page
      if (drawing && drawing.specimen) picture = `<div class="stills">${figure(drawing.specimen, `${p.title}, versão ${v.number}`, false)}</div>`;
      else picture = `<p class="notice">${esc(drawing ? drawing.refused : 'Ainda sem desenho registrado.')}</p>`;
    }
    const tags = [v.status === 'proposed' ? '<span class="tag warn">Proposta</span>' : '<span class="tag">Aprovada</span>'];
    if (v.default) tags.push('<span class="tag default">Padrão para novos reels</span>');
    const approval = v.approval ? `<p class="approval">Aprovação do operador em ${esc(day(v.approval.date))}: “${esc(v.approval.words)}”</p>` : '';
    const proof = proofLink(v.proof, v.proof_path);
    return `<section class="version${picture ? ' pictured' : ''}${v.number === at ? ' current' : ''}" data-version="${v.number}">${picture}` +
      `<div class="version-facts"><h3>Versão ${v.number}</h3><div class="tags">${tags.join('')}</div>` +
      `<small>${esc(day(v.date))}</small><p>${esc(v.note)}</p>${approval}${proof}${rigEntry(v.rig)}${versionPins(v)}</div></section>`;
  }
  function viewPart(kind, name) {
    const found = parts.get(name);
    const k = KINDS[kind];
    if (!found || found.kind !== kind) return missing(`${k.one} ${name}`);
    const p = found.version_of ? parts.get(found.version_of) : found; // a later version opens its character's history
    const at = found.version_of ? p.versions.find(v => v.part === found.name).number : 0;
    const shots = drawingsOf(p).flatMap(d => d.gallery);
    const gallery = (shots.length ? '<div class="sub">Visto em</div>' : '') + shots.map(g =>
      `<div class="stills lead">${figure(g.still, g.name, true)}</div>` +
      (g.voice ? `<p>voz ${esc(g.voice)} (ElevenLabs)</p>` : '') + `<p class="note">${g.note_html}${copyButton(plainText(g.note_html), 'nota')}</p>` +
      (g.poses.length ? `<div class="stills">${g.poses.map(s => figure(s, `${g.name}, ${s.label}`, false)).join('')}</div>` : '')).join('');
    const sheet = p.sheet.length
      ? `<div class="sub">Folha de poses</div><div class="stills" id="pose-sheet">${p.sheet.map(s => figure(s, `${p.title}, pose ${s.label}`, false)).join('')}</div>`
      : '';
    const drawn = defaultDrawing(p);
    const specimen = drawn.specimen
      ? `<div class="stills lead" id="specimen">${figure(drawn.specimen, p.title, false)}</div>`
      : `<p class="notice" id="refused">Sem desenho isolado. ${esc(drawn.refused)}</p>`;
    const history = hasHistory(p)
      ? `<div class="sub">Versões</div><div id="versions">${p.versions.map(v => versionEntry(p, v, at)).join('')}</div>` : '';
    const seen = videosOf(p);
    let used;
    if (!C.measured) used = '<p class="notice">Uso não medido: o catálogo foi gerado sem o relatório de <code>srstudio usage</code>.</p>';
    else if (!seen.length) used = `<p class="notice" id="unused">Não usado: nenhum episódio medido chama esta peça.</p>${unmeasuredNote()}`;
    else used = grid(seen.map(slug => videoCard(videos.get(slug))), 'part-videos') + unmeasuredNote();
    const voices = shots.map(g => g.voice).filter(Boolean);
    const sheetFacts = ficha([
      ['Tipo', k.one], ['Estilo', styleLink(p.style) || 'Compartilhada'], ['Nome', named(p.name)],
      ['Versões', p.versions.length > 1 ? String(p.versions.length) : ''],
      ['Aparece em', C.measured ? videoCount(seen.length) : 'não medido'],
      ['Voz', esc([...new Set(voices)].join(', '))],
    ]);
    return {
      title: p.title,
      html: `<article class="detail" data-part="${esc(p.name)}">${crumbs(`#/${k.route}`, k.label, p.title)}` +
        `<div class="view-head"><h2>${esc(p.title)}${copyButton(p.title, 'título')}</h2><div class="tags">${styleTag(p.style)}</div>` +
        `<p class="lede">${esc(p.summary)}${copyButton(p.summary, 'descrição')}</p></div><div class="detail-grid part"><div class="part-main">${specimen}${history}${gallery}${sheet}</div>` +
        `<aside class="side">${sheetFacts}</aside></div>` +
        `<div class="sub">Vídeos com esta peça</div>${used}</article>`,
    };
  }
  function viewStyle(slug, params) {
    const s = styles.get(slug);
    if (!s) return missing(`O estilo ${slug}`);
    const tab = params.get('aba') || '';
    const ownOf = kind => s.parts.map(n => parts.get(n)).filter(p => p.kind === kind && !p.version_of);
    const link = (value, label, n) =>
      `<a href="${styleHref(s)}${query(new URLSearchParams(), {aba: value})}" aria-current="${tab === value}">${esc(label)}<small>${n}</small></a>`;
    const tabs = [link('', 'Vídeos', s.videos.length)];
    Object.values(KINDS).forEach(k => {
      const n = ownOf(KIND_OF_ROUTE[k.route]).length;
      if (n) tabs.push(link(k.route, k.label, n));
    });
    const body = KIND_OF_ROUTE[tab]
      ? grid(ownOf(KIND_OF_ROUTE[tab]).map(partCard), 'style-parts')
      : grid(s.videos.map(v => videoCard(videos.get(v))), 'style-videos');
    return {
      title: s.name,
      html: `<article class="detail" data-style="${esc(s.slug)}">${crumbs('#/estilos', 'Estilos', s.name)}<div class="view-head">` +
        `<h2>${esc(s.name)}${copyButton(s.name, 'nome')}</h2><b>${esc(s.title)}</b>` +
        `<p class="lede">${s.text_html}${copyButton(plainText(s.text_html), 'descrição')}</p>` +
        (s.text_html === esc(s.summary) ? '' : `<p class="aside">${esc(s.summary)}</p>`) + '</div>' +
        `<nav class="tabs" aria-label="Conteúdo do estilo">${tabs.join('')}</nav>${body}</article>`,
    };
  }

  // -- the registry and the usage lists -------------------------------------------------------------------
  function viewRegistry() {
    const rows = [...C.parts].sort((a, b) => a.name < b.name ? -1 : 1).map(p =>
      `<tr><td><a href="${partHref(p)}"><code>${esc(p.name)}</code></a>${copyButton(p.name, 'nome')}</td>` +
      `<td>${esc(styles.has(p.style) ? styles.get(p.style).name : 'todos')}</td><td>${KINDS[p.kind].one}</td>` +
      `<td>${esc(p.summary)}</td><td class="num">${p.videos.length}</td></tr>`).join('');
    const blocks = Object.entries(KINDS).map(([kind, k]) => {
      const all = C.parts.filter(p => p.kind === kind);
      const used = all.filter(p => p.videos.length);
      const unused = all.filter(p => !p.videos.length);
      const item = p => `<li><a href="${partHref(p)}"><code>${esc(p.name)}</code></a>${copyButton(p.name, 'nome')} <small>${esc(p.summary)}</small></li>`;
      return `<div class="lib-usage-kind" id="usage-${kind}"><h3>${k.label}</h3>` +
        `<p><b>${used.length}</b> usados · <b>${unused.length}</b> não usados</p><ul>` +
        used.map(p => `<li><a href="${partHref(p)}"><code>${esc(p.name)}</code></a>${copyButton(p.name, 'nome')} <small>${esc(p.videos.join(', '))}</small></li>`).join('') +
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
        `<th class="num">Vídeos</th></tr></thead><tbody>${rows}</tbody></table></div>${usage}`,
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
      found[k.label] = listed(kind).filter(p => hit(drawingsOf(p).flatMap(d => [d.title, d.name, ...d.gallery.map(g => g.name)]))).map(partCard);
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

  function styleRow(s) {
    const v = s.videos.map(slug => videos.get(slug)).find(x => x.poster);
    const count = kind => s.parts.filter(n => parts.get(n).kind === kind && !parts.get(n).version_of).length;
    const cell = (route, n) => `<td class="num"><a href="#/${route}?estilo=${esc(s.slug)}">${n || '—'}</a></td>`;
    const time = s.videos.reduce((t, slug) => t + videos.get(slug).duration, 0);
    return `<tr>${v ? thumb(v.poster, s.name, v.width, v.height) : thumb()}` +
      `<td><a href="${styleHref(s)}"><b>${esc(s.name)}</b></a>${s.title === s.name ? '' : `<small>${esc(s.title)}</small>`}</td>` +
      cell('videos', s.videos.length) + Object.entries(KINDS).map(([kind, k]) => cell(k.route, count(kind))).join('') +
      `<td class="num">${minutes(time)}</td></tr>`;
  }
  function usageBar([kind, k]) {
    const all = listed(kind);
    const used = all.filter(p => videosOf(p).length).length;
    const share = all.length ? Math.round(100 * used / all.length) : 0;
    return `<div class="usage-bar"><a href="#/${k.route}">${k.label}</a><span class="usage-n">${used} de ${all.length}</span>` +
      `<div class="bar" role="img" aria-label="${used} de ${all.length} ${k.label} usados"><i style="width:${share}%"></i></div>` +
      (used < all.length ? `<a class="usage-gap" href="#/${k.route}?uso=nao">${all.length - used} sem uso</a>` : '') + '</div>';
  }
  function attention() {
    const noRender = C.videos.filter(v => v.source === 'no-render');
    const refused = C.parts.filter(p => p.refused);
    const line = (label, items) => (items.length
      ? `<details><summary>${esc(label)} <b>${items.length}</b></summary><div class="pills">${items.join('')}</div></details>` : '');
    const body = [
      line('Vídeos sem render', noRender.map(v => `<a href="${videoHref(v)}">${esc(v.slug)}</a>`)),
      line('Vídeos não medidos', C.unmeasured.map(slug => `<a href="#/videos/${slugLink(slug)}">${esc(slug)}</a>`)),
      line('Peças sem desenho isolado', refused.map(p => `<a href="${partHref(p)}">${esc(p.name)}</a>`)),
    ].join('');
    return body ? `<section class="panel"><h3>Pendências</h3>${body}</section>` : '';
  }
  function viewHome() {
    const total = C.videos.reduce((t, v) => t + v.duration, 0);
    const used = C.parts.filter(p => p.videos.length).length;
    const tiles = [
      ['#/videos', C.videos.length, 'Vídeos'], ['#/videos?ordem=duracao', minutes(total), 'De vídeo'],
      ['#/estilos', C.styles.length, 'Estilos'], ['#/registro', C.parts.length, 'Peças registradas'],
      ['#/registro', `${Math.round(100 * used / C.parts.length)} %`, 'Peças em uso'],
    ];
    const heads = [{}, {label: 'Estilo'}, {label: 'Vídeos', num: true},
      ...Object.values(KINDS).map(k => ({label: k.label, num: true})), {label: 'Duração', num: true}];
    const specs = document.querySelector('.hero .specs');
    return {
      title: '',
      html: head('Visão geral', '') +
        `<div class="tiles-nav">${tiles.map(([href, n, label]) => `<a href="${href}"><b>${n}</b><span>${label}</span></a>`).join('')}</div>` +
        `<div class="home-grid"><section class="panel style-table"><h3>Estilos</h3>${table(heads, C.styles.map(styleRow))}</section>` +
        `<div class="home-side"><section class="panel"><h3>Uso da biblioteca</h3>${Object.entries(KINDS).map(usageBar).join('')}</section>${attention()}</div></div>` +
        (specs ? `<section class="panel"><h3>Especificações</h3>${specs.outerHTML}</section>` : ''),
    };
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
    if (section === 'estilos') return viewStyles(id, params);
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
  function countSections() {
    const count = {'#/estilos': C.styles.length, '#/videos': C.videos.length, '#/registro': C.parts.length,
      '#/pacotes': C.videos.filter(v => v.source === 'package').length, '#/motor': C.engine.length};
    Object.entries(KINDS).forEach(([kind, k]) => { count[`#/${k.route}`] = listed(kind).length; });
    document.querySelectorAll('.nav-links a').forEach(a => {
      const n = count[a.getAttribute('href')];
      if (n !== undefined) a.dataset.count = n;
    });
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
    const target = route.section === 'pacotes' && route.id ? document.getElementById(`ep-${route.id}`) : app.querySelector('.version.current');
    if (target) target.scrollIntoView();
    else window.scrollTo(0, fresh ? 0 : scrolled.get(location.hash) || 0);
    fresh = false;
  }

  document.addEventListener('click', event => {
    if (event.target.closest && event.target.closest('a[href^="#/"]')) fresh = true;
  });

  // The clipboard API needs a secure context, which loopback is and a forwarded plain http host may not be. The older
  // command works anywhere a click does; when it too refuses, the page says so rather than seeming to have copied.
  async function writeClipboard(text) {
    if (navigator.clipboard) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        // refused by the browser: the older command below may still work
      }
    }
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const done = document.execCommand('copy');
    area.remove();
    return done;
  }
  const notice = document.createElement('div');
  notice.id = 'copied';
  notice.setAttribute('role', 'status');
  notice.hidden = true;
  document.body.appendChild(notice);
  let hideNotice = 0;
  app.addEventListener('click', async event => {
    const button = event.target.closest('.copy');
    if (!button) return;
    const done = await writeClipboard(button.dataset.copy);
    button.focus();
    button.classList.toggle('done', done);
    notice.textContent = done ? 'Copiado.' : 'Não foi possível copiar.';
    notice.hidden = false;
    clearTimeout(hideNotice);
    hideNotice = setTimeout(() => {
      notice.hidden = true;
      button.classList.remove('done');
    }, 1800);
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

  app.addEventListener('change', event => {
    if (event.target.id === 'sort') location.hash = event.target.value;
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
      countSections();
      render();
      afterRender();
    })
    .catch(err => fail(`Não foi possível ler o catálogo (${err.message}). Abra o site com srstudio serve.`));
})();
