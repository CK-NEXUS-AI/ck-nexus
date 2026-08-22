(() => {
  "use strict";

  const TRUTH = new Set(["OBSERVED", "INFERRED", "SIMULATED", "VERIFIED"]);
  const MOTION = new Set(["idle", "searching", "analyzing", "planning", "executing", "verifying", "waiting", "blocked", "evidence"]);

  function normalizeTruth(value) {
    const truth = String(value || "").toUpperCase();
    return TRUTH.has(truth) ? truth : "INFERRED";
  }

  function normalizeMotion(value) {
    const motion = String(value || "idle").toLowerCase();
    return MOTION.has(motion) ? motion : "idle";
  }

  function canUseWebGL(env = globalThis) {
    try {
      if (!env.document?.createElement) return false;
      const canvas = env.document.createElement("canvas");
      return Boolean(canvas.getContext?.("webgl2") || canvas.getContext?.("webgl"));
    } catch (_) {
      return false;
    }
  }

  function selectBackend(env = globalThis) {
    const webgl = canUseWebGL(env);
    const three = Boolean(env.THREE);
    const vrm = Boolean(env.THREE_VRM || env.VRMLoaderPlugin);
    if (webgl && three) return { mode: "THREE_WEBGL", webgl, three, vrm };
    return { mode: "CSS_FALLBACK", webgl, three, vrm };
  }

  function sanitizeAgent(agent) {
    if (!agent || typeof agent !== "object") return null;
    const id = String(agent.id || "").trim();
    if (!id) return null;
    return {
      id,
      truth: normalizeTruth(agent.truth),
      motion: normalizeMotion(agent.motion || agent.state),
      active: Boolean(agent.active),
      verified: normalizeTruth(agent.truth) === "VERIFIED",
      source: typeof agent.source === "string" ? agent.source : "runtime-projection",
    };
  }

  function sanitizeProjection(input) {
    if (!input || typeof input !== "object") return { subject: null, agents: [], truth: "INFERRED" };
    const agents = Array.isArray(input.agents) ? input.agents.map(sanitizeAgent).filter(Boolean) : [];
    return {
      subject: typeof input.subject === "string" ? input.subject : null,
      taskId: typeof input.task_id === "string" ? input.task_id : null,
      runId: typeof input.run_id === "string" ? input.run_id : null,
      truth: normalizeTruth(input.truth),
      agents,
    };
  }

  class CognitiveTwinRendererAdapter {
    constructor({ scene, env = globalThis } = {}) {
      if (!scene) throw new Error("renderer scene is required");
      this.scene = scene;
      this.env = env;
      this.backend = selectBackend(env);
      this.lod = "auto";
      this.motion = "full";
      this.lastProjection = null;
      this.destroyed = false;
      this.publishDiagnostics();
    }

    publishDiagnostics() {
      this.scene.dataset.rendererMode = this.backend.mode;
      this.scene.dataset.webgl = this.backend.webgl ? "available" : "unavailable";
      this.scene.dataset.three = this.backend.three ? "available" : "unavailable";
      this.scene.dataset.vrm = this.backend.vrm ? "available" : "unavailable";
    }

    setLod(value) {
      const lod = ["auto", "high", "medium", "low"].includes(value) ? value : "auto";
      this.lod = lod;
      this.scene.dataset.rendererLod = lod;
      return lod;
    }

    setMotionPolicy(value) {
      const motion = ["full", "balanced", "reduced"].includes(value) ? value : "full";
      this.motion = motion;
      this.scene.dataset.rendererMotion = motion;
      return motion;
    }

    applyProjection(input) {
      if (this.destroyed) throw new Error("renderer adapter is destroyed");
      const projection = sanitizeProjection(input);
      this.lastProjection = projection;
      if (projection.subject) this.scene.dataset.subject = projection.subject;
      this.scene.dataset.truth = projection.truth;
      projection.agents.forEach((agent) => {
        const node = this.scene.querySelector?.(`[data-agent="${agent.id}"]`);
        if (!node) return;
        node.dataset.truth = agent.truth;
        node.dataset.motion = agent.motion;
        node.dataset.active = agent.active ? "true" : "false";
        node.dataset.verified = agent.verified ? "true" : "false";
      });
      return projection;
    }

    diagnostics() {
      return {
        backend: { ...this.backend },
        lod: this.lod,
        motion: this.motion,
        subject: this.lastProjection?.subject || null,
        truth: this.lastProjection?.truth || null,
        destroyed: this.destroyed,
      };
    }

    destroy() {
      this.destroyed = true;
      delete this.scene.dataset.rendererMode;
      delete this.scene.dataset.rendererLod;
      delete this.scene.dataset.rendererMotion;
    }
  }

  const api = {
    CognitiveTwinRendererAdapter,
    normalizeTruth,
    normalizeMotion,
    sanitizeProjection,
    selectBackend,
  };

  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof globalThis !== "undefined") globalThis.CKNexusTwinRenderer = api;
})();
