export function Footer() {
  return (
    <footer style={{ borderTop: "1px solid var(--border)", padding: "24px 0", marginTop: 40 }}>
      <div className="container small mute" style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between" }}>
        <span>
          MVP decision-support model, not a validated prediction model. Sites, values, personnel and
          protocols are simulated. Fire data is near-real-time detections, not perimeters.
        </span>
        <span className="mono">© OpenStreetMap contributors</span>
      </div>
    </footer>
  );
}
