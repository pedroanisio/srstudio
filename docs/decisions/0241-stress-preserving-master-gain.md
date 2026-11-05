# 0241 — Stress-preserving master gain

An emphasized take can pass the word stress bar and lose it on the master.
The news-ai-hostage button measured 3.49593166972576 dB on the clip,
3.49605693528634 dB on the unmastered engine mix, and 2.5461492909116963 dB
on the delivered master. The authored integrated gain reaches the true-peak
limiter; its time-varying attenuation reduces the stressed word's contrast.
Word placement and the unmastered mix preserve that contrast.

For `master.encode` projects with recorded named stress and integrated
normalization, run an audio-only engine analysis with normalization and
limiting disabled. Keep the authored tracks, effects, fader and programme
selection. Read the engine's full-precision integrated LUFS and true peak.
Cap the requested integrated target at:

    unmastered LUFS + declared true-peak ceiling - unmastered true peak

This bounds constant master gain by the available peak headroom. Keep the
limiter as a ceiling guard. The engine's limiter has a small internal safety
factor; no extra word margin is added. `emphasis.lean`, its existing margin,
and `emphasis.MOST` remain unchanged. A sufficiently quiet requested target
keeps its authored value. Report any reduction in the encode result.

Use a temporary sibling scene so relative asset and report paths retain their
meaning; never rewrite the source. Analysis audio stays outside the install
stage. Analysis failure refuses the encode. Program range, data, representation,
parameters and thread arguments pass through to analysis. Analysis never uploads.

This policy trades integrated loudness for preserved dynamics; the craft bar
specifies no integrated loudness target. It applies to the SDK master path,
not direct engine calls, dynamic normalization, or unrecorded projects. It
cannot repair contrast already lost to overlapping tracks, authored effects,
or a take that fails stress. Cached timing still must match the source.
Lossy encoding can perturb word levels; proof on the delivered mix remains
necessary, especially when a take only barely passes.

Synthetic integration tests reproduce limiter loss and check both peak-limited
and unconstrained gain through PCM and AAC outputs, source preservation and
scratch cleanup. The real project is rebuilt only from a scratch copy.
