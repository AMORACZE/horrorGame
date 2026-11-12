class_name ReaderStyles
extends RefCounted
## How the document reader dresses each ReadableInteractable.Style.
## Paper colour, ink, fonts, margins, sheet size and a slight tilt.

class Look:
	var paper: Color
	var ink: Color
	var title_ink: Color
	var body_font: Font
	var title_font: Font
	var body_size: int
	var title_size: int
	var margin_h: int
	var margin_v: int
	var sheet_size: Vector2
	var tilt_degrees: float
	var line_spacing: int
	var title_uppercase: bool
	var align: HorizontalAlignment
	var title_align: HorizontalAlignment
	## Draw a thin rule under the title.
	var rule: bool
	## Faint ruled lines and a red margin (notebook paper).
	var ruled: bool


static func for_style(style: int) -> Look:
	var l := Look.new()
	l.align = HORIZONTAL_ALIGNMENT_LEFT
	l.title_align = HORIZONTAL_ALIGNMENT_LEFT
	l.title_uppercase = false
	l.rule = false
	l.ruled = false
	match style:
		ReadableInteractable.Style.HANDWRITTEN:
			# Yellow legal pad, blue ballpoint.
			l.paper = Color(0.96, 0.91, 0.62)
			l.ink = Color(0.12, 0.18, 0.45)
			l.title_ink = l.ink
			l.body_font = UIFonts.HAND
			l.title_font = UIFonts.HAND
			l.body_size = 23
			l.title_size = 26
			l.margin_h = 52
			l.margin_v = 46
			l.sheet_size = Vector2(560, 680)
			l.tilt_degrees = 0.0
			l.line_spacing = 8
			l.ruled = true
		ReadableInteractable.Style.TYPED:
			# Bond paper through a ribbon typewriter.
			l.paper = Color(0.94, 0.93, 0.89)
			l.ink = Color(0.07, 0.07, 0.08)
			l.title_ink = l.ink
			l.body_font = UIFonts.TYPEWRITER
			l.title_font = UIFonts.TYPEWRITER
			l.body_size = 19
			l.title_size = 19
			l.margin_h = 78
			l.margin_v = 70
			l.sheet_size = Vector2(620, 800)
			l.tilt_degrees = 0.0
			l.line_spacing = 4
			l.title_uppercase = true
		ReadableInteractable.Style.LABEL:
			# A stick-on label or index card: small, centred, bold title.
			l.paper = Color(0.97, 0.96, 0.92)
			l.ink = Color(0.1, 0.1, 0.1)
			l.title_ink = Color(0.55, 0.12, 0.1)
			l.body_font = UIFonts.SANS
			l.title_font = UIFonts.SANS_BOLD
			l.body_size = 18
			l.title_size = 21
			l.margin_h = 30
			l.margin_v = 24
			l.sheet_size = Vector2(460, 250)
			l.tilt_degrees = 0.0
			l.line_spacing = 3
			l.title_uppercase = true
			l.align = HORIZONTAL_ALIGNMENT_CENTER
			l.title_align = HORIZONTAL_ALIGNMENT_CENTER
			l.rule = true
		ReadableInteractable.Style.PRINT:
			# Printed page: manual, booklet, newspaper clipping.
			l.paper = Color(0.89, 0.87, 0.81)
			l.ink = Color(0.1, 0.1, 0.1)
			l.title_ink = l.ink
			l.body_font = UIFonts.SERIF
			l.title_font = UIFonts.SANS_BOLD
			l.body_size = 17
			l.title_size = 25
			l.margin_h = 56
			l.margin_v = 50
			l.sheet_size = Vector2(600, 780)
			l.tilt_degrees = 0.0
			l.line_spacing = 3
			l.align = HORIZONTAL_ALIGNMENT_FILL
			l.rule = true
		_:
			# PAPER: plain white letter paper, a pen-and-serif feel.
			l.paper = Color(0.95, 0.94, 0.9)
			l.ink = Color(0.15, 0.15, 0.2)
			l.title_ink = l.ink
			l.body_font = UIFonts.SERIF
			l.title_font = UIFonts.SERIF_BOLD
			l.body_size = 19
			l.title_size = 22
			l.margin_h = 60
			l.margin_v = 56
			l.sheet_size = Vector2(580, 760)
			l.tilt_degrees = 0.0
			l.line_spacing = 5
	return l
