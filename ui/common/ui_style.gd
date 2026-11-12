class_name UIStyle
extends RefCounted
## Shared colours and sizes for the UI. The theme builder
## (`ui/theme/build_theme.gd`) and the scripts that colour things at runtime
## both read from here, so the look can be retuned in one file.

## Warm off-white, never pure #fff: sits better under the tape look.
const TEXT := Color(0.96, 0.95, 0.91, 1.0)
const TEXT_DIM := Color(0.96, 0.95, 0.91, 0.55)
const TEXT_FAINT := Color(0.96, 0.95, 0.91, 0.32)
## Soft dark edge that keeps white type readable over a blown-out window.
const OUTLINE := Color(0.04, 0.035, 0.03, 0.45)
const SHADOW := Color(0.0, 0.0, 0.0, 0.32)

## Screen dims behind modals.
const DIM_EXAMINE := Color(0.03, 0.028, 0.025, 0.62)
const DIM_READER := Color(0.03, 0.028, 0.025, 0.70)
const DIM_PAUSE := Color(0.02, 0.02, 0.02, 0.80)

const FONT_SIZE_HUD := 17
const FONT_SIZE_OBSERVATION := 21
const FONT_SIZE_MENU := 22
const FONT_SIZE_SMALL := 14
