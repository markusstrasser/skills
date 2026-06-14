<!-- Reference file for modal skill. Loaded on demand. -->

# Scaling Out on Modal

## Automatic Autoscaling

Every Modal Function corresponds to an autoscaling pool of containers. Modal's autoscaler:
- Spins up containers when no capacity available
- Spins down containers when resources idle
- Scales to zero by default when no inputs to process

Autoscaling decisions are made quickly and frequently.

## Parallel Execution with `.map()`

Run function repeatedly with different inputs in parallel:

```python
@app.function()
def evaluate_model(x):
    return x ** 2

@app.local_entrypoint()
def main():
    inputs = list(range(100))
    # Runs 100 inputs in parallel across containers
    for result in evaluate_model.map(inputs):
        print(result)
```

### Multiple Arguments with `.starmap()`

For functions with multiple arguments:

```python
@app.function()
def add(a, b):
    return a + b

@app.local_entrypoint()
def main():
    results = list(add.starmap([(1, 2), (3, 4)]))
    # [3, 7]
```

### Exception Handling

```python
@app.function()
def may_fail(a):
    if a == 2:
        raise Exception("error")
    return a ** 2

@app.local_entrypoint()
def main():
    # v1.4+: exceptions come through as-is (wrap_returned_exceptions removed)
    results = list(may_fail.map(
        range(3),
        return_exceptions=True,
    ))
    # [0, 1, Exception('error')]
```

## Autoscaling Configuration

Configure autoscaler behavior with parameters:

```python
@app.function(
    max_containers=100,      # Upper limit on containers
    min_containers=2,        # Keep warm even when inactive
    buffer_containers=5,     # Maintain buffer while active
    scaledown_window=60,     # Max idle time before scaling down (seconds)
)
def my_function():
    ...
```

Parameters:
- **max_containers**: Upper limit on total containers
- **min_containers**: Minimum kept warm even when inactive
- **buffer_containers**: Buffer size while function active (additional inputs won't need to queue)
- **scaledown_window**: Maximum idle duration before scale down (seconds)

Trade-offs:
- Larger warm pool/buffer → Higher cost, lower latency
- Longer scaledown window → Less churn for infrequent requests

## Dynamic Autoscaler Updates

Update autoscaler settings without redeployment:

```python
f = modal.Function.from_name("my-app", "f")
f.update_autoscaler(max_containers=100)
```

Settings revert to decorator configuration on next deploy, or are overridden by further updates:

```python
f.update_autoscaler(min_containers=2, max_containers=10)
f.update_autoscaler(min_containers=4)  # max_containers=10 still in effect
```

### Time-Based Scaling

Adjust warm pool based on time of day:

```python
@app.function()
def inference_server():
    ...

@app.function(schedule=modal.Cron("0 6 * * *", timezone="America/New_York"))
def increase_warm_pool():
    inference_server.update_autoscaler(min_containers=4)

@app.function(schedule=modal.Cron("0 22 * * *", timezone="America/New_York"))
def decrease_warm_pool():
    inference_server.update_autoscaler(min_containers=0)
```

### For Classes

Update autoscaler for specific parameter instances:

```python
MyClass = modal.Cls.from_name("my-app", "MyClass")
obj = MyClass(model_version="3.5")
obj.update_autoscaler(buffer_containers=2)  # type: ignore
```

## Input Concurrency

Process multiple inputs per container with `@modal.concurrent`:

```python
@app.function()
@modal.concurrent(max_inputs=100)
def my_function(input: str):
    # Container can handle up to 100 concurrent inputs
    ...
```

Ideal for I/O-bound workloads:
- Database queries
- External API requests
- Remote Modal Function calls

### Concurrency Mechanisms

**Synchronous Functions**: Separate threads (must be thread-safe)

```python
@app.function()
@modal.concurrent(max_inputs=10)
def sync_function():
    time.sleep(1)  # Must be thread-safe
```

**Async Functions**: Separate asyncio tasks (must not block event loop)

```python
@app.function()
@modal.concurrent(max_inputs=10)
async def async_function():
    await asyncio.sleep(1)  # Must not block event loop
```

### Target vs Max Inputs

```python
@app.function()
@modal.concurrent(
    max_inputs=120,    # Hard limit
    target_inputs=100  # Autoscaler target
)
def my_function(input: str):
    # Allow 20% burst above target
    ...
```

Autoscaler aims for `target_inputs`, but containers can burst to `max_inputs` during scale-up.

## Scaling Limits

Modal enforces limits per function:
- 2,000 pending inputs (not yet assigned to containers)
- 25,000 total inputs (running + pending)

For `.spawn()` async jobs: up to 1 million pending inputs.

Exceeding limits returns `Resource Exhausted` error - retry later.

Each `.map()` invocation: max 1,000 concurrent inputs.

## Sizing & Extrapolating Fanouts

### Chunk size = preemption-loss budget
Chunk size bounds what a single preemption / budget-kill / timeout destroys on
a `.map()`/`.starmap()` fanout. Lose a chunk, redo a chunk.

| Chunks | Per-chunk runtime | Preempt loss | Scheduling   | Orch overhead |
|--------|-------------------|--------------|--------------|---------------|
| 6      | ~5h               | up to 5h     | hard at 48GB | light         |
| 60     | ~30min            | up to 30min  | easier       | heavier       |
| 200    | ~10min            | up to 10min  | easiest      | heavy         |

Default aim: **~30 min runtime per chunk.** For an algorithm with a fixed memory
floor (e.g. a 25-30GB aligner index), shrink chunks AND cap parallelism via
`.map(max_concurrent=N)` — chunk size alone won't ease scheduling when every
container still needs the full memory floor. The `.SUCCESS` sentinel only earns
its keep when a chunk is short enough to retry cheaply (<1.5h). (Evidence: a
5h×30GB chunk design lost ~$10 to one Modal infra event; a 60×3GB design would
have lost <$1.)

### Extrapolating wall-clock from a probe — watch for regime transitions
Two measured points do NOT prove the function is linear between them. A
single-item or small-N probe systematically *under*-predicts at scale:
1. **One-time costs baked into per-item time** (reference/index load, first cold
   start) inflate the per-item figure a 1-item probe reports.
2. **Quota-saturation regime transition.** At small N relative to the workspace
   concurrency cap, all workers start near-simultaneously → observed rate ≈
   serial × cap. At large N the scheduling queue sits deep and cold-start + wave
   overhead dominate → rate collapses toward serial. Super-linear wall-clock is
   the baseline expectation at scale, not an anomaly.

Evidence: an annotate stage ran 50 min at n=5000 (50 chunks / 10-concurrent cap
= 5 waves) but **9h at n=15000** (150 chunks / same cap = 15 waves) — 10.8×
wall-clock for 3× input. A separate batch predicted 1.5-2h from a 1-trait probe,
actually ran ~8.7h for 208 traits, and a 4h timeout killed it at 95/208.

**Before firing a larger scale:**
- Check whether either probe point saturated the workspace GPU/CPU concurrency
  cap (log `list_apps` / observed concurrency during the small probe).
- If projected `queue_depth / cap` > ~2×, expect a different regime — surface the
  ceiling explicitly *before* spending, don't learn the boundary by burning money.
- Size the timeout for projected full-scale runtime, not probe runtime (see
  debugging.md "Timeout Sizing" for the extrapolation formula).

Other regime transitions to watch: a memory cliff when an intermediate array
grows past L3/driver RAM; volume-commit throughput when commit frequency exceeds
the NFS flush budget; Flex→Standard billing-tier transitions.

## Async Usage

Use async APIs for arbitrary parallel execution patterns:

```python
@app.function()
async def async_task(x):
    await asyncio.sleep(1)
    return x * 2

@app.local_entrypoint()
async def main():
    tasks = [async_task.remote.aio(i) for i in range(100)]
    results = await asyncio.gather(*tasks)
```

## Common Gotchas

**Incorrect**: Using Python's builtin map (runs sequentially)
```python
# DON'T DO THIS
results = map(evaluate_model, inputs)
```

**Incorrect**: Calling function first
```python
# DON'T DO THIS
results = evaluate_model(inputs).map()
```

**Correct**: Call .map() on Modal function object
```python
# DO THIS
results = evaluate_model.map(inputs)
```
