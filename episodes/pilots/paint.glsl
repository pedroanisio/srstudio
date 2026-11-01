// The paint-over of pedro_drive_3d.py, over the picture of the engine's 3D pass: a Kuwahara filter flattens each
// surface to a brush-sized patch, the light is cut into bands that keep each hue (cool in the shade, warm in the light),
// and ink follows the edges. The picture is 1080 x 1920.
uniform float tx; // = 0.000926
uniform float ty; // = 0.000520
uniform float radius; // = 3.0
uniform float bands; // = 5.0
uniform float soft; // = 0.16
uniform float ink; // = 1.0
uniform float inkWidth; // = 1.2
uniform float inkLow; // = 0.14
uniform float inkHigh; // = 0.36

float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

vec4 effect(vec2 uv) {
    vec2 px = vec2(tx, ty);
    vec3 mean[4];
    float var[4];
    for (int k = 0; k < 4; k++) { mean[k] = vec3(0.0); var[k] = 0.0; }
    float n = (radius + 1.0) * (radius + 1.0);
    for (int j = 0; j <= 6; j++) {
        for (int i = 0; i <= 6; i++) {
            if (float(i) > radius || float(j) > radius) continue;
            vec2 o = vec2(float(i), float(j));
            vec3 c0 = getColor(uv + vec2(-o.x, -o.y) * px).rgb;
            vec3 c1 = getColor(uv + vec2( o.x, -o.y) * px).rgb;
            vec3 c2 = getColor(uv + vec2(-o.x,  o.y) * px).rgb;
            vec3 c3 = getColor(uv + vec2( o.x,  o.y) * px).rgb;
            mean[0] += c0; var[0] += luma(c0) * luma(c0);
            mean[1] += c1; var[1] += luma(c1) * luma(c1);
            mean[2] += c2; var[2] += luma(c2) * luma(c2);
            mean[3] += c3; var[3] += luma(c3) * luma(c3);
        }
    }
    vec3 best = vec3(0.0);
    float low = 1e9;
    for (int k = 0; k < 4; k++) {
        vec3 m = mean[k] / n;
        float v = var[k] / n - luma(m) * luma(m);
        if (v < low) { low = v; best = m; }
    }
    vec4 src = getColor(uv);
    float l = luma(best);
    // bands with a painted edge: each step rises over the last `soft` of its band
    float x = l * bands;
    float level = (floor(x) + smoothstep(1.0 - soft, 1.0, fract(x)) + 0.5) / bands;
    vec3 col = best * (level + 0.03) / max(l, 0.03);
    // cool in the shade, warm in the light
    float warm = smoothstep(0.25, 0.8, level);
    col *= mix(vec3(0.88, 0.93, 1.10), vec3(1.08, 1.0, 0.9), warm);
    // ink along the edges of the picture
    float w = inkWidth;
    float tl = luma(getColor(uv + vec2(-w, -w) * px).rgb), t = luma(getColor(uv + vec2(0.0, -w) * px).rgb);
    float tr = luma(getColor(uv + vec2(w, -w) * px).rgb), le = luma(getColor(uv + vec2(-w, 0.0) * px).rgb);
    float ri = luma(getColor(uv + vec2(w, 0.0) * px).rgb), bl = luma(getColor(uv + vec2(-w, w) * px).rgb);
    float b = luma(getColor(uv + vec2(0.0, w) * px).rgb), br = luma(getColor(uv + vec2(w, w) * px).rgb);
    float gx = -tl - 2.0 * le - bl + tr + 2.0 * ri + br;
    float gy = -tl - 2.0 * t - tr + bl + 2.0 * b + br;
    float edge = smoothstep(inkLow, inkHigh, sqrt(gx * gx + gy * gy));
    col = mix(col, vec3(0.035, 0.03, 0.07), edge * ink);
    return vec4(col, src.a);
}
