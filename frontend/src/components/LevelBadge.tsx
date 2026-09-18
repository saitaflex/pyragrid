import type { Level } from "../api/types";

export function LevelBadge({ level, score }: { level: Level; score?: number }) {
  return (
    <span className={`badge lv-${level} ${level}`}>
      <span className="dot" />
      {level}{score !== undefined ? ` · ${score}` : ""}
    </span>
  );
}
