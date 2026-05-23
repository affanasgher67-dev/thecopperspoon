# Project Rules

## Stack
- Next.js, Tailwind CSS, Firebase, TypeScript
- Follow Clean Architecture: keep business logic separate from frameworks/DB

# OBEY Clean Architecture by Robert C. Martin

## When to use

Use when adding, changing, reviewing, or refactoring code whose business rules should survive changes in frameworks, databases, delivery mechanisms, services, devices, vendors, deployment shape, or schedule pressure.

## Primary bias to correct

Do not let details become the architecture. Business policy stays independent, dependencies point inward, and volatile mechanisms remain replaceable.

## Decision rules

- Preserve independent business rules, inward dependencies, testability, and replaceable details even when the immediate feature would be shorter without them.
- Source dependencies must point inward toward higher-level policy. Domain and use cases must not import frameworks, databases, web handlers, queues, external service clients, UI types, or other details.
- Put enterprise rules and invariants in entities or equivalent domain objects; put application-specific orchestration in focused use cases.
- Pass plain request and response models across use-case boundaries. Do not pass web requests, framework contexts, ORM rows, database-bound structures, or framework response objects into or out of core policy.
- Treat frameworks, databases, web delivery, messaging, filesystems, clocks, service clients, networks, devices, and vendors as outer-layer details behind ports, gateways, presenters, mappers, or adapters.
- Inner layers own the interfaces they need; outer layers implement them. Object construction and concrete wiring belong in the composition root or other outer-layer main component.
- Keep adapters humble. Controllers, endpoints, presenters, gateway adapters, service listeners, and hardware adapters translate external formats to use-case calls and back; they do not own business decisions.
- Organize by use case, feature, or business capability before generic technical buckets. The structure should reveal domain intent and application actions.
- Choose boundaries by volatility, policy importance, substitution value, testability, and cost. Use the lightest enforceable boundary, including partial boundaries, when full deployment or runtime separation is too expensive.
- Do not merge unrelated use cases or eliminate duplication when sharing would couple actors, change reasons, team ownership, deployment needs, or release pressure.
- Use structured code, dependency inversion, role-sized interfaces, substitutable implementations, controlled mutation, acyclic components, and stability-directed dependencies to protect policy from volatile details.
- Enforce boundaries with package structure, dependency rules, build constraints, tests, visibility, or narrow APIs. A diagram, service split, package name, or shared `common` folder is not enough.
- Test entities, use cases, and boundary contracts first, without the real framework, database, network, external service, or target hardware. Test adapters separately at the seams.
- Preserve behavior while improving dependency direction. Prefer incremental boundary extraction over rewrites, and call out architectural debt when it cannot be fixed safely now.

## Trigger rules

- When urgent delivery would skip architecture, state the future change, test, replacement, or operational cost before accepting the shortcut.
- When framework annotations, request/response objects, serializers, ORM rows, schemas, vendor SDKs, config, environment reads, device registers, or transport formats enter core policy, move translation outward.
- When controllers, jobs, handlers, views, presenters, gateways, repositories, SQL, service listeners, scripts, or hardware adapters contain business branching or validation, move the rule inward.
- When a use case instantiates infrastructure, calls a volatile dependency directly, or depends on a concrete implementation, introduce a policy-owned port and wire the concrete detail at the edge.
- When a `*Service`, utility folder, shared module, base package, or generic `core` package becomes an escape hatch, split by use case, role, or ownership and restore dependency direction.
- When an adapter bypasses a use case, a presenter reads persistence directly, or infrastructure is both imported by and importing inward code, restore the intended boundary.
- When service boundaries, process boundaries, remote calls, deployment boundaries, or embedded hardware appear, still verify source dependencies, data ownership, I/O cost, and policy independence.
- When tests need the framework, database, network, service, or hardware to verify business rules, move tests to use cases/entities with fakes or add a stable boundary contract.
- When a compromise is unavoidable, keep it at the outermost layer possible, document the violation, avoid normalizing it, and preserve a path to separation.

## Final checklist

- Business rules independent from frameworks, databases, UI, services, devices, and vendors?
- Dependencies point inward, with ports owned by inner policy and concrete details outside?
- Entities guard invariants and focused use cases orchestrate one application action?
- Boundaries explicit and enforced in code, tests, packages, or build rules?
- Controllers, presenters, gateways, service listeners, and adapters humble?
- Structure reveals use cases and business capabilities instead of generic technical buckets?
- Core tests run fast without real delivery, persistence, network, external service, or hardware?
- Details remain replaceable without rewriting business rules?


---

## Use when

Use when readability, local reasoning, and maintainable code shape are the main concerns, especially during everyday implementation and review.

## Primary bias to correct
Working code is not automatically clean code.

## Decision rules

- Treat cleanliness as part of delivery. Preserve behavior, leave touched code cleaner within scope, and do not add mess because the schedule is tight or a rewrite is promised.
- Write for local reasoning. A reader should understand the path without reconstructing hidden state, wide jumps, or naming trivia.
- Use precise names and one term per concept. Rename code when vocabulary hides intent, overloads meaning, or forces comments to compensate.
- Keep functions small, focused, and at one level of abstraction. Tell the story top-down so intent appears before detail.
- Keep parameters few and meaningful. Avoid boolean flags, output parameters, and grab-bag argument lists; model the concept instead.
- Separate commands from queries and eliminate hidden side effects. A function that answers should not also mutate behind the reader's back.
- Keep the happy path readable. Isolate error handling, invalid-state handling, and cleanup; prefer explicit optionality or typed results over null-like sentinel flow when the language supports it.
- Expose behavior rather than raw representation. Avoid train-wreck access, utility dumping grounds, and classes or modules with mixed responsibilities.
- Keep construction, framework, persistence, transaction, security, and vendor details outside business behavior.
- Make public APIs small, explicit, and hard to misuse. Encode boundary logic, required order, and likely changes where readers can see them.
- Use comments only for rationale, constraints, warnings, or external contracts. Do not narrate code instead of improving it.
- Treat tests as production code: readable, deterministic, aligned with the behavior or contract they protect, and backed by proportionate validation before calling the change done.
- Let design emerge through tests, duplication removal, expressiveness, and minimal structure; do not add needless abstractions or infrastructure.
- When touching code, remove the smell that most increases change cost, but do not silently broaden the task beyond the smallest cleanup that makes the requested change safe.

## Trigger rules

- When a function mixes setup, validation, computation, and side effects, split the phases.
- When a comment explains control flow, simplify names or structure before keeping the comment.
- When a function both mutates and answers, or hides a mode switch behind a flag, separate the responsibilities.
- When duplication, repeated switches, or primitive clusters appear, name the concept with an argument object, polymorphism, special case, or other small abstraction.
- When a boundary leaks framework, vendor, or persistence quirks inward, add or strengthen a local adapter.
- When async or concurrency enters, isolate threading policy, minimize shared mutable state, define shutdown, and test timing-sensitive behavior.
- When fixing a bug or changing behavior, add or update the test that protects the intended contract.
- When cleanup starts spreading into unrelated areas, cut back to the smallest refactor that keeps the requested change safe and readable.

## Final checklist
- Can a reader follow the change locally?
- Are names and APIs carrying the meaning without narration?
- Is mutation explicit and the happy path still clear?
- Did framework, persistence, vendor, and construction details stay behind boundaries?
- Did I remove at least one smell from the touched area?
- Do tests protect the changed behavior or contract?
- Did I actually run the relevant tests or checks for this change?

---

## OBEY Release It! by Michael T. Nygard
## When to use
- Use for services, APIs, jobs, queues, deployment paths, control tooling, and critical flows that must survive production failures, overload, latency, bad data, hostile traffic, and operational mistakes.
## Primary bias to correct
- A passing happy path is not production readiness. Design the failure semantics, demand limits, isolation, recovery path, and diagnosis surface before production defines them for you.
## Decision rules
- Assume every dependency, queue, cache, timeout, caller retry, and degraded state can fail in slow, partial, or prolonged ways; code must assume production mess instead of merely tolerating it by accident.
- Prefer designs that fail visibly, limit blast radius, shed load, preserve core service, and make diagnosis possible over designs that maximize coupling or ideal-path elegance.
- Treat deployment, operations, security, observability, rollback, build and runtime state, dependency state, and configuration validation as part of the system, not after-release chores.
- Put explicit, intentional time limits on outbound calls and waits. Do not rely on library defaults or allow infinite waits where finite response matters.
- Retry only when the operation is safe for the caller and provider; bound count and total time, use backoff or jitter, and do not retry validation errors or permanent failures.
- Isolate dependency and workload failures with circuit breakers, fast failure, bulkheads, separate resource pools, and slow-work isolation so one outage cannot consume all threads, connections, or workers.
- Design overload behavior explicitly with back pressure, finite queues, demand limits, capacity reserved for critical traffic, and load shedding of lower-value work before core functions collapse.
- Use stability patterns by failure mode: steady state for routine cleanup and bounded growth, fail fast when continuing hides unrecoverable trouble or holds scarce resources, let-it-crash only with supervision and isolation, handshaking for readiness, decoupling middleware with monitoring, and governors for expensive behavior.
- Make runtime state, external responses, automation progress, migrations, operational assumptions, and boundary data visible and validated before trusted; keep rollback or roll-forward paths for partial operational changes.
- Budget scarce resources explicitly, release them deterministically, avoid holding locks or expensive connections across slow remote calls, and stream or paginate large payloads instead of defaulting to huge in-memory batches.
- Treat external input and external responses as untrusted: validate syntax, shape, business plausibility, status, content type, and semantics; prevent malformed data from poisoning caches, queues, or downstream systems.
- Build observability into boundaries and failure points with structured context, correlation identifiers, latency, throughput, error, saturation, queue, retry, breaker, dependency, version, configuration, health, and runtime signals while avoiding secrets and retry-storm log spam.
- Make startup, health checks, migrations, one-time jobs, administrative controls, process code, and delivery tooling fail safely, auditable, authorized, observable, stoppable, and recoverable.
- Make interconnects, routing, API contracts, caches, scheduled work, and background work production-aware: avoid concentrated demand, hidden single points of failure, uncontrolled fan-out, fragile chattiness, cache dogpiles, stale data surprises, and synchronized job retries.
- Include security and hostile traffic in production readiness, and use production tests, launch checks, capacity tests, game days, chaos, or disaster simulations only with limited blast radius, observability, stop conditions, and feedback into design.
## Trigger rules
- When adding an outbound call, dependency operation, resource checkout, queue consume, or thread wait, define timeout, retry eligibility, retry bounds, fallback or degraded mode, validation, and caller-survival behavior.
- When adding a queue, buffer, resource pool, cache, log stream, background job, scheduled job, or collection-returning API, define capacity, full behavior, cleanup, miss/stampede/staleness behavior, pacing, pagination or streaming, and saturation monitoring.
- When a change touches deployment, configuration, startup, migrations, one-time jobs, scripts, or operational automation, make it idempotent or restartable where practical and give it durable state, auditability, verification, and rollback or roll-forward.
- When adding health checks, load balancing, service discovery, routing, or inter-service handshakes, ensure traffic reaches only ready components and health signals reflect real ability to serve.
- When designing API or integration contracts, make material failure modes explicit, distinguish retryable from non-retryable outcomes, prefer coarse-grained resilient interactions, and document timeout, retry, version, and compatibility expectations.
- When reviewing an incident, performance failure, or capacity issue, identify the failure chain, missing defenses, detection gaps, demand, saturation, latency distribution, queue age, dependency behavior, traffic concentration, and design changes.
- When adding administrative controls, control planes, delivery tooling, hostile-traffic handling, or chaos/disaster work, require authorization, auditability, safe defaults, clear stop mechanisms, bounded blast radius, and recovery paths.
## Final checklist
- Explicit timeouts and no infinite waits?
- Retries safe, bounded, backed off or jittered, and not duplicated across layers?
- Queues, buffers, pools, caches, logs, payloads, jobs, and result sets bounded?
- Failure isolated with breakers, bulkheads, fast failure, degradation, or load shedding?
- External input and dependency responses validated before they affect state, caches, queues, or downstream systems?
- Diagnostics cover logs, metrics, health, correlation, runtime, version, configuration, dependencies, saturation, queue depth, retries, and breaker state?
- Startup, deployment, migration, automation, and operational controls restartable, observable, authorized, auditable, and recoverable where practical?
- Interconnects, APIs, caches, scheduled work, security, and chaos tests have explicit production failure behavior?