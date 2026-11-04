package main

import (
	"math"

	. "sovbuild/geo"
)

// stairRails adds intermediate handrails (0.9 / 0.7 m) on both flights of the
// wrap-around entrance stair. t = run distance from the landing edge (outward).
func (b *B) stairRails() {
	run := float64(NRiser-1) * StepT // 2.24 m
	pitch := StepR / StepT
	// rail height above the nosing line at outward distance t
	nose := func(t float64) float64 {
		if t <= 0 {
			return FFL
		}
		if t >= run+StepT {
			return 0
		}
		return FFL - t*pitch
	}
	tread := func(t float64) float64 { // walking surface under a post
		if t <= 0 {
			return FFL
		}
		k := math.Ceil(t / StepT)
		return math.Max(0, FFL-k*StepR)
	}
	flights := []struct {
		at  func(t float64) (float64, float64) // plan position for outward distance t
		dir Vec3
	}{
		{func(t float64) (float64, float64) { return LandX0 - t, (LandY0 + StairY1) / 2 }, V3(-1, 0, 0)},
		{func(t float64) (float64, float64) { return (LandX0 + EntX0) / 2, LandY0 - t }, V3(0, -1, 0)},
	}
	for _, f := range flights {
		for _, h := range []float64{RailHi, RailLo} {
			var pts []Vec3
			for _, t := range []float64{-RailExt, 0, run + StepT, run + StepT + RailExt} {
				x, y := f.at(t)
				pts = append(pts, V3(x, y, nose(math.Min(t, run+StepT))+h))
			}
			// bent-down returns at both ends
			s0, s1 := pts[0], pts[len(pts)-1]
			pts = append([]Vec3{s0.Add(f.dir.Mul(0.05)).Add(V3(0, 0, -0.14)), s0.Add(f.dir.Mul(0.05)).Add(V3(0, 0, -0.05))}, pts...)
			pts = append(pts, s1.Add(f.dir.Mul(0.05)).Add(V3(0, 0, -0.05)), s1.Add(f.dir.Mul(0.05)).Add(V3(0, 0, -0.14)))
			b.StairRails.Tube(MMetal, pts, RailR, 10, true, true, 1, 0)
		}
		for _, t := range []float64{-0.15, 0.9, 1.9, run + StepT + 0.15} {
			x, y := f.at(t)
			top := nose(math.Min(t, run+StepT)) + RailHi
			b.StairRails.Tube(MMetal, []Vec3{V3(x, y, tread(t)), V3(x, y, top)}, PostR, 8, false, true, 1, 0)
			b.StairRails.Box(MMetal, V3(x-0.05, y-0.05, tread(t)), V3(x+0.05, y+0.05, tread(t)+0.012), FXn|FXp|FYn|FYp|FZp, WorldUV(1, 1, 0, 0))
		}
	}
}
