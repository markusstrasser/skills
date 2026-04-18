<!-- Reference file for modal skill. Loaded on demand. -->

# Modal Images

## Overview

Modal Images define the environment code runs in - containers with dependencies installed. Images are built from method chains starting from a base image.

## Base Images

Start with a base image and chain methods:

```python
image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .uv_pip_install("torch<3")
    .env({"HALT_AND_CATCH_FIRE": "0"})
    .run_commands("git clone https://github.com/modal-labs/agi")
)
```

Available base images:
- `Image.debian_slim()` - Debian Linux with Python
- `Image.micromamba()` - Base with Micromamba package manager
- `Image.from_registry()` - Pull from Docker Hub, ECR, etc.
- `Image.from_dockerfile()` - Build from existing Dockerfile

## Installing Python Packages

### With uv (Recommended)

Use `.uv_pip_install()` for fast package installation:

```python
image = (
    modal.Image.debian_slim()
    .uv_pip_install("pandas==2.2.0", "numpy")
)
```

### With pip

Fallback to standard pip if needed:

```python
image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("pandas==2.2.0", "numpy")
)
```

Pin dependencies tightly (e.g., `"torch==2.8.0"`) for reproducibility.

## Installing System Packages

Install Linux packages with apt:

```python
image = modal.Image.debian_slim().apt_install("git", "curl")
```

## Setting Environment Variables

Pass a dictionary to `.env()`:

```python
image = modal.Image.debian_slim().env({"PORT": "6443"})
```

## Running Shell Commands

Execute commands during image build:

```python
image = (
    modal.Image.debian_slim()
    .apt_install("git")
    .run_commands("git clone https://github.com/modal-labs/gpu-glossary")
)
```

## Running Python Functions at Build Time

Download model weights or perform setup:

```python
def download_models():
    import diffusers
    model_name = "segmind/small-sd"
    pipe = diffusers.StableDiffusionPipeline.from_pretrained(model_name)

hf_cache = modal.Volume.from_name("hf-cache")

image = (
    modal.Image.debian_slim()
    .pip_install("diffusers[torch]", "transformers")
    .run_function(
        download_models,
        secrets=[modal.Secret.from_name("huggingface-secret")],
        volumes={"/root/.cache/huggingface": hf_cache},
    )
)
```

## Adding Local Files

### Add Files or Directories

```python
image = modal.Image.debian_slim().add_local_dir(
    "/user/erikbern/.aws",
    remote_path="/root/.aws"
)
```

By default, files are added at container startup. Use `copy=True` to include in built image.

### Add Python Source

Add importable Python modules:

```python
image = modal.Image.debian_slim().add_local_python_source("local_module")

@app.function(image=image)
def f():
    import local_module
    local_module.do_stuff()
```

## Using Existing Container Images

### From Public Registry

```python
sklearn_image = modal.Image.from_registry("huanjason/scikit-learn")

@app.function(image=sklearn_image)
def fit_knn():
    from sklearn.neighbors import KNeighborsClassifier
    ...
```

Can pull from Docker Hub, Nvidia NGC, AWS ECR, GitHub ghcr.io.

### From Private Registry

Use Modal Secrets for authentication:

**Docker Hub**:
```python
secret = modal.Secret.from_name("my-docker-secret")
image = modal.Image.from_registry(
    "private-repo/image:tag",
    secret=secret
)
```

**AWS ECR**:
```python
aws_secret = modal.Secret.from_name("my-aws-secret")
image = modal.Image.from_aws_ecr(
    "000000000000.dkr.ecr.us-east-1.amazonaws.com/my-private-registry:latest",
    secret=aws_secret,
)
```

### From Dockerfile

```python
image = modal.Image.from_dockerfile("Dockerfile")

@app.function(image=image)
def fit():
    import sklearn
    ...
```

Can still extend with other image methods after importing.

## Using Micromamba

For coordinated installation of Python and system packages:

```python
numpyro_pymc_image = (
    modal.Image.micromamba()
    .micromamba_install("pymc==5.10.4", "numpyro==0.13.2", channels=["conda-forge"])
)
```

## GPU Support at Build Time

Run build steps on GPU instances:

```python
image = (
    modal.Image.debian_slim()
    .pip_install("bitsandbytes", gpu="H100")
)
```

## GPU Image Recipes — Split-Brain CUDA

Stages that install TensorFlow — or any framework resolving CUDA user-space
libs via the system dynamic linker — hit "split-brain CUDA" on NVIDIA
`-runtime` base images. Symptoms:

- `nvidia-smi` passes inside the container (driver mount works)
- `tf.config.list_physical_devices('GPU')` returns `[]`
- TF silently falls back to CPU — jobs run to "completion" but produce
  partial/incomplete output
- Downstream step crashes on missing file hours later

Root cause: `nvidia/cuda:X-runtime-ubuntu22.04` ships `libcudart` but NOT
cuDNN. `tensorflow[and-cuda]==2.16.1` ships cuDNN wheels under
`site-packages/nvidia/cudnn/lib`. `LD_LIBRARY_PATH` does NOT recurse into
nested paths, so the linker resolves `libcudart` from the system path but
cannot find `libcudnn.so.8` at the same location. TF silently skips GPU
init. Reference: TF issue #65842.

**Fix recipe for TF stages:**

```python
image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.2.2-cudnn8-devel-ubuntu22.04",
        # 12.2.2-cudnn8 is the correct TF 2.16 pair:
        # - TF 2.16 wants CUDA 12.3 + cuDNN 8.9;
        # - CUDA 12.3 only ships cudnn9 tags (wrong ABI);
        # - kind=devel ships libdevice.10.bc for XLA (runtime strips it).
        add_python="3.11",
    )
    .pip_install(
        "tensorflow==2.16.1",
        # NOT tensorflow[and-cuda] — let the system libs take over; the
        # and-cuda extra ships nested cuDNN wheels that the linker can't find.
    )
)
```

Then in subprocess env set:

```python
env["XLA_FLAGS"] = "--xla_gpu_cuda_data_dir=/usr/local/cuda"
```

XLA JIT needs `libdevice.10.bc` (LLVM NVVM bitcode) for kernel compilation.
The `-runtime` image strips it; `-devel` ships it at
`/usr/local/cuda/nvvm/libdevice/libdevice.10.bc`. Without the flag XLA
searches `./libdevice.10.bc` (CWD) and fails with "libdevice not found".

### NVIDIA `nvidia/cuda` tag naming (non-obvious)

| CUDA | cuDNN variant tag |
|---|---|
| 12.2.2 | `cudnn8` (TF 2.16-compatible) |
| 12.3.2 | `cudnn9` only (breaks TF 2.16 ABI) |
| 12.4.1 / 12.5.1 / 12.6+ / 12.8+ / 13.x | `cudnn` (implicit, always latest) |

Verify via `https://hub.docker.com/v2/repositories/nvidia/cuda/tags` before
pinning a tag. Model-generated tag suggestions (e.g. `12.3.2-cudnn8`) often
don't exist on Docker Hub — always verify first.

### Channel priority for PyTorch + compiled C++ extensions

For tools needing PyTorch + a GPU-built C++ extension (PyG, DGL,
scatter/sparse/cluster, deepchem, flash-attn, transformer-engine), the
conda channel priority matters. Default `append` lets conda-forge's CPU-only
torch win the resolve and ABI-mismatch the GPU extensions.

```python
# bioconda_base(extra_channels=["pytorch", "nvidia", "pyg"],
#               extra_channels_priority="prepend")
# ... or equivalent .micromamba_install() with channel_priority="prepend"
```

Triple-pin extension packages: `pyg=2.6.1=py311_torch_2.4.0_cu121`, NOT
just `pyg`. Without the build string, the solver picks mismatched
CUDA / Python builds; C++ `.so` files crash at import with
`_version_cuda.so: undefined symbol _ZN5torch3jit17parse…`.

### uv_pip_install vs pip_install on CUDA base images

`uv_pip_install("torch")` resolves to the latest torch (CUDA 13.0 default)
regardless of base image CUDA version. On `nvidia/cuda:12.4` images with
`run_commands` compiling flash-attn or transformer-engine, this causes
CUDA version mismatch or ABI breakage. Use `pip_install` for the entire
chain when the base image dictates a specific CUDA.

### Fail-loud assertion pattern

Add an explicit CUDA-visibility check at the top of any GPU stage body:

```python
@app.function(image=image, gpu="T4")
def run():
    import subprocess
    # Driver mount check
    subprocess.run(["nvidia-smi"], check=True)
    # Framework check (the one that catches split-brain CUDA)
    import tensorflow as tf
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        raise RuntimeError("TF GPU init failed — split-brain CUDA?")
    # ... actual work
```

For PyTorch stages: `assert torch.cuda.is_available()`. The two-layer check
(nvidia-smi + framework device count) catches split-brain CUDA at launch
instead of after hours of CPU fallback.

## Image Caching

Images are cached per layer. Breaking cache on one layer causes cascading rebuilds for subsequent layers.

Define frequently-changing layers last to maximize cache reuse.

### Force Rebuild

```python
image = (
    modal.Image.debian_slim()
    .apt_install("git")
    .pip_install("slack-sdk", force_build=True)
)
```

Or set environment variable:
```bash
MODAL_FORCE_BUILD=1 modal run ...
```

## Handling Different Local/Remote Packages

Import packages only available remotely inside function bodies:

```python
@app.function(image=image)
def my_function():
    import pandas as pd  # Only imported remotely
    df = pd.DataFrame()
    ...
```

Or use the imports context manager:

```python
pandas_image = modal.Image.debian_slim().pip_install("pandas")

with pandas_image.imports():
    import pandas as pd

@app.function(image=pandas_image)
def my_function():
    df = pd.DataFrame()
```

## Fast Pull from Registry with eStargz

Improve pull performance with eStargz compression:

```bash
docker buildx build --tag "<registry>/<namespace>/<repo>:<version>" \
  --output type=registry,compression=estargz,force-compression=true,oci-mediatypes=true \
  .
```

Supported registries:
- AWS ECR
- Docker Hub
- Google Artifact Registry
