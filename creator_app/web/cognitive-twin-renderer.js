(() => {
  "use strict";

  const VALID_TRUTH = new Set(["OBSERVED", "INFERRED", "SIMULATED", "VERIFIED"]);
  const ACTIVE_TRUTH = new Set(["OBSERVED", "VERIFIED"]);
  const STATE_COLORS = {
    idle: [0.42, 0.58, 0.68],
    searching: [0.22, 0.84, 1.0],
    analyzing: [0.66, 0.52, 1.0],
    planning: [0.66, 0.52, 1.0],
    executing: [0.29, 0.62, 1.0],
    verifying: [0.94, 0.77, 0.42],
    waiting: [1.0, 0.76, 0.36],
    blocked: [1.0, 0.42, 0.42],
    evidence: [0.27, 0.90, 0.61],
    success: [0.27, 0.90, 0.61],
  };

  const AGENT_POINTS = {
    agnes: [-0.05, 0.02],
    strategos: [-0.40, -0.02],
    scout: [-0.72, -0.28],
    verifier: [0.43, -0.02],
    guardian: [0.72, -0.30],
    builder: [0.22, -0.48],
  };

  const ZONES = {
    research: [0.15, 0.19],
    analysis: [0.42, 0.18],
    core: [0.49, 0.47],
    sandbox: [0.68, 0.20],
    security: [0.89, 0.22],
    evidence: [0.88, 0.73],
  };

  const STATE_ZONE = {
    searching: "research",
    analyzing: "analysis",
    planning: "core",
    executing: "sandbox",
    verifying: "evidence",
    blocked: "security",
    evidence: "evidence",
    success: "core",
  };

  function normalizeTruth(value) {
    const truth = String(value || "INFERRED").toUpperCase();
    return VALID_TRUTH.has(truth) ? truth : "INFERRED";
  }

  function normalizeState(value) {
    const state = String(value || "idle").toLowerCase();
    if (state.includes("search") || state.includes("research")) return "searching";
    if (state.includes("analy")) return "analyzing";
    if (state.includes("plan")) return "planning";
    if (state.includes("verify") || state.includes("review")) return "verifying";
    if (state.includes("run") || state.includes("execut") || state.includes("work")) return "executing";
    if (state.includes("block") || state.includes("deny") || state.includes("error")) return "blocked";
    if (state.includes("evidence") || state.includes("seal")) return "evidence";
    if (state.includes("success") || state.includes("complete")) return "success";
    if (state.includes("wait") || state.includes("approval")) return "waiting";
    return STATE_COLORS[state] ? state : "idle";
  }

  class SemanticMotionController {
    constructor(scene) {
      this.scene = scene;
      this.nodes = new Map();
      this.baseCenters = new Map();
      this.semantic = true;
      this.motionQuality = "full";
      document.querySelectorAll(".agent[data-agent]").forEach((node) => {
        this.nodes.set(node.dataset.agent, node);
      });
      this.measure();
      window.addEventListener("resize", () => this.measure());
    }

    measure() {
      const sceneRect = this.scene.getBoundingClientRect();
      this.nodes.forEach((node, id) => {
        node.style.translate = "0px 0px";
        const rect = node.getBoundingClientRect();
        this.baseCenters.set(id, {
          x: rect.left - sceneRect.left + rect.width / 2,
          y: rect.top - sceneRect.top + rect.height / 2,
        });
      });
    }

    configure({ semantic = true, motionQuality = "full" } = {}) {
      this.semantic = Boolean(semantic);
      this.motionQuality = motionQuality;
      if (!this.semantic || this.motionQuality === "reduced") {
        this.nodes.forEach((node) => {
          node.style.translate = "0px 0px";
          node.dataset.motionState = "rest";
        });
      }
    }

    apply(agentId, rawState, rawTruth) {
      const node = this.nodes.get(agentId);
      if (!node) return;
      const state = normalizeState(rawState);
      const truth = normalizeTruth(rawTruth);
      node.dataset.truth = truth;
      node.dataset.motionState = state;

      if (!this.semantic || this.motionQuality === "reduced" || !ACTIVE_TRUTH.has(truth)) {
        node.style.translate = "0px 0px";
        return;
      }

      const zone = ZONES[STATE_ZONE[state]];
      const base = this.baseCenters.get(agentId);
      if (!zone || !base || !this.scene.clientWidth || !this.scene.clientHeight) {
        node.style.translate = "0px 0px";
        return;
      }

      const targetX = zone[0] * this.scene.clientWidth;
      const targetY = zone[1] * this.scene.clientHeight;
      const dx = Math.max(-220, Math.min(220, targetX - base.x));
      const dy = Math.max(-150, Math.min(150, targetY - base.y));
      node.style.translate = `${dx.toFixed(1)}px ${dy.toFixed(1)}px`;
    }
  }

  class WebGLTwinRenderer {
    constructor(canvas, statusNode) {
      this.canvas = canvas;
      this.statusNode = statusNode;
      this.gl = null;
      this.program = null;
      this.positionBuffer = null;
      this.colorBuffer = null;
      this.agentStates = new Map();
      this.running = false;
      this.paused = false;
      this.mode = "auto";
      this.frameCap = 45;
      this.lastFrame = 0;
      this.pointSize = 18;
      this.boundFrame = (time) => this.frame(time);
    }

    setStatus(label, state = "ok") {
      if (!this.statusNode) return;
      this.statusNode.textContent = label;
      this.statusNode.dataset.state = state;
    }

    init() {
      if (!this.canvas) return false;
      const options = {
        alpha: true,
        antialias: true,
        premultipliedAlpha: false,
        powerPreference: "high-performance",
      };
      const gl = this.canvas.getContext("webgl2", options) || this.canvas.getContext("webgl", options);
      if (!gl) {
        this.setStatus("DOM FALLBACK", "fallback");
        this.canvas.hidden = true;
        return false;
      }
      this.gl = gl;
      this.program = this.createProgram();
      if (!this.program) {
        this.setStatus("DOM FALLBACK", "fallback");
        this.canvas.hidden = true;
        return false;
      }
      this.positionBuffer = gl.createBuffer();
      this.colorBuffer = gl.createBuffer();
      this.resize();
      window.addEventListener("resize", () => this.resize());
      this.setStatus(window.WebGL2RenderingContext && gl instanceof WebGL2RenderingContext ? "WEBGL2 ACTIVE" : "WEBGL ACTIVE");
      this.running = true;
      window.requestAnimationFrame(this.boundFrame);
      return true;
    }

    createShader(type, source) {
      const gl = this.gl;
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    }

    createProgram() {
      const gl = this.gl;
      const vertex = this.createShader(gl.VERTEX_SHADER, `
        attribute vec2 a_position;
        attribute vec3 a_color;
        varying vec3 v_color;
        uniform float u_point_size;
        void main() {
          gl_Position = vec4(a_position, 0.0, 1.0);
          gl_PointSize = u_point_size;
          v_color = a_color;
        }
      `);
      const fragment = this.createShader(gl.FRAGMENT_SHADER, `
        precision mediump float;
        varying vec3 v_color;
        void main() {
          vec2 p = gl_PointCoord * 2.0 - 1.0;
          float r2 = dot(p, p);
          if (r2 > 1.0) discard;
          float glow = smoothstep(1.0, 0.0, r2);
          gl_FragColor = vec4(v_color, 0.18 + glow * 0.62);
        }
      `);
      if (!vertex || !fragment) return null;
      const program = gl.createProgram();
      gl.attachShader(program, vertex);
      gl.attachShader(program, fragment);
      gl.linkProgram(program);
      gl.deleteShader(vertex);
      gl.deleteShader(fragment);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        gl.deleteProgram(program);
        return null;
      }
      return program;
    }

    configure({ mode = "auto", frameCap = 45, lodMode = "auto" } = {}) {
      this.mode = mode;
      this.frameCap = Number(frameCap) || 45;
      this.pointSize = lodMode === "low" ? 12 : lodMode === "medium" ? 15 : 18;
      if (mode === "dom") {
        this.canvas.hidden = true;
        this.setStatus("DOM ONLY", "fallback");
      } else if (this.gl) {
        this.canvas.hidden = false;
        this.setStatus(window.WebGL2RenderingContext && this.gl instanceof WebGL2RenderingContext ? "WEBGL2 ACTIVE" : "WEBGL ACTIVE");
      }
    }

    setPaused(value) {
      this.paused = Boolean(value);
    }

    update(agentId, rawState, rawTruth) {
      if (!AGENT_POINTS[agentId]) return;
      this.agentStates.set(agentId, {
        state: normalizeState(rawState),
        truth: normalizeTruth(rawTruth),
      });
    }

    resize() {
      if (!this.gl || !this.canvas) return;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = Math.max(1, Math.floor(this.canvas.clientWidth * dpr));
      const height = Math.max(1, Math.floor(this.canvas.clientHeight * dpr));
      if (this.canvas.width !== width || this.canvas.height !== height) {
        this.canvas.width = width;
        this.canvas.height = height;
      }
      this.gl.viewport(0, 0, width, height);
    }

    frame(time) {
      if (!this.running) return;
      window.requestAnimationFrame(this.boundFrame);
      if (this.paused || this.canvas.hidden || !this.gl) return;
      const interval = 1000 / Math.max(12, this.frameCap);
      if (time - this.lastFrame < interval) return;
      this.lastFrame = time;
      this.draw(time);
    }

    draw(time) {
      const gl = this.gl;
      const ids = Object.keys(AGENT_POINTS);
      const positions = [];
      const colors = [];
      ids.forEach((id, index) => {
        const point = AGENT_POINTS[id];
        const status = this.agentStates.get(id) || { state: "idle", truth: "INFERRED" };
        const pulse = status.truth === "VERIFIED" ? Math.sin(time / 620 + index) * 0.012 : 0;
        positions.push(point[0], point[1] + pulse);
        const color = STATE_COLORS[status.state] || STATE_COLORS.idle;
        const dim = status.truth === "SIMULATED" ? 0.48 : status.truth === "INFERRED" ? 0.68 : 1;
        colors.push(color[0] * dim, color[1] * dim, color[2] * dim);
      });

      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.useProgram(this.program);

      const positionLoc = gl.getAttribLocation(this.program, "a_position");
      gl.bindBuffer(gl.ARRAY_BUFFER, this.positionBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(positionLoc);
      gl.vertexAttribPointer(positionLoc, 2, gl.FLOAT, false, 0, 0);

      const colorLoc = gl.getAttribLocation(this.program, "a_color");
      gl.bindBuffer(gl.ARRAY_BUFFER, this.colorBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(colors), gl.DYNAMIC_DRAW);
      gl.enableVertexAttribArray(colorLoc);
      gl.vertexAttribPointer(colorLoc, 3, gl.FLOAT, false, 0, 0);

      const pointSizeLoc = gl.getUniformLocation(this.program, "u_point_size");
      gl.uniform1f(pointSizeLoc, this.pointSize * Math.min(window.devicePixelRatio || 1, 2));
      gl.drawArrays(gl.POINTS, 0, ids.length);
    }
  }

  class TwinRendererController {
    constructor({ scene, canvas, statusNode }) {
      this.scene = scene;
      this.motion = new SemanticMotionController(scene);
      this.webgl = new WebGLTwinRenderer(canvas, statusNode);
      this.initialized = false;
    }

    init() {
      if (this.initialized) return this;
      this.initialized = true;
      this.webgl.init();
      window.addEventListener("cknexus:projection", (event) => {
        this.applyProjection(event.detail);
      });
      return this;
    }

    configure(settings = {}) {
      this.motion.configure({
        semantic: settings.semanticMotion,
        motionQuality: settings.motionQuality,
      });
      this.webgl.configure({
        mode: settings.rendererMode,
        frameCap: settings.frameCap,
        lodMode: settings.lodMode,
      });
    }

    setPaused(value) {
      this.webgl.setPaused(value);
    }

    applyAgentState(agentId, state, truth = "INFERRED") {
      const normalizedTruth = normalizeTruth(truth);
      this.motion.apply(agentId, state, normalizedTruth);
      this.webgl.update(agentId, state, normalizedTruth);
    }

    applyProjection(projection) {
      if (!projection || typeof projection !== "object") return;
      const agents = Array.isArray(projection.agents) ? projection.agents : [];
      agents.forEach((agent) => {
        if (!agent || !agent.agent_id) return;
        this.applyAgentState(
          String(agent.agent_id).toLowerCase(),
          agent.public_state || agent.state || "idle",
          agent.truth || projection.truth || "INFERRED",
        );
      });
    }
  }

  window.CKNexusTwinRenderer = {
    create(options) {
      return new TwinRendererController(options).init();
    },
    normalizeState,
    normalizeTruth,
  };
})();