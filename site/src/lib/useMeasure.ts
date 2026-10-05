import { useLayoutEffect, useRef, useState, type RefObject } from "react";

/**
 * Layout width of an element in CSS pixels, so charts draw at real size and text stays legible on phones.
 * clientWidth ignores CSS transforms, so a chart inside the scaled-down film preview still lays out at full size.
 */
export function useMeasure<T extends HTMLElement>(fallback = 720): [RefObject<T | null>, number] {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => setWidth(Math.max(280, Math.round(el.clientWidth)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}
