# Tool 04 — Cline
Research date: 2026-10-25. Primary sources: https://github.com/cline/cline, https://github.com/cline/cline/blob/main/docs/getting-started/authorizing-with-cline.mdx, https://cline.bot/faq.

## 1. Identity
Cline is an open-source coding agent best known as a VS Code extension and also offers a CLI. The source repository is publicly available under Apache-2.0. It is active and supports a provider-based model architecture. Cline itself is the client/agent; hosted billing options are separate services, and using Cline does not imply model inference is free.

## 2. Category
AI-Assisted plus Task Agent. It can inspect files, plan, edit code, call tools and run terminal commands. It is not intrinsically a multi-agent orchestration framework or a self-evolving codebase.

## 3. Core Mechanism
Cline runs in the editor/CLI, calls a configured provider, and executes a tool-use loop over file operations, terminal commands, browser or MCP tools where configured. It supports user approval gates and configurable auto-approval. The project documentation says Cline asks for confirmation before changes unless auto-approve is enabled; the CLI currently documents tool calls as auto-approved by default in one invocation mode, with `--auto-approve false` to require review. This difference is important: defaults depend on client and configuration, so teams must explicitly set and test the approval mode rather than assume a safe default. Sources above.

## 4. Key Capabilities
- Multiple provider options: Cline's own usage-billing account, ClinePass, BYOK cloud APIs, and local runtimes such as Ollama/LM Studio.
- VS Code in-editor task execution with visible edits and tool actions.
- Terminal CLI for scripted use.
- MCP integration extends available tools.
- BYOK can send inference requests directly to the selected provider from the user's environment, reducing lock-in to a single model gateway.
- Team use cases include codebase changes, test generation, bug investigation, and repeatable tool-assisted workflows.

## 5. Evidence
Official repository and documentation support the provider options, approval controls, and supported workflows. No public independent benchmark was found in this pass that demonstrates Cline consistently outperforms commercial agents on the same tasks. Community metrics such as GitHub stars are snapshots, not quality or adoption evidence. For enterprise evaluation, use a representative issue set and measure task completion, review acceptance, security findings, tool-approval burden, and total model spend.

## 6. Limitations
An agent with terminal access can alter files, execute scripts and potentially exfiltrate repository content if granted network access and tricked by malicious instructions. Auto-approval materially expands this risk. BYOK shifts credential management to the user's environment; keys must not be embedded in prompts or committed to the repository. Free/local models may be slow or underperform on complex code tasks. Cline's client being open-source does not make model providers, hosted billing, or all extensions open-source. MCP tools expand capabilities but also expand the trust boundary.

## 7. Cost & Access
The client is free/open-source. Options include direct provider API billing, local inference without a cloud API key, Cline's usage-based billing with free model options, or ClinePass at $9.99/month according to the current official provider setup guide. Prices, free-model availability and bundled usage can change; source: https://github.com/cline/cline/blob/main/docs/getting-started/authorizing-with-cline.mdx. Install the VS Code extension or official CLI. The client can run locally, but cloud inference still needs provider authentication or an account; self-hosting the client is not the same as self-hosting a frontier model.

## 8. Comparison
Compared with Aider, Cline provides a richer in-editor tool loop and approval UI; Aider has a simpler Git-native terminal workflow. Compared with Cursor, Cline offers more open client code and provider freedom, while Cursor packages editor, indexing and hosted background-agent experience more tightly. Compare real spend and approval settings rather than just subscription price.

## 9. Verdict
Good for developers who want an interactive agent in VS Code, provider flexibility and a visible tool-approval workflow. Suitable for teams that can standardize configuration and enforce repository policy. Not suitable for unattended production changes with default permissions or shared long-lived credentials. For CK-NEXUS, run Cline only in a sandbox/worktree, explicitly disable unsafe auto-approval for privileged commands, restrict network and secrets, and require CI plus independent review.

## Evidence gaps
No public evidence found here for a guaranteed bug-fix success rate or a current independent productivity ranking. Approval behavior should be verified against the exact extension/CLI version deployed.
