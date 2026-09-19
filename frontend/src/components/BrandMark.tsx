import { useState } from "react";
import { BRAND } from "../brand";

/** The logo (from brand.ts) or, if none is set or it fails to load, the orange mark. */
export function BrandMark({ size = 26 }: { size?: number }) {
  const [broken, setBroken] = useState(false);
  if (BRAND.logo && !broken) {
    return <img src={BRAND.logo} alt="" width={size} height={size} onError={() => setBroken(true)}
      style={{ width: size, height: size, objectFit: "contain", borderRadius: size * 0.3 }} />;
  }
  return <span aria-hidden style={{ width: size, height: size, borderRadius: size * 0.3, flex: "none",
    background: "linear-gradient(135deg, var(--ember), var(--ember-2))", boxShadow: `0 0 ${size * 0.6}px var(--ember-glow)` }} />;
}
