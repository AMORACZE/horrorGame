shader_type spatial;
// Off-air CRT static ("snow") for a television screen mesh.
// Screen coordinates come from the mesh's local XY, so it works on a curved
// (flattened sphere) screen as well as on a quad. `power` animates the tube:
// 0 = off, a bright line while it warms up, 1 = full raster.
render_mode unshaded, cull_back, shadows_disabled;

instance uniform float power : hint_range(0.0, 1.0) = 1.0;
uniform float brightness : hint_range(0.0, 4.0) = 1.15;
uniform vec2 screen_size = vec2(1.0, 1.0);     // mesh-local extent of the tube face
uniform vec2 resolution = vec2(220.0, 165.0);  // noise cells across the tube
uniform float frame_rate = 30.0;
uniform vec3 tint : source_color = vec3(0.86, 0.9, 1.0);

varying vec2 scr;

float hash(vec2 p) {
	p = fract(p * vec2(443.897, 441.423));
	p += dot(p, p.yx + 19.19);
	return fract((p.x + p.y) * p.x);
}

void vertex() {
	scr = VERTEX.xy / screen_size + 0.5;
}

void fragment() {
	vec2 uv = clamp(scr, 0.0, 1.0);
	float t = floor(TIME * frame_rate);
	vec2 cell = floor(uv * resolution);
	float n = hash(cell + vec2(t * 3.7, t * 1.3));
	// Horizontal smear: neighbouring cells along a line share noise a little.
	float n2 = hash(vec2(floor(cell.x * 0.5), cell.y) + t);
	float snow = pow(mix(n, n2, 0.35), 1.6);
	// Scanlines and a slow rolling hum bar.
	float scan = 0.82 + 0.18 * sin(uv.y * resolution.y * 3.14159);
	float roll = 0.86 + 0.14 * sin((uv.y + TIME * 0.21) * 6.2831);
	// Tube edges: darker towards the corners.
	vec2 c = uv - 0.5;
	float vig = clamp(1.0 - dot(c, c) * 2.2, 0.0, 1.0);
	// Warm-up / collapse: the raster grows from a horizontal line at the centre.
	float half_h = max(power * power, 0.004) * 0.5;
	float band = 1.0 - smoothstep(half_h, half_h + 0.01, abs(uv.y - 0.5));
	float line_glow = (1.0 - smoothstep(0.0, 0.25, power)) * 3.0;
	float lum = (snow * scan * roll * vig + line_glow) * band;
	lum *= smoothstep(0.0, 0.05, power);
	// Unshaded: ALBEDO is the final colour; values over 1 feed the glow.
	ALBEDO = tint * lum * brightness;
}
