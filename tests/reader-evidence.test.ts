import assert from "node:assert/strict";
import test from "node:test";
import { advanceReading, newReadingState, evidenceParameters } from "../src/lib/reader-evidence.ts";

test("reading requires both foreground time and half of the text reached", () => {
  let state = newReadingState();
  for (let at = 0; at <= 90_000; at += 1000) state = advanceReading(state, at, true, 0.2);
  assert.equal(state.activeMs, 90_000);
  assert.equal(state.reached, false);
  state = advanceReading(state, 91_000, true, 0.5);
  assert.equal(state.reached, true);
  let scrolled = advanceReading(newReadingState(), 0, true, 1);
  scrolled = advanceReading(scrolled, 1000, true, 1);
  assert.equal(scrolled.reached, false);
});

test("hidden, unfocused or off-content time does not count; returning does not backfill it", () => {
  let state = advanceReading(newReadingState(), 0, true, 0.1);
  state = advanceReading(state, 1000, true, 0.1);
  state = advanceReading(state, 2000, false, 1);
  state = advanceReading(state, 602_000, false, 1);
  state = advanceReading(state, 603_000, true, 0.1);
  assert.equal(state.activeMs, 1000);
  assert.equal(state.progress, 0.1);
  assert.equal(state.reached, false);
});

test("a suspended timer cannot count a long gap as reading", () => {
  let state = advanceReading(newReadingState(), 0, true, 1);
  state = advanceReading(state, 600_000, true, 1);
  assert.equal(state.activeMs, 2000);
  assert.equal(state.reached, false);
});

test("event parameters bind role and answer to the same page and exclude query strings", () => {
  assert.deepEqual(evidenceParameters("translation", "/articles/example/?email=private#fragment", "quality", "useful"),
    { research_v1: { translation: { "/articles/example/": { quality: "useful" } } } });
  assert.deepEqual(evidenceParameters("collection", "/vypuski/listeriya/", "unexpected free text", "engaged"),
    { research_v1: { collection: { "/vypuski/listeriya/": { unspecified: "engaged" } } } });
});
