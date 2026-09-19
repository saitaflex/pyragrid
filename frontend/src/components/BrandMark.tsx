import { useState } from "react";
import { BRAND } from "../brand";

/** The logo (from brand.ts) or, if none is set or it fails to load, the orange mark. */
export function BrandMark({ size = 26 }: { size?: number }) {
  const [broken, setBroken] = useState(false);
  if (BRAND.logo && !broken) {
    // the artwork is black ink on paper, so it sits on a light tile on the dark theme
    return <img src={BRAND.logo} alt="" width={size} height={size} onError={() => setBroken(true)}
      style={{ width: size, height: size, objectFit: "contain", borderRadius: size * 0.28, background: "#FAF9F6",
        boxShadow: "0 0 0 1px rgba(255,255,255,.12), 0 4px 14px -4px rgba(255,90,31,.45)", flex: "none" }} />;
  }
  return <span aria-hidden style={{ width: size, height: size, borderRadius: size * 0.3, flex: "none",
    background: "linear-gradient(135deg, var(--ember), var(--ember-2))", boxShadow: `0 0 ${size * 0.6}px var(--ember-glow)` }} />;
}
