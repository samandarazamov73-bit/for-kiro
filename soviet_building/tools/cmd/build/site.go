package main

import . "sovbuild/geo"

// site builds the paved forecourt, the blind strip (otmostka) and paths to the rear exits.
func (b *B) site() {
	m := b.Site
	type rc struct {
		x0, y0, x1, y1 float64
		edges          int // which outer edges get a kerb face
	}
	rects := []rc{
		{2, -25, EntX0, 0, FXn | FYn},
		{EntX0, -25, EntX1, EntY0, FYn},
		{EntX1, -25, 46, 0, FXp | FYn},
		{-1, -1, 2, 0, FXn | FYn},
		{46, -1, MainLen + 1, 0, FXp | FYn},
		{-1, 0, 0, MainDepth, FXn},
		{MainLen, 0, MainLen + 1, MainDepth, FXp},
		{-1, MainDepth, MainLen + 1, MainDepth + 1, FXn | FXp | FYp},
		{2.0, MainDepth + 1, 7.0, MainDepth + 6, FXn | FXp | FYp},
		{68.0, MainDepth + 1, 73.0, MainDepth + 6, FXn | FXp | FYp},
	}
	for _, r := range rects {
		m.Box(MPaving, V3(r.x0, r.y0, -0.15), V3(r.x1, r.y1, 0), r.edges|FZp, WorldUV(3, 3, 0.37, 0.11))
	}
}
