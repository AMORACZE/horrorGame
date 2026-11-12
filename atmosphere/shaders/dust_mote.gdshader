shader_type spatial;
// Dust motes: tiny additive billboards lit ONLY by direct light (no ambient,
// no GI, no fog), with a forward-scattering phase. Inside a sun shaft they
// sparkle; in shadow they vanish. Drawn by GPUParticles3D (dust_motes.tscn).
render_mode blend_add, depth_draw_never, cull_disabled, specular_disabled,
		ambient_light_disabled, fog_disabled;

// Physical mote diameter in metres (before per-particle scale).
instance uniform float mote_size = 0.006;
// Overall brightness of a lit mote.
instance uniform float brightness = 1.0;
// Motes never shrink below this many pixels; smaller ones fade instead,
// so distant dust does not crawl or pop.
uniform float min_pixels : hint_range(0.5, 4.0) = 1.75;
// Henyey-Greenstein g: > 0 makes motes brightest when looking toward the sun.
uniform float forward_scatter : hint_range(0.0, 0.9) = 0.45;
uniform vec3 tint : source_color = vec3(1.0, 0.95, 0.87);
// Distance from the camera below which motes fade out (no blobs on the lens).
uniform float near_fade = 0.35;

varying float v_alpha;

float hash11(float p) {
	p = fract(p * 0.1031);
	p *= p + 33.33;
	p *= p + p;
	return fract(p);
}

void vertex() {
	// Camera-facing billboard at the particle position.
	mat4 world = mat4(normalize(INV_VIEW_MATRIX[0]), normalize(INV_VIEW_MATRIX[1]),
			normalize(INV_VIEW_MATRIX[2]), MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = VIEW_MATRIX * world;
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);

	float pscale = length(MODEL_MATRIX[0].xyz);
	vec4 centre = MODELVIEW_MATRIX * vec4(0.0, 0.0, 0.0, 1.0);
	float dist = max(-centre.z, 0.01);
	float pixel_world = 2.0 * dist / (PROJECTION_MATRIX[1][1] * VIEWPORT_SIZE.y);
	float size = mote_size * pscale;
	float draw_size = max(size, pixel_world * min_pixels);
	float coverage = (size * size) / (draw_size * draw_size);
	VERTEX *= draw_size;

	float life = INSTANCE_CUSTOM.y;
	float fade = smoothstep(0.0, 0.15, life) * (1.0 - smoothstep(0.85, 1.0, life));
	float h = hash11(float(INSTANCE_ID) + 0.37);
	// Flakes turning in the air catch the light now and then.
	float twinkle = 0.55 + 0.45 * sin(TIME * (0.6 + h * 1.7) + h * 40.0);
	v_alpha = coverage * fade * twinkle * smoothstep(near_fade, near_fade * 2.5, dist);
}

void fragment() {
	vec2 d = UV * 2.0 - 1.0;
	float r2 = dot(d, d);
	ALBEDO = tint;
	ALPHA = exp(-r2 * 3.0) * (1.0 - smoothstep(0.6, 1.0, r2)) * v_alpha;
}

void light() {
	float g = forward_scatter;
	// Angle between the light's travel direction and the direction to the eye.
	float cos_t = dot(-LIGHT, VIEW);
	float phase = (1.0 - g * g) / pow(1.0 + g * g - 2.0 * g * cos_t, 1.5);
	DIFFUSE_LIGHT += LIGHT_COLOR * ATTENUATION * phase * brightness / PI;
}
