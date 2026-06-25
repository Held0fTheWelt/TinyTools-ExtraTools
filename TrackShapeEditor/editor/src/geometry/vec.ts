export interface Vec2 {
  x: number;
  y: number;
}

export const sub = (a: Vec2, b: Vec2): Vec2 => ({ x: a.x - b.x, y: a.y - b.y });
export const add = (a: Vec2, b: Vec2): Vec2 => ({ x: a.x + b.x, y: a.y + b.y });
export const mul = (a: Vec2, s: number): Vec2 => ({ x: a.x * s, y: a.y * s });
export const len = (a: Vec2): number => Math.hypot(a.x, a.y);
export const dist = (a: Vec2, b: Vec2): number => len(sub(a, b));
export const lerp = (a: Vec2, b: Vec2, t: number): Vec2 => add(a, mul(sub(b, a), t));
export const norm = (a: Vec2): Vec2 => {
  const l = len(a) || 1;
  return { x: a.x / l, y: a.y / l };
};
export const angleDeg = (a: Vec2, b: Vec2): number => {
  const d = Math.min(1, Math.max(-1, a.x * b.x + a.y * b.y));
  return (Math.acos(d) * 180) / Math.PI;
};
