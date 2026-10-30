"""What the catalog tests share: a base page, an episode project, a gallery and a usage report."""

import json
from pathlib import Path

from srstudio import catalog_page as cp

SCENE = """<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="{w}" height="{h}" fps="{fps}" duration="{dur}" seed="1" background="#000000"/>
  <metadata title="{title}" description="{desc}" generator="test"/>
</scene>
"""

SCENES = json.dumps(
    [
        {"id": "honesty-interview", "title": "Honesty", "description": "The first.", "width": 1080, "height": 1920,
         "fps": 30, "duration": 10.9},
        {"id": "printer-recreation", "title": "The Printer", "description": "Ink.", "width": 1080, "height": 1080,
         "fps": 24, "duration": 42.0},
    ]
)  # fmt: skip

BASE = (
    """<!doctype html>
<html lang="pt-BR"><head><style>
.a{ color:red }
</style>
</head><body>
<div class="wrap">
<header class="hero">
<div>
<div class="eyebrow">scene-render · sr-core · srstudio · AudioForge · 6 pacotes .vpkg</div>
<p class="lede">Seis curtas reconstruídos, com <b>Cutout</b> e <b>Ink</b>.</p>
<div class="styles">
        <div class="style-card"><span class="style-tag cutout">Cutout</span><b>Recorte</b></div>
        <div class="style-card"><span class="style-tag ink">Ink</span><b>Traço</b></div>
      </div>
    </div>
    <div class="specs" aria-label="Especificações comuns">
      <div class="spec"><b>95,7 s</b><span>6 episódios</span></div>
    </div>
</header>
<section id="episodios"><div class="eyebrow">Parte 1</div></section>
<section id="elenco"><div class="eyebrow">Parte 2</div>
<p class="lede">Tudo que aparece nos seis vídeos, recortado do próprio desenho.</p>
  <div class="cast" id="cast"></div>
</section>
<section id="motor"><div class="eyebrow">Parte 4</div></section>
<footer>
  <p>Fontes: os seis pacotes.</p>
</footer>
</div>

<script id="scenes-data" type="application/json">"""
    + SCENES
    + """</script>
<script>
(function(){
'use strict';
const AUDIO_SRC = {};
const EP = {
 'honesty-interview':{no:'01', pt:'Honestidade', desc:'A primeira entrevista.',
   hl:['x']},
 'printer-recreation':{no:'06', pt:'A impressora', desc:'O estilo d\\'Ink.',
   hl:['y']},
};
const ENGINE = [
 {h:'Animação e tempo', items:['42 curvas']},
 {h:'Simulação física', items:['Corpos']},
];
})();
</script>

</body>
</html>
"""
)


def write_project(root: Path, slug: str, *, kind: str = "dialogue", w=1080, h=1920, fps=30, dur=4.0) -> Path:
    p = root / slug
    p.mkdir(parents=True)
    (p / f"{slug}.scene.xml").write_text(
        SCENE.format(w=w, h=h, fps=fps, dur=dur, title=f"{slug} title", desc=f"About {slug} &amp; more")
    )
    (p / f"{slug}.audio.scene.xml").write_text("<scene/>")  # the audio document is not the episode
    if kind == "dialogue":
        data = {
            "phrases": [
                {"role": "pip", "voice_name": "Will", "text": "Second line.", "start": 2.0},
                {"role": "boss", "voice_name": "Eric", "text": "First line.", "start": 0.5},
            ],
            "sound_effects": [{"name": "call-chime", "start": 1.0, "duration": 0.5}],
        }
    elif kind == "timeline":
        data = {
            "items": [
                {"actor": "human", "voice_name": "Chris", "text": "Load!", "start": 0.0},
                {"actor": "sfx", "text": "[BEEP]", "start": 1.0},
            ]
        }
    else:
        data = {"items": [{"text": "This module will take forty-five minutes.", "start": 0.08}]}
    (p / f"{kind if kind != 'narration' else 'narration'}.json").write_text(json.dumps(data))
    return p


def shot(episode="camera-off", at=1.0, box=None):
    return {"episode": episode, "at": at, **({"box": box} if box else {})}


GALLERY = [  # covers every part the tree's three episodes are registered with
    {"section": "cast", "name": "Pip", "parts": ["pip"], "voice": "Will", "text": "O <i>blob</i>.",
     "shot": shot(box=[0, 0, 300, 400]), "poses": [{"label": "dança", "shot": shot(at=2.0, box=[0, 0, 200, 200])}]},
    {"section": "cast", "name": "O roteador", "parts": ["talking-router", "ink-hand"], "text": "Fala.",
     "shot": shot("the-router")},
    {"section": "locations", "name": "Escritório & casa", "parts": ["soft-office"], "text": "Mesa.", "shot": shot()},
    {"section": "locations", "name": "Prateleira", "parts": ["ink-router-shot", "ink-router-wide"], "text": "Muro.",
     "shot": shot("the-router", 0.5)},
    {"section": "cast", "name": "Cogumelo", "parts": ["cel-traced"], "text": "Traçado.",
     "shot": shot("mushroom-training")},
    {"section": "locations", "name": "Sala", "parts": ["cel-room"], "text": "Piso.", "shot": shot("mushroom-training")},
    {"section": "graphics", "name": "Letreiro", "parts": ["cel-lettering"], "text": "Caixa.",
     "shot": shot("mushroom-training", 0.2, [0, 0, 1080, 300])},
]  # fmt: skip


def item(**changes):
    return {**GALLERY[0], **changes}


USAGE = cp.Report(
    {
        "camera-off": ("pip", "soft-office", "soft-desk"),
        "the-router": ("talking-router", "ink-hand", "ink-router-shot", "ink-router-wide"),
        "mushroom-training": ("cel-traced", "cel-room", "cel-lettering"),
        "honesty-interview": ("manager", "office-wide"),  # a package episode: no card, not in the gallery
    }
)
