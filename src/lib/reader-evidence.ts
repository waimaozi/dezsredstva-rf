export type ReadingState = {
  at: number | null;
  eligible: boolean;
  activeMs: number;
  progress: number;
  reached: boolean;
};

export const newReadingState = (): ReadingState => ({
  at: null, eligible: false, activeMs: 0, progress: 0, reached: false
});

// Foreground time and text reached are engagement proxies, not evidence of comprehension.
export function advanceReading(state: ReadingState, at: number, eligible: boolean, progress: number): ReadingState {
  const elapsed = state.at === null ? 0 : Math.max(0, Math.min(2000, at - state.at));
  const activeMs = state.activeMs + (state.eligible && eligible ? elapsed : 0);
  const reachedProgress = eligible ? Math.max(state.progress, Math.min(1, Math.max(0, progress))) : state.progress;
  return { at, eligible, activeMs, progress: reachedProgress,
    reached: state.reached || (activeMs >= 90_000 && reachedProgress >= 0.5) };
}

export const feedbackGoals = {
  useful: "reader_useful", not_relevant: "reader_not_relevant", needs_detail: "reader_needs_detail"
} as const;
export const readerRoles = ["unspecified", "quality", "laboratory", "technologist", "sanitation", "veterinary", "other"] as const;

export function evidenceParameters(kind: "translation" | "collection", path: string, role: string, response: string) {
  const safeRole = (readerRoles as readonly string[]).includes(role) ? role : "unspecified";
  // One event hierarchy keeps the page, role and answer together in goal_params reports.
  return { research_v1: { [kind]: { [path.split(/[?#]/)[0]]: { [safeRole]: response } } } };
}
