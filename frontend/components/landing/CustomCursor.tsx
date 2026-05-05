'use client';
import { useEffect, useRef } from 'react';

export function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const pos = useRef({ x: 0, y: 0 });
  const ringPos = useRef({ x: 0, y: 0 });
  const rafRef = useRef(0);

  useEffect(() => {
    const dot = dotRef.current;
    const ring = ringRef.current;
    if (!dot || !ring) return;

    const onMove = (e: MouseEvent) => {
      pos.current = { x: e.clientX, y: e.clientY };
      dot.style.left = e.clientX + 'px';
      dot.style.top = e.clientY + 'px';
    };

    // Lerp ring to follow dot smoothly
    const lerpRing = () => {
      rafRef.current = requestAnimationFrame(lerpRing);
      ringPos.current.x += (pos.current.x - ringPos.current.x) * 0.1;
      ringPos.current.y += (pos.current.y - ringPos.current.y) * 0.1;
      ring.style.left = ringPos.current.x + 'px';
      ring.style.top = ringPos.current.y + 'px';
    };

    // Hover states for links and buttons
    const hoverables = document.querySelectorAll('a,.btn-ghost-nav,.btn-nav-cta,.logo,.nav-links a');
    const btns = document.querySelectorAll('.btn-primary,.btn-outline');

    const addLink = () => document.body.classList.add('hover-link');
    const removeLink = () => document.body.classList.remove('hover-link');
    const addBtn = () => document.body.classList.add('hover-btn');
    const removeBtn = () => document.body.classList.remove('hover-btn');

    hoverables.forEach(el => {
      el.addEventListener('mouseenter', addLink);
      el.addEventListener('mouseleave', removeLink);
    });
    btns.forEach(el => {
      el.addEventListener('mouseenter', addBtn);
      el.addEventListener('mouseleave', removeBtn);
    });

    // Hide default cursor on landing
    document.body.style.cursor = 'none';

    window.addEventListener('mousemove', onMove);
    rafRef.current = requestAnimationFrame(lerpRing);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('mousemove', onMove);
      document.body.style.cursor = '';
      document.body.classList.remove('hover-link', 'hover-btn');
      hoverables.forEach(el => {
        el.removeEventListener('mouseenter', addLink);
        el.removeEventListener('mouseleave', removeLink);
      });
      btns.forEach(el => {
        el.removeEventListener('mouseenter', addBtn);
        el.removeEventListener('mouseleave', removeBtn);
      });
    };
  }, []);

  return (
    <>
      <div ref={dotRef} id="cursor" />
      <div ref={ringRef} id="cursor-ring" />
    </>
  );
}
