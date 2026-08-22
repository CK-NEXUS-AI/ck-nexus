"use strict";

const assert = require("assert");
const renderer = require("../../creator_app/web/cognitive-twin-renderer.js");

function fakeScene() {
  const agents = new Map();
  return {
    dataset: {},
    agents,
    querySelector(selector) {
      const match = selector.match(/data-agent="([^"]+)"/);
      if (!match) return null;
      if (!agents.has(match[1])) agents.set(match[1], { dataset: {} });
      return agents.get(match[1]);
    },
  };
}

assert.equal(renderer.normalizeTruth("verified"), "VERIFIED");
assert.equal(renderer.normalizeTruth("secret"), "INFERRED");
assert.equal(renderer.normalizeMotion("executing"), "executing");
assert.equal(renderer.normalizeMotion("private_reasoning"), "idle");

const fallbackEnv = { document: { createElement: () => ({ getContext: () => null }) } };
assert.equal(renderer.selectBackend(fallbackEnv).mode, "CSS_FALLBACK");

const threeEnv = {
  THREE: {},
  document: { createElement: () => ({ getContext: (kind) => kind === "webgl2" ? {} : null }) },
};
assert.equal(renderer.selectBackend(threeEnv).mode, "THREE_WEBGL");

const scene = fakeScene();
const adapter = new renderer.CognitiveTwinRendererAdapter({ scene, env: fallbackEnv });
assert.equal(scene.dataset.rendererMode, "CSS_FALLBACK");
assert.equal(adapter.setLod("medium"), "medium");
assert.equal(adapter.setLod("invalid"), "auto");
assert.equal(adapter.setMotionPolicy("reduced"), "reduced");

const projection = adapter.applyProjection({
  subject: "subject-sha",
  truth: "observed",
  task_id: "task-1",
  run_id: "run-1",
  agents: [
    { id: "agnes", truth: "verified", motion: "verifying", active: true },
    { id: "builder", truth: "made-up", motion: "private_reasoning", active: false },
    { truth: "OBSERVED" },
  ],
});
assert.equal(projection.truth, "OBSERVED");
assert.equal(projection.agents.length, 2);
assert.equal(scene.agents.get("agnes").dataset.verified, "true");
assert.equal(scene.agents.get("builder").dataset.truth, "INFERRED");
assert.equal(scene.agents.get("builder").dataset.motion, "idle");
assert.equal(adapter.diagnostics().subject, "subject-sha");

adapter.destroy();
assert.equal(adapter.diagnostics().destroyed, true);
assert.throws(() => adapter.applyProjection({}), /destroyed/);
console.log("cognitive-twin-renderer: PASS");
