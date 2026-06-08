import { useState, useEffect, useRef } from 'react';

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

export default function useCountUp(target: number, duration = 1200): number {
  const [value, setValue] = useState(0);
  const valueRef = useRef(0);
  const prevTarget = useRef(target);

  useEffect(() => {
    const commitValue = (nextValue: number) => {
      valueRef.current = nextValue;
      setValue(nextValue);
    };

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (target === 0 || reducedMotion) {
      const raf = requestAnimationFrame(() => {
        prevTarget.current = target;
        commitValue(target);
      });
      return () => cancelAnimationFrame(raf);
    }

    const start = prevTarget.current === target ? 0 : valueRef.current;
    prevTarget.current = target;
    const startTime = performance.now();

    let raf: number;
    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOutCubic(progress);
      commitValue(start + (target - start) * eased);
      if (progress < 1) {
        raf = requestAnimationFrame(tick);
      }
    }

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return value;
}
