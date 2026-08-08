# Minimalist Typography & Motion Design System

## Product principle

CK-NEXUS Creator Edition uses words, weight, spacing, and motion as the primary interface language. The interface does not depend on icon fonts, emoji, external font CDNs, or decorative three-dimensional assets.

## 1. Typography and grid

- Display type uses a fluid `clamp()` scale and a system serif stack.
- Interface and Thai body copy use local system sans-serif fonts.
- Critical information uses bold weight; normal content uses regular weight; secondary/completed information uses light italic treatment.
- Runtime state is always written explicitly, for example `[ DEMO LINKED ]`, `[ LIVE LINKED ]`, and `[ LIVE DISCONNECTED ]`.
- Disconnected states use restrained blur and lower opacity in addition to wording, so color is never the only signal.
- The desktop workspace uses an asymmetric specialist/brief grid and collapses to one column on smaller screens.

## 2. Motion language

- Main headings enter through a masked reveal; the system eyebrow uses a short typing reveal.
- Magnetic hover uses a small pointer-relative translation and a spring-like easing curve.
- The background mesh moves slowly and receives a subtle pointer parallax offset.
- View changes use a short fade-and-rise transition.
- Metric values use a cubic-eased number ticker driven by real API/history values.
- `prefers-reduced-motion: reduce` disables motion, parallax, and magnetic transforms.

## 3. Functional control hub

- `WORKSPACE`: direct specialist selection, structured creative brief, generated output, copy, and text-file export.
- `STREAM`: live runtime mode, model name, specialist count, session run count, and recent outputs.
- `SYSTEM`: theme selection, connection matrix, session-token control, local-session deletion, and an honest feature blueprint.
- `Ctrl/Cmd + K`: text-only command palette for navigation, focus, refresh, and theme commands.
- Access Gate: requests the configured CK-NEXUS bearer token and keeps it in browser session storage only. It is not a simulated username/password system.

## 4. Environment themes

- `Deep Midnight`: `#0F172A` with muted purple depth.
- `Clean Alabaster`: `#F8FAFC` and `#F1F5F9` with dark typography.
- `Cyber Aurora`: deep emerald/cyan with restrained luminous accents.
- Without a stored preference, the initial theme follows local time: Alabaster by day, Aurora near evening, and Midnight at night.
- A manual choice persists in local browser storage.

## Accessibility and security notes

- Keyboard focus is visible and the command palette supports Enter/Escape.
- Text state supplements theme color; output is inserted with `textContent`, never interpreted as HTML.
- No third-party frontend request is required to render the interface.
- The full File Depot, multi-user identity, and external publishing remain roadmap items and are labelled as such in the UI.

