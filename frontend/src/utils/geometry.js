/**
 * Retourne les coordonnées [x, y] d'un point situé à `radius` du centre
 * (cx, cy), à `angleDeg` degrés, où 0° pointe vers le haut (convention
 * horloge, comme un cadran).
 */
export function polarPoint(cx, cy, radius, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + radius * Math.cos(rad), cy + radius * Math.sin(rad)];
}
