"""Small 2D geometry helpers (all in millimetres, y up)."""
import math


def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def add(a, b): return (a[0] + b[0], a[1] + b[1])
def mul(a, k): return (a[0] * k, a[1] * k)
def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def norm(a):
    d = math.hypot(*a)
    return (a[0] / d, a[1] / d) if d > 1e-12 else (1.0, 0.0)
def perp(a): return (-a[1], a[0])
def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
def angle_deg(a, b): return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def rot(p, deg, c=(0.0, 0.0)):
    r = math.radians(deg); cs, sn = math.cos(r), math.sin(r)
    x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x * cs - y * sn, c[1] + x * sn + y * cs)


def segs(pts, closed=False):
    n = len(pts); out = [(pts[i], pts[i + 1]) for i in range(n - 1)]
    if closed and n > 2: out.append((pts[-1], pts[0]))
    return out


def poly_length(pts, closed=False): return sum(dist(a, b) for a, b in segs(pts, closed))


def point_at(pts, s, closed=False):
    s = max(0.0, s)
    for a, b in segs(pts, closed):
        L = dist(a, b)
        if L < 1e-9: continue
        if s <= L:
            t = norm(sub(b, a)); return (a[0] + t[0] * s, a[1] + t[1] * s), t
        s -= L
    a, b = segs(pts, closed)[-1]
    return b, norm(sub(b, a))


def project_on_seg(p, a, b):
    ab = sub(b, a); L2 = dot(ab, ab)
    if L2 < 1e-12: return a, 0.0
    t = max(0.0, min(1.0, dot(sub(p, a), ab) / L2))
    return (a[0] + ab[0] * t, a[1] + ab[1] * t), t


def project_on_poly(p, pts, closed=False):
    """-> (distance, arc_length_s, foot_point)"""
    best = (1e18, 0.0, pts[0]); acc = 0.0
    for a, b in segs(pts, closed):
        f, t = project_on_seg(p, a, b); d = dist(p, f); L = dist(a, b)
        if d < best[0]: best = (d, acc + t * L, f)
        acc += L
    return best


def arc_pts(c, r, a0, a1, step=6.0):
    n = max(2, int(abs(a1 - a0) / step) + 1)
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
