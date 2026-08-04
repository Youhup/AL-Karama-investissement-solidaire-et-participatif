import { polarPoint } from '../utils/geometry';

/**
 * Anneau de progression du financement, stylisé pour évoquer un
 * assemblage de tuiles : anneau de fond en pointillés (tuiles non
 * remplies), arc plein en rouge par-dessus (part financée), et des
 * traits de "joint" dorés qui subdivisent visuellement l'arc rempli.
 */
export default function ZelligeProgressRing({ percent, size = 68 }) {
  const center = size / 2;
  const radius = size * 0.41;
  const strokeWidth = size * 0.103;
  const circumference = 2 * Math.PI * radius;
  const fontSize = size * 0.206;

  const clamped = Math.max(0, Math.min(100, percent));
  const tickCount = Math.max(1, Math.round(clamped / 8));

  const ticks = Array.from({ length: tickCount }, (_, i) => {
    const angle = (clamped / tickCount) * i;
    const inner = polarPoint(center, center, radius - strokeWidth * 0.6, angle);
    const outer = polarPoint(center, center, radius + strokeWidth * 0.6, angle);
    return { inner, outer, key: `tick-${i}` };
  });

  return (
    <div className="ring-wrap" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${Math.round(clamped)} pour cent financé`}>
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="var(--cedre)" strokeOpacity="0.18"
          strokeWidth={strokeWidth} strokeDasharray={`${strokeWidth * 0.8} ${strokeWidth * 0.45}`}
        />
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="var(--rouge)" strokeWidth={strokeWidth} strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - clamped / 100)}
          transform={`rotate(-90 ${center} ${center})`}
        />
        {ticks.map((t) => (
          <line
            key={t.key}
            x1={t.inner[0]} y1={t.inner[1]} x2={t.outer[0]} y2={t.outer[1]}
            stroke="var(--sable)" strokeWidth={Math.max(1, strokeWidth * 0.2)}
          />
        ))}
      </svg>
      <div className="ring-pct" style={{ fontSize }}>{Math.round(clamped)}%</div>
    </div>
  );
}
