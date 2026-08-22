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
  const STATIC_ASSET_PREFIX = "/static/";
  const AVATAR_EXTENSIONS = /\.(?:vrm|glb|gltf)$/i;

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
    const three = window.THREE;
    return Boolean(
      three
      && typeof three.Scene === "function"
      && typeof three.PerspectiveCamera === "function"
      && typeof three.WebGLRenderer === "function"
    );
  }

  function gltfRuntimeAvailable() {
    return Boolean(threeRuntimeAvailable() && window.THREE.GLTFLoader);
  }

  function vrmRuntimeAvailable() {
    return Boolean(gltfRuntimeAvailable() && window.VRMLoaderPlugin);
  }

  function normalizeAssetUrl(value) {
    if (!value) throw new Error("avatar asset URL is required");
    const url = new URL(String(value), window.location.href);
    if (url.origin !== window.location.origin) {
      throw new Error("cross-origin avatar assets are denied");
    }
    if (!url.pathname.startsWith(STATIC_ASSET_PREFIX)) {
      throw new Error("avatar assets must be served from /static/");
    }
    if (!AVATAR_EXTENSIONS.test(url.pathname)) {
      throw new Error("avatar asset must be VRM, GLB, or GLTF");
    }
    return url.href;
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
      this.three = null;
      this.avatars = new Map();
      this.resizeObserver = null;
      this.frameHandle = null;
    }

    initialize() {
      if (!this.scene) return this.status("missing-scene");
      this.scene.dataset.renderer = "css-fallback";
      if (!webglAvailable()) return this.status("webgl-unavailable");
      if (!threeRuntimeAvailable()) return this.status("three-unavailable");

      try {
        this.initializeThreeScene();
      } catch (_) {
        this.disposeThreeScene();
        return this.status("three-init-failed");
      }

      this.mode = vrmRuntimeAvailable()
        ? "three-vrm"
        : gltfRuntimeAvailable() ? "three-gltf" : "three-basic";
      this.ready = true;
      this.scene.dataset.renderer = this.mode;
      this.startRenderLoop();
      return this.status("ready");
    }

    initializeThreeScene() {
      const THREE = window.THREE;
      const stage = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
      camera.position.set(0, 1.5, 4.5);

      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setPixelRatio(Math.min(Number(window.devicePixelRatio) || 1, 2));
      renderer.domElement.classList.add("cognitive-twin-webgl");
      renderer.domElement.setAttribute("aria-hidden", "true");
      renderer.domElement.style.position = "absolute";
      renderer.domElement.style.inset = "0";
      renderer.domElement.style.width = "100%";
      renderer.domElement.style.height = "100%";
      renderer.domElement.style.pointerEvents = "none";
      this.scene.prepend(renderer.domElement);

      this.three = { THREE, stage, camera, renderer };
      this.resize();
      if (typeof ResizeObserver === "function") {
        this.resizeObserver = new ResizeObserver(() => this.resize());
        this.resizeObserver.observe(this.scene);
      }
    }

    resize() {
      if (!this.three || !this.scene) return;
      const width = Math.max(1, this.scene.clientWidth || 1);
      const height = Math.max(1, this.scene.clientHeight || 1);
      this.three.camera.aspect = width / height;
      this.three.camera.updateProjectionMatrix();
      this.three.renderer.setSize(width, height, false);
    }

    startRenderLoop() {
      if (!this.three || this.frameHandle) return;
      const render = () => {
        this.frameHandle = null;
        if (!this.three) return;
        if (document.visibilityState !== "hidden") {
          this.three.renderer.render(this.three.stage, this.three.camera);
        }
        this.frameHandle = window.requestAnimationFrame(render);
      };
      this.frameHandle = window.requestAnimationFrame(render);
    }

    loadAvatar({ agentId, assetUrl }) {
      if (!this.three || !gltfRuntimeAvailable()) {
        return Promise.reject(new Error("GLTF runtime is unavailable"));
      }
      const id = String(agentId || "").trim();
      if (!id) return Promise.reject(new Error("agentId is required"));
      let url;
      try {
        url = normalizeAssetUrl(assetUrl);
      } catch (error) {
        return Promise.reject(error);
      }

      const loader = new window.THREE.GLTFLoader();
      if (/\.vrm(?:$|[?#])/i.test(url) && vrmRuntimeAvailable()) {
        loader.register((parser) => new window.VRMLoaderPlugin(parser));
      }
      return new Promise((resolve, reject) => {
        loader.load(
          url,
          (gltf) => {
            const vrm = gltf?.userData?.vrm || null;
            const root = vrm?.scene || gltf?.scene;
            if (!root) {
              reject(new Error("avatar scene is missing"));
              return;
            }
            const previous = this.avatars.get(id);
            if (previous?.root) this.three.stage.remove(previous.root);
            this.three.stage.add(root);
            const avatar = Object.freeze({ id, url, root, vrm, format: vrm ? "vrm" : "gltf" });
            this.avatars.set(id, avatar);
            resolve(avatar);
          },
          undefined,
          (error) => reject(error instanceof Error ? error : new Error("avatar load failed")),
        );
      });
    }

    applyProfileToAvatar(agentId, profile) {
      const avatar = this.avatars.get(agentId);
      if (!avatar?.root) return;
      avatar.root.rotation.y = Number(profile.gaze || 0) * 0.08;
      avatar.root.rotation.x = Number(profile.posture || 0) * -0.04;
      avatar.root.position.y = Number(profile.micro || 0) * 0.025;
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
      this.applyProfileToAvatar(state.agentId, profile);
      return this.lastState;
    }

    setReducedMotion(enabled) {
      this.reducedMotion = Boolean(enabled);
      if (this.lastState) return this.consume(this.lastState);
      return null;
    }

    disposeThreeScene() {
      if (this.frameHandle) {
        window.cancelAnimationFrame(this.frameHandle);
        this.frameHandle = null;
      }
      if (this.resizeObserver) {
        this.resizeObserver.disconnect();
        this.resizeObserver = null;
      }
      if (this.three?.renderer) {
        this.three.renderer.dispose();
        this.three.renderer.domElement?.remove();
      }
      this.three = null;
      this.avatars.clear();
      this.mode = "css-fallback";
      this.ready = false;
      if (this.scene) this.scene.dataset.renderer = this.mode;
    }

    status(reason = "unknown") {
      return Object.freeze({
        mode: this.mode,
        ready: this.ready,
        reason,
        webgl: webglAvailable(),
        three: threeRuntimeAvailable(),
        gltf: gltfRuntimeAvailable(),
        vrm: vrmRuntimeAvailable(),
        avatars: this.avatars.size,
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
    normalizeAssetUrl,
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
