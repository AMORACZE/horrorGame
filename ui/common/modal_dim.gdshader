shader_type canvas_item;
// Softens and darkens whatever is already on screen behind a modal view.
// Blur is a small tap pattern over a mip level of the screen copy: cheap and
// soft enough that the room stays legible as a place but stops competing.

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float amount : hint_range(0.0, 1.0) = 1.0;
uniform vec4 tint : source_color = vec4(0.03, 0.028, 0.025, 0.62);
uniform float blur_lod : hint_range(0.0, 6.0) = 2.5;
uniform float blur_radius : hint_range(0.0, 8.0) = 3.0;
uniform float vignette : hint_range(0.0, 1.0) = 0.35;
uniform float desaturate : hint_range(0.0, 1.0) = 0.35;

void fragment() {
	float lod = blur_lod * amount;
	vec2 px = SCREEN_PIXEL_SIZE * blur_radius * exp2(lod) * amount;
	vec3 c = textureLod(screen_tex, SCREEN_UV, lod).rgb * 0.2;
	c += textureLod(screen_tex, SCREEN_UV + vec2( px.x, 0.0), lod).rgb * 0.1;
	c += textureLod(screen_tex, SCREEN_UV + vec2(-px.x, 0.0), lod).rgb * 0.1;
	c += textureLod(screen_tex, SCREEN_UV + vec2(0.0,  px.y), lod).rgb * 0.1;
	c += textureLod(screen_tex, SCREEN_UV + vec2(0.0, -px.y), lod).rgb * 0.1;
	c += textureLod(screen_tex, SCREEN_UV + px, lod).rgb * 0.1;
	c += textureLod(screen_tex, SCREEN_UV - px, lod).rgb * 0.1;
	c += textureLod(screen_tex, SCREEN_UV + vec2(px.x, -px.y), lod).rgb * 0.1;
	c += textureLod(screen_tex, SCREEN_UV + vec2(-px.x, px.y), lod).rgb * 0.1;
	float grey = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(c, vec3(grey), desaturate * amount);
	vec2 d = (UV - 0.5) * vec2(1.25, 1.0);
	float v = smoothstep(0.2, 0.8, length(d)) * vignette;
	c = mix(c, tint.rgb, clamp(tint.a + v, 0.0, 1.0) * amount);
	COLOR = vec4(c, 1.0);
}
