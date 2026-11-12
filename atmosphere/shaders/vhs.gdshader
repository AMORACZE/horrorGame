shader_type canvas_item;
render_mode unshaded;

// Consumer VHS record/playback, approximated in one pass over the finished frame.
//
// Signal model (NTSC-ish, SP speed, a tired deck):
//   * luma bandwidth ~3 MHz  -> soft horizontally, a little edge enhancement halo
//   * chroma bandwidth ~0.5 MHz, colour-under -> smeared ~6x wider than luma,
//     delayed (shifted right), averaged with the line above, noisy
//   * tape noise is mostly in luma, streaky along the line, worst in the shadows
//   * time-base error: lines wander left/right a fraction of a pixel
//   * head switching: the last few lines of the field are torn sideways
//   * dropouts: rare short white streaks where oxide is missing
//   * the deck/camera clamp blacks a little high and roll highlights off
// Every term is scaled by `intensity` (0 = pass-through, 1 = shipped look).

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap, repeat_disable;

uniform float intensity : hint_range(0.0, 1.5) = 1.0;
// Driven by post_fx.gd: autofocus hunt blur (0 sharp .. 1 badly out of focus).
uniform float focus_blur : hint_range(0.0, 1.0) = 0.0;
// Driven by post_fx.gd: zoom position (0 wide .. 1 tele). Tele adds gain noise.
uniform float tele : hint_range(0.0, 1.0) = 0.0;

group_uniforms tuning;
// Horizontal luma blur, sigma as a fraction of screen width.
uniform float luma_sigma : hint_range(0.0, 0.005, 0.0001) = 0.0009;
// Horizontal chroma blur, sigma as a fraction of screen width.
uniform float chroma_sigma : hint_range(0.0, 0.02, 0.0005) = 0.005;
// Chroma delay to the right, fraction of screen width.
uniform float chroma_shift : hint_range(0.0, 0.01, 0.0001) = 0.0022;
// Playback "sharpness" halo.
uniform float halo : hint_range(0.0, 2.0, 0.01) = 0.45;
uniform float luma_noise : hint_range(0.0, 0.2, 0.001) = 0.045;
uniform float chroma_noise : hint_range(0.0, 0.2, 0.001) = 0.022;
// Lateral line wander, fraction of screen width.
uniform float wobble : hint_range(0.0, 0.004, 0.0001) = 0.00045;
uniform float scanline : hint_range(0.0, 0.2, 0.005) = 0.03;
uniform float head_switch_height : hint_range(0.0, 0.05, 0.001) = 0.011;
// Chance per frame of a dropout streak.
uniform float dropout_rate : hint_range(0.0, 0.2, 0.001) = 0.003;
uniform float black_lift : hint_range(0.0, 0.2, 0.001) = 0.045;
uniform float highlight_knee : hint_range(0.5, 1.0, 0.01) = 0.78;
uniform float saturation : hint_range(0.0, 1.5, 0.01) = 0.9;
uniform vec3 color_cast : source_color = vec3(1.0, 0.985, 0.95);
uniform float vignette : hint_range(0.0, 1.0, 0.01) = 0.22;
group_uniforms;

const mat3 RGB2YIQ = mat3(
	vec3(0.299, 0.596, 0.211),
	vec3(0.587, -0.274, -0.523),
	vec3(0.114, -0.322, 0.312));
const mat3 YIQ2RGB = mat3(
	vec3(1.0, 1.0, 1.0),
	vec3(0.956, -0.272, -1.106),
	vec3(0.621, -0.647, 1.703));

float hash12(vec2 p) {
	vec3 p3 = fract(vec3(p.xyx) * 0.1031);
	p3 += dot(p3, p3.yzx + 33.33);
	return fract((p3.x + p3.y) * p3.z);
}

// Value noise along a line: smooth in x, independent per (row, frame).
float line_noise(float x, float row, float frame) {
	float i = floor(x);
	float f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	float a = hash12(vec2(i, row + frame * 17.0));
	float b = hash12(vec2(i + 1.0, row + frame * 17.0));
	return mix(a, b, f) - 0.5;
}

vec3 sample_rgb(vec2 uv, float lod) {
	return textureLod(screen_tex, clamp(uv, vec2(0.0005), vec2(0.9995)), lod).rgb;
}

void fragment() {
	float k = intensity;
	vec2 uv = SCREEN_UV;
	vec2 px = SCREEN_PIXEL_SIZE;
	float screen_h = 1.0 / px.y;
	float aspect = px.y / px.x;

	// Field structure locked to whole output pixels so it never moires.
	float line_px = max(1.0, floor(screen_h / 360.0 + 0.5));
	float row = floor(FRAGCOORD.y / line_px);
	float frame = mod(floor(TIME * 29.97), 4096.0);
	float noise_gain = (1.0 + 0.8 * tele) * k;

	// --- Time-base error (gentle) and head switching (bottom of frame) ------
	float slow = sin(uv.y * 6.0 + TIME * 0.9) * 0.6 + sin(uv.y * 21.0 - TIME * 1.7) * 0.4;
	float jitter = hash12(vec2(row, frame)) - 0.5;
	float dx = (slow * 0.75 + jitter * 0.5) * wobble * k;

	float hs = smoothstep(1.0 - head_switch_height, 1.0, uv.y) * step(0.001, head_switch_height);
	float hs_tear = hs * (0.018 + 0.03 * hash12(vec2(frame, 3.7)) + 0.012 * jitter);
	dx += hs_tear * k;
	uv.x -= dx;

	// --- Lens / autofocus ---------------------------------------------------
	float lod = focus_blur * 3.2;

	// --- Luma: soft, with a playback sharpening halo ------------------------
	float ls = luma_sigma * k * (1.0 + focus_blur * 2.0) + 1e-6;
	float y_gauss = 0.0;
	float y_wide = 0.0;
	float wsum = 0.0;
	vec3 centre_rgb = vec3(0.0);
	for (int i = -3; i <= 3; i++) {
		float o = float(i);
		vec3 c = sample_rgb(vec2(uv.x + o * ls * 0.85, uv.y), lod);
		float y = dot(c, vec3(0.299, 0.587, 0.114));
		float w = exp(-0.5 * o * o * 0.72);
		y_gauss += y * w;
		wsum += w;
		y_wide += y;
		if (i == 0) {
			centre_rgb = c;
		}
	}
	y_gauss /= wsum;
	y_wide /= 7.0;
	float luma = y_gauss + (y_gauss - y_wide) * halo * k;

	// --- Chroma: wide, late, averaged with the previous line ----------------
	float cs = chroma_sigma * k + 1e-6;
	vec2 iq = vec2(0.0);
	float csum = 0.0;
	float line_h = line_px * px.y;
	for (int i = 0; i < 6; i++) {
		float o = (float(i) - 2.5) / 2.5 * 2.2;  // -2.2 .. +2.2 sigma
		float vy = (i % 2 == 0) ? 0.0 : line_h;
		vec3 c = sample_rgb(vec2(uv.x - chroma_shift * k + o * cs, uv.y - vy), lod + 0.5);
		vec3 yiq = RGB2YIQ * c;
		float w = exp(-0.5 * o * o);
		iq += yiq.yz * w;
		csum += w;
	}
	iq /= csum;
	// Without any VHS, keep the original chroma exactly.
	vec2 iq_orig = (RGB2YIQ * centre_rgb).yz;
	iq = mix(iq_orig, iq, clamp(k * 2.0, 0.0, 1.0));

	// --- Tape noise ---------------------------------------------------------
	float shadow = 1.0 - clamp(luma, 0.0, 1.0);
	float grain_w = 2.2 * line_px;  // noise specks are a few pixels long
	float g = line_noise(FRAGCOORD.x / grain_w, row, frame) * 0.75
			+ (hash12(vec2(FRAGCOORD.x, row + frame * 31.0)) - 0.5) * 0.35;
	luma += g * luma_noise * noise_gain * (0.25 + 0.75 * shadow * shadow);

	float cw = 14.0 * line_px;
	vec2 cn = vec2(line_noise(FRAGCOORD.x / cw, row, frame + 101.0),
			line_noise(FRAGCOORD.x / cw + 37.0, row, frame + 211.0));
	iq += cn * chroma_noise * noise_gain * (0.35 + 0.65 * shadow);

	// Head switching band: noisy, chroma-less.
	luma += (hash12(vec2(FRAGCOORD.x * 0.5, row + frame)) - 0.5) * 0.25 * hs * k;
	iq *= 1.0 - hs * 0.8 * k;

	// Dropouts: rare, one frame long, 1-2 lines tall, bright with a dark tail.
	float d_roll = hash12(vec2(frame, 91.3));
	if (d_roll < dropout_rate * k) {
		float d_row = floor(hash12(vec2(frame, 7.1)) * screen_h / line_px);
		float d_x0 = hash12(vec2(frame, 1.9));
		float d_len = 0.02 + 0.14 * hash12(vec2(frame, 4.4));
		float in_row = step(abs(row - d_row), 0.5 + step(0.6, hash12(vec2(frame, 8.8))));
		float t = (uv.x - d_x0) / d_len;
		float in_x = step(0.0, t) * step(t, 1.0);
		float streak = in_row * in_x * (1.0 - t * 0.6);
		luma = mix(luma, 0.92 + 0.08 * hash12(vec2(FRAGCOORD.x, frame)), streak * 0.85);
		iq *= 1.0 - streak;
	}

	// --- Back to RGB, then the camcorder's tone curve -----------------------
	vec3 rgb = YIQ2RGB * vec3(luma, iq * mix(1.0, saturation, k));

	// Field/scanline structure: very faint.
	float lf = fract(FRAGCOORD.y / line_px);
	rgb *= 1.0 - scanline * k * step(1.5, line_px) * smoothstep(0.35, 1.0, lf);

	// Highlights roll off softly; blacks sit a little above zero.
	vec3 over = max(rgb - highlight_knee, 0.0);
	float range = 1.0 - highlight_knee;
	vec3 knee = highlight_knee + range * (1.0 - exp(-over / max(range, 1e-3))) * 0.92;
	rgb = mix(rgb, mix(rgb, knee, step(highlight_knee, rgb)), k);
	rgb = rgb * (1.0 - black_lift * k) + black_lift * k;

	// Slight cast, a touch cooler and magenta in the shadows.
	float lum = dot(rgb, vec3(0.299, 0.587, 0.114));
	vec3 cast = mix(vec3(1.0), color_cast, k);
	rgb *= cast;
	rgb += vec3(0.006, -0.002, 0.012) * (1.0 - lum) * (1.0 - lum) * k;

	// Lens vignette.
	vec2 vc = (SCREEN_UV - 0.5) * vec2(aspect * 0.75, 1.0);
	float v = 1.0 - vignette * k * smoothstep(0.25, 0.95, length(vc) * 1.1);
	rgb *= v;

	COLOR = vec4(clamp(rgb, 0.0, 1.0), 1.0);
}
