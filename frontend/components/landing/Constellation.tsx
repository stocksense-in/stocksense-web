'use client';
import { useEffect, useRef } from 'react';

/* ── Stock data for tooltip nodes ── */
const STOCKS = [
  { sym: 'INFY', p: '₹1,842', ch: '+1.4%', up: true },
  { sym: 'HDFC', p: '₹1,623', ch: '-0.3%', up: false },
  { sym: 'TCS', p: '₹3,842', ch: '+0.9%', up: true },
  { sym: 'RELIANCE', p: '₹2,934', ch: '+3.2%', up: true },
  { sym: 'NIFTY', p: '24,328', ch: '+0.82%', up: true },
  { sym: 'ZOMATO', p: '₹224', ch: '+0.8%', up: true },
  { sym: 'HAL', p: '₹4,620', ch: '+2.8%', up: true },
  { sym: 'WIPRO', p: '₹458', ch: '-0.4%', up: false },
  { sym: 'BAJFIN', p: '₹6,482', ch: '+0.4%', up: true },
  { sym: 'ICICI', p: '₹1,120', ch: '+1.1%', up: true },
];

/* Warm multi-color palette — green for up, red for down */
const UP_COLS: [number, number, number][] = [
  [0, 230, 118],
  [40, 200, 100],
  [20, 210, 110],
];
const DN_COLS: [number, number, number][] = [
  [255, 58, 58],
  [220, 80, 80],
  [200, 70, 70],
];
function rCol(up: boolean) {
  const a = up ? UP_COLS : DN_COLS;
  return a[Math.floor(Math.random() * a.length)];
}

interface Star {
  x: number; y: number;
  bx: number; by: number;
  r: number;
  col: [number, number, number];
  baseA: number;
  phase: number;
  speed: number;
  z: number;
  hasData: boolean;
  stock: typeof STOCKS[number];
  prox: number;
}

interface Edge {
  a: number; b: number;
  d: number; maxD: number;
  dwell: number;    // how long cursor has been near this edge (seconds)
  breakAmt: number; // 0 = bonded, 1 = fully separated
}

export function Constellation() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const starsRef = useRef<Star[]>([]);
  const edgesRef = useRef<Edge[]>([]);
  const mouseRef = useRef({ x: typeof window !== 'undefined' ? window.innerWidth / 2 : 700, y: typeof window !== 'undefined' ? window.innerHeight / 2 : 400 });
  const smoothMouse = useRef({ x: 0, y: 0 });
  const dimRef = useRef({ w: 0, h: 0 });
  const tRef = useRef(0);
  const rafRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const build = () => {
      const W = dimRef.current.w;
      const H = dimRef.current.h;
      const stars: Star[] = [];
      const edges: Edge[] = [];
      const total = 120;
      const cenX = W / 2, cenY = H / 2;

      for (let i = 0; i < total; i++) {
        let x: number, y: number;
        // 42% clustered toward center
        if (Math.random() < 0.42) {
          const r = (Math.random() + Math.random()) * 0.27;
          const a = Math.random() * Math.PI * 2;
          x = cenX + Math.cos(a) * r * W;
          y = cenY + Math.sin(a) * r * H;
        } else {
          x = Math.random() * W;
          y = Math.random() * H;
        }
        const isUp = Math.random() > 0.38;
        stars.push({
          x, y, bx: x, by: y,
          r: 0.7 + Math.random() * 2.0,
          col: rCol(isUp),
          baseA: 0.07 + Math.random() * 0.25,
          phase: Math.random() * Math.PI * 2,
          speed: 0.18 + Math.random() * 0.55,
          z: 0.12 + Math.random() * 0.88,
          hasData: Math.random() < 0.42,
          stock: STOCKS[Math.floor(Math.random() * STOCKS.length)],
          prox: 0,
        });
      }

      // Build edges
      const maxDist = Math.min(W, H) * 0.18;
      for (let i = 0; i < stars.length; i++) {
        for (let j = i + 1; j < stars.length; j++) {
          const dx = stars[i].bx - stars[j].bx;
          const dy = stars[i].by - stars[j].by;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < maxDist && Math.random() < 0.33) {
            edges.push({ a: i, b: j, d, maxD: maxDist, dwell: 0, breakAmt: 0 });
          }
        }
      }

      starsRef.current = stars;
      edgesRef.current = edges;
    };

    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const W = window.innerWidth;
      const H = window.innerHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = W + 'px';
      canvas.style.height = H + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dimRef.current = { w: W, h: H };
      smoothMouse.current = { x: W / 2, y: H / 2 };
      build();
    };

    resize();

    const onResize = () => resize();
    window.addEventListener('resize', onResize);

    const onMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener('mousemove', onMove);

    /* ── Draw tooltip ── */
    const drawTooltip = (s: Star) => {
      const { x, y, stock, col } = s;
      const tw = 92, th = 34;
      let tx = x + 12, ty = y - th - 6;
      const W = dimRef.current.w;
      if (tx + tw > W - 10) tx = x - tw - 12;
      if (ty < 6) ty = y + 10;

      ctx.fillStyle = 'rgba(12,11,9,0.9)';
      ctx.strokeStyle = `rgba(${col[0]},${col[1]},${col[2]},0.34)`;
      ctx.lineWidth = 0.6;
      ctx.beginPath();
      ctx.roundRect(tx, ty, tw, th, 3);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = 'rgba(240,235,224,0.88)';
      ctx.font = '600 9px "JetBrains Mono",monospace';
      ctx.fillText(stock.sym, tx + 7, ty + 12);

      ctx.fillStyle = `rgba(${col[0]},${col[1]},${col[2]},0.85)`;
      ctx.font = '400 8px "JetBrains Mono",monospace';
      ctx.fillText(`${stock.p}  ${stock.ch}`, tx + 7, ty + 25);
    };

    /* ── Render loop ── */
    const loop = () => {
      rafRef.current = requestAnimationFrame(loop);
      const W = dimRef.current.w;
      const H = dimRef.current.h;
      const stars = starsRef.current;
      const edges = edgesRef.current;
      const pmx = mouseRef.current.x;
      const pmy = mouseRef.current.y;

      tRef.current += 0.009;
      const t = tRef.current;

      // Smooth mouse — faster lerp for snappy repulsion
      smoothMouse.current.x += (pmx - smoothMouse.current.x) * 0.12;
      smoothMouse.current.y += (pmy - smoothMouse.current.y) * 0.12;
      const smx = smoothMouse.current.x;
      const smy = smoothMouse.current.y;

      ctx.clearRect(0, 0, W, H);

      // Mouse ambient glow
      const mg = ctx.createRadialGradient(smx, smy, 0, smx, smy, W * 0.32);
      mg.addColorStop(0, 'rgba(201,168,76,0.018)');
      mg.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = mg;
      ctx.fillRect(0, 0, W, H);

      // Corner glows — warm red/green spectrum
      const corners: [number, number, string][] = [
        [0, 0, '255,58,58'],
        [W, 0, '0,230,118'],
        [0, H, '255,58,58'],
        [W, H, '0,230,118'],
      ];
      for (const [cx, cy, col] of corners) {
        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, W * 0.22);
        g.addColorStop(0, `rgba(${col},0.032)`);
        g.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = g;
        ctx.fillRect(0, 0, W, H);
      }

      // Update star positions with parallax
      for (const s of stars) {
        const px = (smx / W - 0.5) * 26 * s.z;
        const py = (smy / H - 0.5) * 15 * s.z;
        s.x = s.bx + px + Math.sin(t * s.speed + s.phase) * 1.8;
        s.y = s.by + py;
        const dx = smx - s.x, dy = smy - s.y;
        s.prox = Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) / 155);
      }

      // Dwell-based bond breaking
      // Phase 1: hover → glow. Phase 2: dwell > 0.4s → slow separation
      const HOVER_RADIUS = 65;
      const DWELL_THRESHOLD = 0.4; // seconds before breaking starts
      const BREAK_SPEED = 0.012;   // how fast breakAmt rises per frame (~0.7/sec)
      const HEAL_SPEED = 0.006;    // how fast bonds reform when cursor leaves
      const MAX_PUSH = 32;         // max displacement at full break

      for (const e of edges) {
        const a = stars[e.a], b = stars[e.b];
        const emx = (a.x + b.x) / 2;
        const emy = (a.y + b.y) / 2;
        const edx = smx - emx;
        const edy = smy - emy;
        const eDist = Math.sqrt(edx * edx + edy * edy);
        const isNear = eDist < HOVER_RADIUS;

        // Accumulate dwell time
        if (isNear) {
          e.dwell += 0.016; // ~60fps
        } else {
          e.dwell = Math.max(0, e.dwell - 0.03); // reset faster
        }

        // Only start breaking after dwell threshold
        if (e.dwell > DWELL_THRESHOLD) {
          e.breakAmt = Math.min(1, e.breakAmt + BREAK_SPEED);
        } else if (!isNear) {
          e.breakAmt = Math.max(0, e.breakAmt - HEAL_SPEED); // slowly reform
        }

        // Apply separation — push stars apart along edge axis
        if (e.breakAmt > 0.001) {
          const ex = b.x - a.x;
          const ey = b.y - a.y;
          const eLen = Math.sqrt(ex * ex + ey * ey) || 1;
          const push = e.breakAmt * MAX_PUSH;
          a.x -= (ex / eLen) * push;
          a.y -= (ey / eLen) * push;
          b.x += (ex / eLen) * push;
          b.y += (ey / eLen) * push;
        }
      }

      // Draw edges
      for (const e of edges) {
        const a = stars[e.a], b = stars[e.b];
        const prox = Math.max(a.prox, b.prox);

        // Line fades as bond breaks
        const bondFade = 1 - e.breakAmt;

        // Glow brighter on hover (even before breaking)
        const emx = (a.x + b.x) / 2;
        const emy = (a.y + b.y) / 2;
        const edx = smx - emx;
        const edy = smy - emy;
        const eDist = Math.sqrt(edx * edx + edy * edy);
        const hoverGlow = eDist < HOVER_RADIUS ? (1 - eDist / HOVER_RADIUS) * 0.15 : 0;

        const baseAlpha = (1 - e.d / e.maxD) * 0.032 + prox * 0.11;
        const alpha = (baseAlpha + hoverGlow) * bondFade;
        if (alpha < 0.003) continue;

        const al = alpha + (prox > 0.15 ? (Math.sin(t * 2 + e.a * 0.3) * 0.5 + 0.5) : 0) * 0.05;

        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);

        const gc = ctx.createLinearGradient(a.x, a.y, b.x, b.y);
        gc.addColorStop(0, `rgba(${a.col[0]},${a.col[1]},${a.col[2]},${al})`);
        gc.addColorStop(1, `rgba(${b.col[0]},${b.col[1]},${b.col[2]},${al})`);
        ctx.strokeStyle = gc;
        ctx.lineWidth = (0.4 + prox * 0.55) * (0.3 + bondFade * 0.7);
        ctx.stroke();
      }

      // Draw stars
      let hoverStar: Star | null = null;
      for (const s of stars) {
        const alpha = Math.min(0.92, s.baseA + s.prox * 0.52);
        const r = s.r * (1 + s.prox * 0.45);

        // Glow halo near mouse
        if (s.prox > 0.07) {
          const gr = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, 19 + s.prox * 13);
          gr.addColorStop(0, `rgba(${s.col[0]},${s.col[1]},${s.col[2]},${s.prox * 0.16})`);
          gr.addColorStop(1, 'rgba(0,0,0,0)');
          ctx.fillStyle = gr;
          ctx.beginPath();
          ctx.arc(s.x, s.y, 19 + s.prox * 13, 0, Math.PI * 2);
          ctx.fill();
        }

        // Star dot
        ctx.beginPath();
        ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${s.col[0]},${s.col[1]},${s.col[2]},${alpha})`;
        ctx.fill();

        // Pick hover star for tooltip
        if (s.hasData && s.prox > 0.48) {
          if (!hoverStar || s.prox > hoverStar.prox) hoverStar = s;
        }
      }

      // Tooltip
      if (hoverStar) drawTooltip(hoverStar);

      // Center vignette
      const v = ctx.createRadialGradient(W / 2, H * 0.44, H * 0.05, W / 2, H * 0.44, H * 0.46);
      v.addColorStop(0, 'rgba(12,11,9,0.42)');
      v.addColorStop(0.6, 'rgba(12,11,9,0.07)');
      v.addColorStop(1, 'rgba(12,11,9,0)');
      ctx.fillStyle = v;
      ctx.fillRect(0, 0, W, H);
    };

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', onResize);
      window.removeEventListener('mousemove', onMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
}
