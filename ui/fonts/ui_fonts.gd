class_name UIFonts
extends RefCounted
## Every font the UI uses, in one place.
##
## There are no font files in the repo yet, so each entry is a SystemFont with a
## fallback chain (macOS / Windows names first, then the Linux build machine's
## DejaVu / Free* / Charter / Courier 10 Pitch). To drop in a real font, replace
## the .tres it points to with a FontFile (or point the constant at the new
## file) and re-run `ui/theme/build_theme.gd`. Nothing else references fonts.

## Quiet sans for the HUD, observation line, examine captions and menus.
const SANS: Font = preload("res://ui/fonts/ui_sans.tres")
const SANS_BOLD: Font = preload("res://ui/fonts/ui_sans_bold.tres")
## Book / letter body text (Style.PAPER, Style.PRINT).
const SERIF: Font = preload("res://ui/fonts/ui_serif.tres")
const SERIF_BOLD: Font = preload("res://ui/fonts/ui_serif_bold.tres")
## Typewriter (Style.TYPED).
const TYPEWRITER: Font = preload("res://ui/fonts/ui_typewriter.tres")
## Stand-in for handwriting (Style.HANDWRITTEN). Real handwriting font wanted.
const HAND: Font = preload("res://ui/fonts/ui_hand.tres")
