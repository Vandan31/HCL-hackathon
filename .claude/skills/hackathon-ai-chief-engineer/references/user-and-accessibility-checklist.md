# User and accessibility checklist

Map four audiences: 1) primary front-line user, 2) administrator/operator, 3) economic buyer/sponsor, 4) underserved or edge-case user. One person may have multiple roles.

Capture: goal; current workaround; frequency; friction; device; literacy; location/bandwidth; permissions; sensitive data; success definition; objection to adopting new product.

Accessibility: keyboard navigation, readable text/contrast, labels & screen reader semantics, captions/transcripts for audio, speech optional not mandatory, clear error messages, plain language, motor/visual/hearing constraints; at least one accessible fallback.

Localization: prioritize user's language, allow correction of machine translation/ASR, avoid enforcing English-only prompts. Never promise coverage of every language without tests.

Connectivity: retry/idempotency, loading feedback, compressed images, text-only route, offline capture/queue or asynchronous processing when feasible.

Trust: user understands when AI is involved; show sources/confidence where appropriate; request consent when required; minimal personal data, short retention, role-based access and auditability.

Measure UX: task completion rate, median and p95 time to complete, correction frequency, abandonment, accessibility task success, subgroup-specific outcomes. Do not invent measured results.
