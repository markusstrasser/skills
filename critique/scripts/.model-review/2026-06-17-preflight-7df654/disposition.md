# Review Findings — 2026-06-17

**44 findings** from 4 axes (9 cross-model agreements)
Structured data: `findings.json`

1. **[CRITICAL]** Dynamic scripts lack host execution sandboxing **[CROSS-MODEL: also Gemini B (full review — coverage + assumptions), Gemini A (full review — structure + correctness), Gemini A (full review — structure + correctness), Gemini A (full review — structure + correctness), Gemini A (full review — structure + correctness)]**
   Category: security | Confidence: 1.0 | Source: Gemini B (full review — coverage + assumptions)
   The review states that the scripts directory is under a local user profile (`/Users/alien/...`) and warns that dynamically generated agent scripts may be run directly on the host without Docker, gVisor, or other sandbox boundaries. Evidence cited includes risks of host compromise, recursive deletes, and local resource exhaustion.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Execute generated scripts only inside a restricted sandbox/container with constrained filesystem, CPU, memory, network, and process permissions.

---

2. **[HIGH]** Script boundaries lack schema enforcement **[CROSS-MODEL: also Gemini A (full review — structure + correctness)]**
   Category: missing | Confidence: 1.0 | Source: Gemini B (full review — coverage + assumptions)
   The review identifies the absence of input parameter validation schemas and output contracts. It gives examples of argument drift such as `--file`, `-f`, or positional arguments, which could cause parsing failures during multi-agent orchestration.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Define strict input and output schemas using Pydantic, JSON Schema, or an equivalent contract system, and validate all script invocations against them.

---

3. **[MEDIUM]** Runtime and interpreter versions are not pinned **[CROSS-MODEL: also Gemini B (full review — coverage + assumptions)]**
   Category: architecture | Confidence: 1.0 | Source: Gemini B (full review — coverage + assumptions)
   The review says the blank scripts directory lacks an explicit execution contract such as `.tool-versions`, `pyproject.toml`, or `package.json`. As a result, different agents may write scripts for incompatible Python, Node.js, Bash, or system dependency versions.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Add a project-level runtime contract that pins supported runtimes, dependency versions, and invocation conventions.

---

4. **[MEDIUM]** No standardized script error semantics **[CROSS-MODEL: also Gemini B (full review — coverage + assumptions), Gemini A (full review — structure + correctness)]**
   Category: missing | Confidence: 1.0 | Source: Gemini B (full review — coverage + assumptions)
   The review flags inconsistent error-state semantics: one script may return exit code 0 on logical failure while printing errors to stdout, while another may return exit code 1 with structured JSON on stderr. This prevents a uniform retry and error-handling policy.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Define a standard failure contract covering exit codes, stdout/stderr usage, machine-readable error fields, and retryability classification.

---

5. **[MEDIUM]** Hung scripts may leak processes and file descriptors **[CROSS-MODEL: also Gemini A (full review — structure + correctness), Gemini A (full review — structure + correctness)]**
   Category: performance | Confidence: 1.0 | Source: Gemini B (full review — coverage + assumptions)
   The review warns that hung scripts may leak system processes or file descriptors if the orchestrator cannot recover cleanly from execution hangs.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Ensure the supervisor kills entire process groups, closes file descriptors, reaps child processes, and cleans temporary resources on timeout or crash.

---

6. **[MEDIUM]** Concurrent script execution may cause race conditions **[CROSS-MODEL: also Gemini A (full review — structure + correctness)]**
   Category: bug | Confidence: 1.0 | Source: Gemini B (full review — coverage + assumptions)
   The review claims the environment appears to assume scripts will not be executed concurrently. If two agents trigger validation scripts simultaneously and the scripts write shared state or temp files without locking, file corruption and race conditions may occur.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Make script execution concurrency-safe by using per-invocation workspaces, unique temp paths, file locking where shared resources are unavoidable, and transactional writes.

---

7. **[MEDIUM]** Adopt a structured command registry framework **[CROSS-MODEL: also Gemini A (full review — structure + correctness)]**
   Category: architecture | Confidence: 0.9 | Source: Gemini A (full review — structure + correctness)
   The review recommends replacing raw scripts with a Command Registry Framework executed inside an isolated runner. The proposed structure includes `.runner/`, `schema/`, and `commands/` directories with commands subclassing a common base interface.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Create a command registry with a central CLI/entrypoint, registered command modules, and shared schema definitions.

---

8. **[MEDIUM]** Scripts assume unrestricted network access **[CROSS-MODEL: also Gemini A (full review — structure + correctness)]**
   Category: architecture | Confidence: 0.9 | Source: Gemini B (full review — coverage + assumptions)
   The review flags an implicit assumption of unrestricted outbound network access for fetching external critique datasets, models, or APIs. This can fail in offline, air-gapped, or restricted-network runtimes.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Declare network requirements explicitly, provide offline fallbacks or cached fixtures, and enforce network policy through the runner or sandbox.

---

9. **[MEDIUM]** Missing structured execution output and observability **[CROSS-MODEL: also Gemini A (full review — structure + correctness)]**
   Category: missing | Confidence: 0.9 | Source: Gemini A (full review — structure + correctness)
   The review states that raw scripts usually emit unstructured text to stdout/stderr and lack a machine-readable validation interface for run status, modified entities, and performance metrics.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Require structured JSON output schemas for all commands, including success status, mutations, errors, metrics, and trace metadata.

---

10. **[CRITICAL]** Complete absence of reviewable artifacts
   Category: missing | Confidence: 1.0 | Source: GPT-5.5 medium A (full review — bugs + structure)
   No implementation, diff, plan, contract, or migration artifact was provided for review. The only provided artifact is /dev/null with empty contents, making any specific claim of correctness impossible.
   File: /dev/null
   Fix: Supply the actual diff, relevant files, interface definitions, and expected behavior invariants.

---

11. **[HIGH]** Process risk due to empty review handoff
   Category: principles | Confidence: 1.0 | Source: GPT-5.5 medium A (full review — bugs + structure)
   The current process allows review requests without sufficient state to validate correctness, which risks creating false confidence where a review passes simply because there is nothing to inspect.
   File: 
   Fix: Enforce a requirement for a minimum reviewable packet before initiating the review process.

---

12. **[HIGH]** Missing boundary and trust model
   Category: architecture | Confidence: 1.0 | Source: GPT-5.5 medium A (full review — bugs + structure)
   There is no information about trust boundaries, filesystem/network/process boundaries, schema boundaries, or API contracts to evaluate potential security or stability risks.
   File: 
   Fix: Provide a boundary model describing interactions and trust assumptions.

---

13. **[HIGH]** Undefined invariants and error semantics
   Category: logic | Confidence: 1.0 | Source: GPT-5.5 medium A (full review — bugs + structure)
   The review packet lacks any description of what the subpart is supposed to guarantee, what inputs it accepts, and what failure modes are acceptable.
   File: 
   Fix: Document functional invariants and error handling expectations.

---

14. **[HIGH]** Unverifiable migration and compatibility model
   Category: logic | Confidence: 1.0 | Source: GPT-5.5 medium A (full review — bugs + structure)
   No evidence was provided regarding how new behavior coexists with old systems, how consumers migrate, or how versioning is handled.
   File: 
   Fix: Include a migration plan and compatibility assessment for existing consumers.

---

15. **[HIGH]** Absence of interface artifacts for architectural review
   Category: missing | Confidence: 1.0 | Source: GPT-5.5 medium B (full review — migration + interfaces)
   The review package lacks schemas, function signatures, API shapes, config keys, and environment variables, making it impossible to evaluate contract stability or identify breaks.
   File: /dev/null
   Fix: Include a list of externally callable APIs, internal module boundaries, input/output schemas, and config changes.

---

16. **[HIGH]** Missing migration and deletion plan
   Category: missing | Confidence: 1.0 | Source: GPT-5.5 medium B (full review — migration + interfaces)
   No identification of old/new paths, dual-read/write behavior, compatibility windows, or cleanup conditions were provided for behavior replacement.
   File: 
   Fix: Document the migration lifecycle including bridge layers, compatibility expectations, and deletion triggers for old code.

---

17. **[HIGH]** No timeout or crash-loop mitigation for script execution
   Category: missing | Confidence: 0.9 | Source: Gemini B (full review — coverage + assumptions)
   The review states that there is no supervisor layer enforcing timeouts. It warns that scripts entering infinite loops, waiting on lock files, or blocking on network sockets could hang the agent pipeline indefinitely, increasing compute cost and stalling execution.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Run scripts under a supervisor that enforces wall-clock timeouts, kills process trees, cleans up resources, and reports timeout failures in a structured format.

---

18. **[HIGH]** No centralized execution and trace harness
   Category: missing | Confidence: 0.9 | Source: Gemini B (full review — coverage + assumptions)
   The review claims there is no centralized entry point or runner script to capture stdout, stderr, execution duration, memory consumption, and exit codes. Without this telemetry, agents cannot reliably debug script failures or produce structured execution traces.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Introduce a single execution harness/runner that wraps all script execution and records stdout, stderr, duration, memory usage, exit code, and structured trace metadata.

---

19. **[HIGH]** No manifest-driven type-safe runner to limit blast radius
   Category: architecture | Confidence: 0.8 | Source: Gemini B (full review — coverage + assumptions)
   The review recommends avoiding raw shell or Python scripts and instead using a single robust, type-safe runner that accepts a declarative JSON/YAML manifest. The stated goal is to reduce blast radius so agent mistakes become schema validation failures rather than arbitrary host execution failures.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Implement a single manifest-driven runner in a robust typed language or strictly typed Python, with schema validation before any task execution.

---

20. **[HIGH]** Missing static-analysis guard rails for risky script operations
   Category: security | Confidence: 0.7 | Source: Gemini A (full review — structure + correctness)
   The review recommends guard rails via pre-commit or pre-execution hooks using Ruff, Bandit, and Semgrep to detect high-risk operations such as `os.system()` and `subprocess.Popen(shell=True)` before execution.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Add linting/static-analysis checks to CI and the runner’s pre-execution path, failing commands that violate safety rules.

---

21. **[HIGH]** Scripts may bypass application boundaries and invariants
   Category: logic | Confidence: 0.6 | Source: Gemini A (full review — structure + correctness)
   The review claims scripts typically import internals or directly manipulate raw databases/datastores, bypassing application invariants, hooks, event listeners, and audit logs. It warns this can cause silent database corruption or inconsistent state.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Route mutations through application services/APIs where possible, or enforce command-level invariants, audit logging, and transactional validation.

---

22. **[HIGH]** Missing network isolation for script execution
   Category: security | Confidence: 0.6 | Source: Gemini A (full review — structure + correctness)
   The review states that no network isolation exists unless explicitly configured through sandboxing. This leaves scripts able to reach external services or internal networks by default.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Apply default-deny network policies in the runner and allowlist required endpoints per command.

---

23. **[HIGH]** Scripts may have unsafe access to production or staging databases
   Category: security | Confidence: 0.6 | Source: Gemini A (full review — structure + correctness)
   The review’s assumptions state that the host machine running scripts may have access to production or staging databases. Combined with direct script execution, this creates risk of accidental production mutations.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Add environment targeting controls, explicit production confirmation gates, least-privilege credentials, dry-run defaults, and audit logging.

---

24. **[MEDIUM]** Absence of observability contract
   Category: missing | Confidence: 1.0 | Source: GPT-5.5 medium A (full review — bugs + structure)
   There is no evidence that failures are surfaced, logged, counted, or traced, which is essential for operational maintenance.
   File: 
   Fix: Define an observability contract ensuring failures are actionable.

---

25. **[MEDIUM]** High risk of implicit contract drift in AI-developed systems
   Category: architecture | Confidence: 0.9 | Source: GPT-5.5 medium B (full review — migration + interfaces)
   Relying on implicit context allows future agents to incorrectly infer behavior from implementation details rather than declared boundaries, leading to accidental API drift.
   File: 
   Fix: Declare explicit public vs internal boundaries and use schema/version declarations over ad hoc shape changes.

---

26. **[MEDIUM]** Undefined error handling and failure contracts
   Category: missing | Confidence: 0.9 | Source: GPT-5.5 medium B (full review — migration + interfaces)
   The interface fails to distinguish between caller and system faults, specify if failures are raised or returned, or define idempotency and partial success states.
   File: 
   Fix: Define a robust error contract that specifies failure modes, retry behavior, and structured error objects.

---

27. **[MEDIUM]** Potential for boundary integration failures despite passing unit tests
   Category: logic | Confidence: 0.8 | Source: GPT-5.5 medium B (full review — migration + interfaces)
   Without verified agreements on required fields, defaults, and encoding between producers and consumers, bugs may exist at the integration layer.
   File: 
   Fix: Implement fail-fast validation at boundaries and tests that exercise producer/consumer integration.

---

28. **[MEDIUM]** Free-form agent scripts create excessive maintenance burden
   Category: architecture | Confidence: 0.8 | Source: Gemini B (full review — coverage + assumptions)
   The review argues that allowing agents to write arbitrary free-form utility scripts directly into `skills/critique/scripts` creates an unmanageable maintenance burden and increases human supervision cost.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Replace arbitrary imperative scripts with a declarative tool configuration model where possible, reviewed and validated against a stable schema.

---

29. **[MEDIUM]** Raw stderr output is not structured or bounded
   Category: missing | Confidence: 0.8 | Source: Gemini B (full review — coverage + assumptions)
   The review notes that raw multi-line stderr output and deep interpreter stack traces may flood the LLM context window and be difficult for upstream orchestrators to parse.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Require structured JSON error output with concise summaries, bounded stack traces, error codes, and optional links or artifacts for full logs.

---

30. **[MEDIUM]** Script shebangs may drift across incompatible interpreters
   Category: bug | Confidence: 0.8 | Source: Gemini B (full review — coverage + assumptions)
   The review warns that generated scripts may use inconsistent shebangs, such as `#!/usr/bin/env python3` versus absolute interpreter paths that may not exist on the runner. This can cause scripts to fail on different machines or CI environments.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Standardize script invocation through the runner instead of relying on per-script shebangs, or enforce portable shebang rules in a lint/validation step.

---

31. **[MEDIUM]** Script execution assumes local environment parity
   Category: architecture | Confidence: 0.7 | Source: Gemini B (full review — coverage + assumptions)
   The review identifies an assumption that the target runtime has the same OS utilities, paths, and library versions as the agent development context. This can break execution when local and CI/production environments differ.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Define reproducible environments using containers, lockfiles, pinned tool versions, and CI checks that validate scripts in the target runtime.

---

32. **[MEDIUM]** Missing enforced dry-run mode for mutating scripts
   Category: missing | Confidence: 0.7 | Source: Gemini A (full review — structure + correctness)
   The review recommends enforcing a mandatory `--dry-run` capability through the `BaseCommand` interface. State-mutating steps should be skipped and logged during verification phases.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Add a required `dry_run` field/flag and require mutating commands to report proposed changes without applying them.

---

33. **[MEDIUM]** No isolated dependency environment for script runtimes
   Category: missing | Confidence: 0.7 | Source: Gemini B (full review — coverage + assumptions)
   The review states that Python and Node.js runtimes are assumed to be preconfigured on the host and do not require virtual environment isolation. This can lead to dependency collisions and non-reproducible executions.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Use isolated per-project or per-run environments such as virtualenv/uv, npm lockfiles, or containers, and install dependencies from locked manifests.

---

34. **[MEDIUM]** Unstructured scripts directory creates architectural drift risk
   Category: architecture | Confidence: 0.7 | Source: Gemini A (full review — structure + correctness)
   The review flags `/Users/alien/Projects/skills/critique/scripts` as an unstructured scripts directory. It claims that, in an environment where code generation is cheap but maintenance and drift are costly, unconstrained ad-hoc scripts become an architectural liability because there is no centralized framework or runtime harness.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Replace the free-form scripts directory with a structured command registry and centralized runner/harness.

---

35. **[MEDIUM]** Scripts may rely on macOS-specific tooling assumptions
   Category: architecture | Confidence: 0.7 | Source: Gemini B (full review — coverage + assumptions)
   The review notes a macOS-looking path (`/Users/alien/...`) and warns that scripts using macOS/BSD-specific utilities such as BSD `sed`, `awk`, or `find` behavior may break in Linux CI or production environments.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Avoid platform-specific shell assumptions, use portable language libraries where possible, and test scripts in the same Linux/container runtime used by automation.

---

36. **[MEDIUM]** Legacy scripts need adapter-based migration path
   Category: architecture | Confidence: 0.7 | Source: Gemini A (full review — structure + correctness)
   The review recommends a compatibility layer for migrating legacy automations. The runner should wrap old scripts with an adapter pattern, catch standard exceptions, and coerce output into the structured schema.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Implement legacy adapters that invoke existing scripts under the runner, normalize stdout/stderr/errors, and gradually migrate scripts to native commands.

---

37. **[MEDIUM]** Dry-run behavior should be idempotent and mutation-free
   Category: logic | Confidence: 0.7 | Source: Gemini A (full review — structure + correctness)
   The review recommends that dry-run execution return the exact changes that would occur without applying them to the datastore. This implies current scripts may not provide reliable idempotent previews of mutations.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Require write commands to calculate and return planned mutations, and add tests proving dry-run mode leaves datastores unchanged.

---

38. **[MEDIUM]** JIT-generated scripts would amplify sandboxing and timeout risks
   Category: architecture | Confidence: 0.6 | Source: Gemini B (full review — coverage + assumptions)
   The review identifies a possible JIT script-generation model and says that if scripts are generated just-in-time rather than committed, static schema files may not exist while sandboxing and timeout risks become more severe.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: If scripts are generated JIT, validate generated code/manifests before execution and enforce sandboxing, timeouts, and resource limits at generation-time and run-time.

---

39. **[MEDIUM]** User-specific absolute path creates portability fragility
   Category: bug | Confidence: 0.6 | Source: Gemini A (full review — structure + correctness)
   The review claims the hard-coded/localized path `/Users/alien` creates fragility across different execution environments and assumes the path will remain consistent.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Use repository-relative paths, configuration variables, or container workspace paths instead of relying on user-specific absolute paths.

---

40. **[MEDIUM]** Missing checks for git-tracked file modifications
   Category: missing | Confidence: 0.6 | Source: Gemini A (full review — structure + correctness)
   The review states there are no safety checks ensuring files modified by scripts are tracked. It claims changes could bypass git and cause drift between local state and the remote source of truth.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Require commands that modify repository files to report changed paths, verify git status, and fail or warn on untracked/uncommitted drift.

---

41. **[MEDIUM]** Scripts may report success despite internal failures
   Category: bug | Confidence: 0.6 | Source: Gemini A (full review — structure + correctness)
   The review claims many scripts exit with code `0` even when internal processes fail, creating silent success assumptions. It argues a standard runner is needed to guarantee exit-code compliance.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Centralize exception handling and process execution in the runner, mapping validation/runtime failures to non-zero exit codes and structured error payloads.

---

42. **[MEDIUM]** Brittle sys.path injection can break imports
   Category: bug | Confidence: 0.5 | Source: Gemini A (full review — structure + correctness)
   The review identifies brittle path-resolution patterns such as `sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`. It claims these can fail when the working directory or execution context changes, causing silent import mistakes or unhandled `ModuleNotFoundError` exceptions.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Package shared code properly, use project-relative imports through an installed package, and execute commands via a stable runner entrypoint.

---

43. **[MEDIUM]** Sandbox design depends on unspecified Docker availability
   Category: architecture | Confidence: 0.5 | Source: Gemini A (full review — structure + correctness)
   The review assumes Docker is available and notes that if the workstation is locked down or lacks virtualization, the proposed sandbox strategy may not work.
   File: /Users/alien/Projects/skills/critique/scripts
   Fix: Document host requirements and provide fallback isolation options such as rootless containers, chroot, gVisor, or a remote runner.

---

44. **[LOW]** Lack of explicit deletion gates for compatibility shims
   Category: principles | Confidence: 0.8 | Source: GPT-5.5 medium B (full review — migration + interfaces)
   The absence of clear ownership and removal conditions for legacy paths increases future maintenance burden and agent inference errors.
   File: 
   Fix: Establish explicit removal conditions and deletion gates for all compatibility helpers and legacy code paths.

---

## Agent Response (fill before implementing)

### Where I disagree with the disposition:
<!-- "Nowhere" is valid. Don't invent disagreements. -->


### Context I had that the models didn't:
<!-- If context file was comprehensive, say so. -->

