(() => {
  "use strict";

  const TRUTH_CLASSES = new Set(["OBSERVED", "INFERRED", "SIMULATED", "VERIFIED"]);
  const MOTION_STATES = new Set([
    "searching",
    "analyzing",
    "planning",
    "executing",
    "verifying",
    "waiting",
    "blocked",
    "evidence",
  ]);
  const PROJECTION_EVENT = "cknexus:projected-state";

  function webglAvailable() {
    try {
      const canvas = document.createElement("canvas");
      return Boolean(
        window.WebGL2RenderingContext && canvas.getContext("webgl2")
          || window.WebGLRenderingContext && canvas.getContext("webgl")
      );
    } catch (_) {
      return false;
    }
  }

  function threeRuntimeAvailable() {
    return Boolean(window.THREE && typeof window.THREE.Scene === "function");
  }

  function vrmRuntimeAvailable() {
    return Boolean(
      threeRuntimeAvailable()
      && window.THREE.GLTFLoader
      && window.VRMLoaderPlugin
    );
  }

  function normalizeTruth(value) {
    const truth = String(value || "INFERRED").toUpperCase();
    return TRUTH_CLASSES.has(truth) ? truth : "INFERRED";
  }

  function normalizeMotion(value) {
    const state = String(value || "waiting").toLowerCase();
    return MOTION_STATES.has(state) ? state : "waiting";
  }

  function normalizeProjectedState(projected) {
    const input = projected && typeof projected === "object" ? projected : {};
    return Object.freeze({
      agentId: String(input.agent_id || input.agentId || "unknown"),
      motion: normalizeMotion(input.motion || input.visual_state || input.state),
      truth: normalizeTruth(input.truth_class || input.truth),
      verified: input.verified === true,
      blocked: input.blocked === true,
      evidenceId: input.evidence_id ? String(input.evidence_id) : null,
      timestamp: input.timestamp ? String(input.timestamp) : null,
    });
  }

  function safeTruthForPresentation(state) {
    if (state.truth === "VERIFIED" && !state.verified) return "OBSERVED";
    return state.truth;
  }

  function motionProfile(state, reducedMotion) {
    if (reducedMotion) {
      return { locomotion: 0, posture: 0, gesture: 0, face: 0, gaze: 0, micro: 0 };
    }
    if (state.blocked || state.motion === "blocked") {
      return { locomotion: 0, posture: -0.35, gesture: 0, face: -0.5, gaze: 0.1, micro: 0.1 };
    }
    const profiles = {
      searching: { locomotion: 0.55, posture: 0.15, gesture: 0.25, face: 0.1, gaze: 0.8, micro: 0.35 },
      analyzing: { locomotion: 0.1, posture: 0.2, gesture: 0.15, face: 0.25, gaze: 0.6, micro: 0.3 },
      planning: { locomotion: 0.05, posture: 0.3, gesture: 0.3, face: 0.2, gaze: 0.55, micro: 0.3 },
      executing: { locomotion: 0.7, posture: 0.45, gesture: 0.5, face: 0.2, gaze: 0.7, micro: 0.4 },
      verifying: { locomotion: 0.05, posture: 0.4, gesture: 0.1, face: 0.35, gaze: 0.9, micro: 0.2 },
      waiting: { locomotion: 0, posture: 0, gesture: 0, face: 0, gaze: 0.25, micro: 0.2 },
      evidence: { locomotion: 0.05, posture: 0.35, gesture: 0.15, face: 0.25, gaze: 0.75, micro: 0.2 },
    };
    return profiles[state.motion] || profiles.waiting;
  }

  class CognitiveTwinRenderer {
    constructor({ scene, reducedMotion = false } = {}) {
      this.scene = scene || document.getElementById("scene");
      this.reducedMotion = Boolean(reducedMotion);
      this.mode = "css-fallback";
      this.ready = false;
      this.lastState = null;
    }

    initialize() {
      if (!this.scene) return this.status("missing-scene");
      this.scene.dataset.renderer = "css-fallback";
      if (!webglAvailable()) return this.status("webgl-unavailable");
      if (!threeRuntimeAvailable()) return this.status("three-unavailable");

      this.mode = vrmRuntimeAvailable() ? "three-vrm" : "three-basic";
      this.ready = true;
      this.scene.dataset.renderer = this.mode;
      return this.status("ready");
    }

    consume(projectedState) {
      const state = normalizeProjectedState(projectedState);
      const truth = safeTruthForPresentation(state);
      const profile = motionProfile(state, this.reducedMotion);
      this.lastState = Object.freeze({ ...state, truth, profile });

      if (this.scene) {
        this.scene.dataset.projectedAgent = state.agentId;
        this.scene.dataset.projectedMotion = state.motion;
        this.scene.dataset.projectedTruth = truth;
        this.scene.dataset.projectedVerified = String(Boolean(state.verified));
      }
      return this.lastState;
    }

    setReducedMotion(enabled) {
      this.reducedMotion = Boolean(enabled);
      if (this.lastState) return this.consume(this.lastState);
      return null;
    }

    status(reason = "unknown") {
      return Object.freeze({
        mode: this.mode,
        ready: this.ready,
        reason,
        webgl: webglAvailable(),
        three: threeRuntimeAvailable(),
        vrm: vrmRuntimeAvailable(),
      });
    }
  }

  function mountProjectionBridge() {
    const scene = document.getElementById("scene");
    if (!scene) return null;
    const renderer = new CognitiveTwinRenderer({
      scene,
      reducedMotion: window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true,
    });
    renderer.initialize();
    window.addEventListener(PROJECTION_EVENT, (event) => {
      renderer.consume(event && event.detail);
    });
    return renderer;
  }

  const publicApi = {
    create(options) {
      return new CognitiveTwinRenderer(options);
    },
    normalizeProjectedState,
    motionProfile,
    projectionEvent: PROJECTION_EVENT,
    truthClasses: Object.freeze(Array.from(TRUTH_CLASSES)),
    active: null,
  };
  window.CKNexusTwinRenderer = publicApi;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      publicApi.active = mountProjectionBridge();
    }, { once: true });
  } else {
    publicApi.active = mountProjectionBridge();
  }
})();
