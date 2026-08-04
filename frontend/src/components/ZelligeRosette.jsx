import { polarPoint } from '../utils/geometry';

const SIZE = 420;
const CENTER = SIZE / 2;

// Les 8 kites (losanges) du guide extérieur, décalés de 22.5° (profondeur de tessellation)
function outlineStarTiles() {
  return Array.from({ length: 8 }, (_, i) => {
    const baseAngle = i * 45 + 22.5;
    const tip = polarPoint(CENTER, CENTER, 150, baseAngle);
    const left = polarPoint(CENTER, CENTER, 58, baseAngle - 22.5);
    const right = polarPoint(CENTER, CENTER, 58, baseAngle + 22.5);
    return { tip, left, right, key: `outline-${i}` };
  });
}

// Les 8 kites de l'étoile principale, alternant vert et rouge
function mainStarTiles() {
  return Array.from({ length: 8 }, (_, i) => {
    const baseAngle = i * 45;
    const tip = polarPoint(CENTER, CENTER, 132, baseAngle);
    const left = polarPoint(CENTER, CENTER, 50, baseAngle - 22.5);
    const right = polarPoint(CENTER, CENTER, 50, baseAngle + 22.5);
    return { tip, left, right, color: i % 2 === 0 ? 'var(--vert)' : 'var(--rouge)', key: `main-${i}` };
  });
}

// L'anneau extérieur de 16 petits triangles alternant safran / sable
function borderRingTiles() {
  const count = 16;
  return Array.from({ length: count }, (_, i) => {
    const a0 = i * (360 / count);
    const a1 = (i + 1) * (360 / count);
    const outer0 = polarPoint(CENTER, CENTER, 190, a0);
    const outer1 = polarPoint(CENTER, CENTER, 190, a1);
    const inner = polarPoint(CENTER, CENTER, 168, (a0 + a1) / 2);
    return {
      outer0, outer1, inner,
      color: i % 2 === 0 ? 'var(--safran)' : 'var(--sable-clair)',
      key: `border-${i}`,
    };
  });
}

export default function ZelligeRosette() {
  const outline = outlineStarTiles();
  const main = mainStarTiles();
  const border = borderRingTiles();
  let delayIndex = 0;

  return (
    <svg viewBox={`0 0 ${SIZE} ${SIZE}`} role="img" aria-label="Rosace zellige décorative">
      <circle
        cx={CENTER} cy={CENTER} r={168}
        fill="none" stroke="var(--vert)" strokeWidth="1" opacity="0.35"
      />

      {outline.map((t) => (
        <polygon
          key={t.key}
          className="tile"
          style={{ animationDelay: `${(delayIndex++) * 0.05}s` }}
          points={`${CENTER},${CENTER} ${t.left[0]},${t.left[1]} ${t.tip[0]},${t.tip[1]} ${t.right[0]},${t.right[1]}`}
          fill="none" stroke="var(--safran)" strokeWidth="1.5" opacity="0.55"
        />
      ))}

      {main.map((t) => (
        <polygon
          key={t.key}
          className="tile"
          style={{ animationDelay: `${(delayIndex++) * 0.05}s` }}
          points={`${CENTER},${CENTER} ${t.left[0]},${t.left[1]} ${t.tip[0]},${t.tip[1]} ${t.right[0]},${t.right[1]}`}
          fill={t.color} stroke="var(--sable)" strokeWidth="2"
        />
      ))}

      {border.map((t) => (
        <polygon
          key={t.key}
          className="tile"
          style={{ animationDelay: `${(delayIndex++) * 0.03}s` }}
          points={`${t.outer0[0]},${t.outer0[1]} ${t.inner[0]},${t.inner[1]} ${t.outer1[0]},${t.outer1[1]}`}
          fill={t.color} stroke="var(--cedre)" strokeWidth="0.75" opacity="0.9"
        />
      ))}

      <circle
        className="tile"
        style={{ animationDelay: `${delayIndex * 0.05}s` }}
        cx={CENTER} cy={CENTER} r={26}
        fill="var(--sable)" stroke="var(--cedre)" strokeWidth="1.5"
      />
    </svg>
  );
}
