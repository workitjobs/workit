"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

/**
 * Marks its box `data-paused` while none of it is on screen, so a CSS loop
 * inside can stop where nobody can watch it (landing.css pauses
 * `.pipe-anim` on it): a loop that runs off screen still costs frames
 * (frontend/CLAUDE.md, "Scroll-driven motion stays cheap"). No attribute in
 * the server's HTML, so the loop plays before the script loads and the
 * page hydrates without a mismatch.
 */
export function HoldOffscreen({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [held, setHeld] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(([entry]) => setHeld(!entry.isIntersecting));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={ref} className={className} data-paused={held || undefined}>
      {children}
    </div>
  );
}
