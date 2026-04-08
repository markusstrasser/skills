<!-- Reference file for data-acquisition skill. Loaded on demand. -->

# Software & Model Artifacts

Not web scraping — but frequently needed during data-acquisition tasks.

**Git repos:** `git clone --depth 1 URL dest/` (shallow clone saves bandwidth)
**HuggingFace models:** `huggingface-cli download ORG/MODEL --local-dir dest/` (needs `huggingface-hub` installed, some models need `huggingface-cli login` for gated access)
**Python packages:** `uv add PACKAGE` (never bare `pip install`)
**Large files from GitHub Releases:** `curl -L -o file "https://github.com/.../releases/download/TAG/FILE"`

If a model/dataset requires license acceptance or signup, STOP and tell the user which ones need manual action.
