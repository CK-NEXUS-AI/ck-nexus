(() => {
  "use strict";

  const TRUTH_CLASSES = new Set(["OBSERVED", "INFERRED", "SIMULATED", "VERIFIED"]);
  const DEFAULT_MOTION = Object.freeze({
    locomotion: true,
    posture: true,
    gesture: true,
    face: true,
    gaze: true,
    microMotion: true,
  });

  function safeNow() {
    return typeof performance !== "undefined" && typeof performance.now === "function"
      ? performance.now()
      : Date.now();
  }

  function hasWebGL() {
    if (typeof document === "undefined") return false;
    try {
      const canvas = document.createElement("canvas");
      return Boolean(
        window.WebGL2RenderingContext && canvas.getContext("webgl2")
      ) || Boolean(
        window.WebGLRenderingContext && (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
      );
    } catch (_) {
      return false;
    }
  }

  function normalizeTruth(value) {
    const truth = String(value || "").toUpperCase();
    return TRUTH_CLASSES.has(truth) ? truth : null;
  }

  function clonePublicState(value) {
    if (!value || typeof value !== "object") return null;
    return JSON.parse(JSON.stringify(value));
  }

  function validateProjection(snapshot) {
    if (!snapshot || typeof snapshot !== "object") {
      return { ok: false, reason: "projection_missing" };
    }
    const truth = normalizeTruth(snapshot.truth_class || snapshot.truth);
    if (!truth) return { ok: false, reason: "truth_class_invalid" };
    if (snapshot.private_chain_of_thought || snapshot.raw_credentials) {
      return { ok: false, reason: "private_data_forbidden" };
    }
    return { ok: true, truth };
  }

  class CssFallbackDriver {
    constructor(sceneElement) {
      this.sceneElement = sceneElement;
      this.mode = "css-fallback";
      this.lastSnapshot = null;
    }

    mount() {
      if (this.sceneElement) this.sceneElement.dataset.renderer = this.mode;
      return { mode: this.mode, mounted: true };
    }

    project(snapshot) {
      this.lastSnapshot = clonePublicState(snapshot);
      if (this.sceneElement) {
        this.sceneElement.dataset.truth = normalizeTruth(snapshot.truth_class || snapshot.truth) || "INFERRED";
      }
      return { mode: this.mode, projected: true };
    }

    setMotion() {}
    setLod() {}
    pause() {}
    resume() {}
    dispose() {}
  }

  class ThreePresentationDriver {
    constructor(sceneElement, deps) {
      this.sceneElement = sceneElement;
      this.THREE = deps.THREE;
      this.GLTFLoader = deps.GLTFLoader || null;
      this.VRMLoaderPlugin = deps.VRMLoaderPlugin || null;
      this.mode = "three-presentation";
      this.renderer = null;
      this.scene = null;
      this.camera = null;
      this.frame = null;
      this.running = false;
      this.motion = { ...DEFAULT_MOTION };
      this.lod = "balanced";
      this.nodes = new Map();
      this.lastFrameAt = safeNow();
    }

    mount() {
      const THREE = this.THREE;
      const host = this.sceneElement;
      if (!host || !THREE || !hasWebGL()) throw new Error("three_runtime_unavailable");

      const canvas = document.createElement("canvas");
      canvas.className = "cognitive-twin-webgl";
      canvas.setAttribute("aria-hidden", "true");
      host.prepend(canvas);

      this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
      this.camera.position.set(0, 7, 13);
      this.camera.lookAt(0, 0, 0);

      const ambient = new THREE.HemisphereLight(0xffffff, 0x1b2230, 1.35);
      const key = new THREE.DirectionalLight(0xffffff, 1.25);
      key.position.set(4, 8, 5);
      this.scene.add(ambient, key);

      this._resize();
      this._onResize = () => this._resize();
      window.addEventListener("resize", this._onResize, { passive: true });
      host.dataset.renderer = this.mode;
      this.running = true;
      this._tick();
      return { mode: this.mode, mounted: true };
    }

    _resize() {
      if (!this.renderer || !this.camera || !this.sceneElement) return;
      const rect = this.sceneElement.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      this.renderer.setSize(width, height, false);
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
    }

    _ensureAgent(agent) {
      const THREE = this.THREE;
      const id = String(agent.agent_id || agent.id || "");
      if (!id) return null;
      if (this.nodes.has(id)) return this.nodes.get(id);

      const group = new THREE.Group();
      group.userData.agentId = id;
      const body = new THREE.Mesh(
        new THREE.CapsuleGeometry(0.28, 0.7, 6, 12),
        new THREE.MeshStandardMaterial({ color: 0x6bc7ff, roughness: 0.55, metalness: 0.15 })
      );
      body.position.y = 0.75;
      group.add(body);
      this.scene.add(group);
      this.nodes.set(id, group);
      return group;
    }

    _positionAgent(group, agent, index) {
      const p = agent.presentation || agent.position || {};
      const x = Number.isFinite(Number(p.x)) ? Number(p.x) : ((index % 4) - 1.5) * 2.2;
      const z = Number.isFinite(Number(p.z)) ? Number(p.z) : (Math.floor(index / 4) - 0.5) * 2.4;
      group.position.set(x, 0, z);
    }

    project(snapshot) {
      const agents = Array.isArray(snapshot.agents) ? snapshot.agents : [];
      const seen = new Set();
      agents.forEach((agent, index) => {
        const group = this._ensureAgent(agent);
        if (!group) return;
        seen.add(group.userData.agentId);
        this._positionAgent(group, agent, index);
        group.visible = agent.visible !== false;
        group.userData.truth = normalizeTruth(agent.truth_class || agent.truth || snapshot.truth_class || snapshot.truth);
        group.userData.operationalState = String(agent.operational_state || agent.state || "unknown");
      });
      this.nodes.forEach((node, id) => {
        if (!seen.has(id)) node.visible = false;
      });
      if (this.sceneElement) {
        this.sceneElement.dataset.truth = normalizeTruth(snapshot.truth_class || snapshot.truth) || "INFERRED";
      }
      return { mode: this.mode, projected: true, agents: seen.size };
    }

    setMotion(motion) {
      this.motion = { ...this.motion, ...(motion || {}) };
    }

    setLod(mode) {
      this.lod = ["performance", "balanced", "quality"].includes(mode) ? mode : "balanced";
      if (this.renderer) {
        const max = this.lod === "quality" ? 2 : this.lod === "performance" ? 1 : 1.5;
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, max));
      }
    }

    _tick() {
      if (!this.running || !this.renderer || !this.scene || !this.camera) return;
      const now = safeNow();
      const dt = Math.min(0.05, Math.max(0, (now - this.lastFrameAt) / 1000));
      this.lastFrameAt = now;
      if (this.motion.microMotion) {
        let motionIndex = 0;
        this.nodes.forEach((node) => {
          node.rotation.y += dt * (0.08 + (motionIndex % 3) * 0.02);
          motionIndex += 1;
        });
      }
      this.renderer.render(this.scene, this.camera);
      this.frame = window.requestAnimationFrame(() => this._tick());
    }

    pause() {
      this.running = false;
      if (this.frame) window.cancelAnimationFrame(this.frame);
      this.frame = null;
    }

    resume() {
      if (this.running) return;
      this.running = true;
      this.lastFrameAt = safeNow();
      this._tick();
    }

    dispose() {
      this.pause();
      if (this._onResize) window.removeEventListener("resize", this._onResize);
      this.nodes.forEach((node) => {
        node.traverse?.((child) => {
          child.geometry?.dispose?.();
          if (Array.isArray(child.material)) child.material.forEach((m) => m.dispose?.());
          else child.material?.dispose?.();
        });
      });
      this.nodes.clear();
      this.renderer?.dispose?.();
      this.renderer?.domElement?.remove?.();
      if (this.sceneElement) delete this.sceneElement.dataset.renderer;
    }
  }

  class CognitiveTwinRendererAdapter {
    constructor(options = {}) {
      this.sceneElement = options.sceneElement || document.getElementById("scene");
      this.truthPolicy = options.truthPolicy || "strict";
      this.driver = null;
      this.mode = "unmounted";
      this.lastAcceptedProjection = null;
      this.rejectedProjectionCount = 0;
      this._visibilityHandler = null;
    }

    mount() {
      const deps = {
        THREE: window.THREE,
        GLTFLoader: window.GLTFLoader,
        VRMLoaderPlugin: window.VRMLoaderPlugin,
      };
      try {
        this.driver = deps.THREE && hasWebGL()
          ? new ThreePresentationDriver(this.sceneElement, deps)
          : new CssFallbackDriver(this.sceneElement);
        const result = this.driver.mount();
        this.mode = result.mode;
      } catch (_) {
        this.driver?.dispose?.();
        this.driver = new CssFallbackDriver(this.sceneElement);
        const result = this.driver.mount();
        this.mode = result.mode;
      }

      this._visibilityHandler = () => {
        if (document.hidden) this.driver?.pause?.();
        else this.driver?.resume?.();
      };
      document.addEventListener("visibilitychange", this._visibilityHandler);
      return this.status();
    }

    project(snapshot) {
      const validation = validateProjection(snapshot);
      if (!validation.ok) {
        this.rejectedProjectionCount += 1;
        return { accepted: false, reason: validation.reason, mode: this.mode };
      }
      const safeSnapshot = clonePublicState(snapshot);
      safeSnapshot.truth_class = validation.truth;
      this.lastAcceptedProjection = safeSnapshot;
      const result = this.driver?.project?.(safeSnapshot) || { projected: false };
      return { accepted: true, truth_class: validation.truth, ...result };
    }

    setMotion(motion) {
      this.driver?.setMotion?.(motion);
    }

    setLod(mode) {
      this.driver?.setLod?.(mode);
    }

    status() {
      return {
        mode: this.mode,
        authority: "presentation-only",
        webgl: hasWebGL(),
        three_available: Boolean(window.THREE),
        vrm_plugin_available: Boolean(window.VRMLoaderPlugin),
        truth_policy: this.truthPolicy,
        rejected_projection_count: this.rejectedProjectionCount,
      };
    }

    dispose() {
      if (this._visibilityHandler) document.removeEventListener("visibilitychange", this._visibilityHandler);
      this._visibilityHandler = null;
      this.driver?.dispose?.();
      this.driver = null;
      this.mode = "disposed";
    }
  }

  window.CKNexusTwinRenderer = Object.freeze({
    create(options) {
      return new CognitiveTwinRendererAdapter(options);
    },
    validateProjection,
    truthClasses: Object.freeze([...TRUTH_CLASSES]),
  });
})();
