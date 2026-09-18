export function EvidenceChip({ ek }: { ek: string }) {
  const [kind, ...rest] = ek.split(":");
  const label = kind.charAt(0).toUpperCase() + kind.slice(1);
  return (
    <span className="chip" style={{ textTransform: "none", color: "var(--text-dim)" }}>
      <span style={{ color: "var(--ember-2)" }}>{label}:</span> {rest.join(":")}
    </span>
  );
}
