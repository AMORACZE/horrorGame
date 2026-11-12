shader_type spatial;
// A thin running-water stream (cylinder mesh along Y). Streaks scroll down,
// the edges thin out, and it picks up a little of the room's light.
render_mode blend_mix, cull_disabled, depth_draw_opaque, shadows_disabled;

uniform vec4 water_color : source_color = vec4(0.82, 0.88, 0.9, 0.55);
uniform float speed = 2.6;
uniform float streaks = 14.0;
uniform float wobble = 0.0006;

void vertex() {
	float w = sin(UV.y * 40.0 - TIME * 30.0) * wobble;
	VERTEX.x += w;
	VERTEX.z += w * 0.6;
}

void fragment() {
	float s = sin(UV.x * 6.2831 * 3.0 + (UV.y * streaks + TIME * speed) * 6.2831);
	float s2 = sin(UV.x * 6.2831 * 5.0 - (UV.y * streaks * 0.7 + TIME * speed * 1.3) * 6.2831);
	float k = 0.5 + 0.25 * s + 0.25 * s2;
	float fres = pow(1.0 - abs(dot(NORMAL, VIEW)), 2.0);
	ALBEDO = water_color.rgb * (0.85 + 0.3 * k);
	ROUGHNESS = 0.08;
	SPECULAR = 0.9;
	ALPHA = clamp(water_color.a * (0.6 + 0.6 * fres) * (0.75 + 0.25 * k), 0.0, 1.0);
}
