"""Shape and motion for the dictation overlay.

Kept apart from the widget so the geometry and the easing can be reasoned about
-- and tested -- without a display attached.

The overlay is meant to read as part of the Caelestia shell rather than as a
window floating in front of it. Two things do most of that work: the panel rises
out of the shell's bottom border instead of appearing, and where it meets that
border the two surfaces join with a concave fillet rather than a corner. The
shell draws those joins with a signed-distance field; at this size the same
silhouette can be had from four arcs, which costs nothing and needs no shader.
"""

import math

# Caelestia's expressiveFastSpatial curve, taken from the shell's own token
# defaults (tokens.hpp). Two control points and an endpoint, as a cubic bezier
# from (0, 0). The first control point sits above 1, which is what gives the
# motion its slight overshoot -- the panel arrives, leans past its resting place
# and settles, rather than easing politely into position.
EXPRESSIVE_FAST_SPATIAL = (0.42, 1.67, 0.21, 0.9)

# The shell's own duration for the same curve, scaled the way the window board
# scales it: a reveal you did not ask for should already be finished by the time
# you look at it.
SLIDE_MS = 235.0


def cubic_bezier(p1x, p1y, p2x, p2y):
    """An easing function matching a CSS/Qt cubic bezier.

    Returns f(x) -> y for x in [0, 1]. The parameter of a bezier is not its x,
    so x is inverted numerically; bisection is plenty at these durations and
    cannot diverge the way Newton can on a curve that overshoots.
    """

    def bezier(a1, a2, t):
        mt = 1.0 - t
        return 3.0 * mt * mt * t * a1 + 3.0 * mt * t * t * a2 + t * t * t

    def ease(x):
        if x <= 0.0:
            return 0.0
        if x >= 1.0:
            return 1.0
        lo, hi = 0.0, 1.0
        for _ in range(24):
            mid = (lo + hi) * 0.5
            if bezier(p1x, p2x, mid) < x:
                lo = mid
            else:
                hi = mid
        return bezier(p1y, p2y, (lo + hi) * 0.5)

    return ease


ease_spatial = cubic_bezier(*EXPRESSIVE_FAST_SPATIAL)


def panel_path(cr, width, height, progress, panel_w, panel_h,
               corner_r, fillet_r, border):
    """Trace the overlay's outline: border strip, panel, and the joins between.

    `progress` is 0 when the panel is entirely hidden behind the border and 1
    when it is fully out. The fillets shrink with it, so the join stays correct
    at every point of the slide instead of only at the end.

    When `border` is zero there is no shell border to rise out of, so the panel
    is drawn as a free-standing pill with rounded lower corners -- the same
    widget still looks deliberate on a desktop that is not Caelestia.
    """
    if progress <= 0.0:
        return False

    baseline = height - border
    ph = panel_h * progress
    if ph <= 0.5:
        return False

    x0 = (width - panel_w) * 0.5
    x1 = x0 + panel_w
    ty = baseline - ph

    r = min(corner_r, panel_w * 0.5, ph)

    if border <= 0:
        # No border to merge with: a rounded rectangle, bottom corners included.
        br = min(corner_r, ph * 0.5)
        cr.new_path()
        cr.arc(x0 + r, ty + r, r, math.pi, 1.5 * math.pi)
        cr.arc(x1 - r, ty + r, r, 1.5 * math.pi, 2.0 * math.pi)
        cr.arc(x1 - br, baseline - br, br, 0.0, 0.5 * math.pi)
        cr.arc(x0 + br, baseline - br, br, 0.5 * math.pi, math.pi)
        cr.close_path()
        return True

    # The fillet cannot be deeper than the panel is tall, or the arc would
    # reach above the panel's own top edge and the outline would cross itself.
    fr = max(0.0, min(fillet_r, ph - r, (width - panel_w) * 0.5))

    cr.new_path()
    cr.move_to(0.0, height)
    cr.line_to(0.0, baseline)
    cr.line_to(x0 - fr, baseline)
    # Concave: curves up off the border into the panel's left flank.
    if fr > 0:
        cr.arc_negative(x0 - fr, baseline - fr, fr, 0.5 * math.pi, 0.0)
    cr.line_to(x0, ty + r)
    cr.arc(x0 + r, ty + r, r, math.pi, 1.5 * math.pi)
    cr.line_to(x1 - r, ty)
    cr.arc(x1 - r, ty + r, r, 1.5 * math.pi, 2.0 * math.pi)
    cr.line_to(x1, baseline - fr)
    # Concave again, mirrored.
    if fr > 0:
        cr.arc_negative(x1 + fr, baseline - fr, fr, math.pi, 0.5 * math.pi)
    cr.line_to(width, baseline)
    cr.line_to(width, height)
    cr.close_path()
    return True
