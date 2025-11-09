"""
LLM provider calls for proposal generation via llmx CLI.

Critical gotchas (see skills/llmx-guide/SKILL.md):
1. Use subprocess with input=prompt, NOT shell=True (breaks with parentheses in prompt)
2. --reasoning-effort only works with OpenAI (gpt-5-pro), not gemini/grok/kimi
3. Model names: hyphens not dots (claude-sonnet-4-5 not 4.5)
4. Test incrementally before full pipeline
"""

import subprocess
from pathlib import Path
from typing import Optional
import re

# Import prompt variants
try:
    import prompts
except ImportError:
    # Fallback if prompts module not found
    prompts = None


# Get project root
PROJECT_ROOT = Path.cwd()


# Default constraints if no file provided
DEFAULT_CONSTRAINTS = {
    "context": "Architectural decisions for a software project",
    "must": [
        "Focus on simplicity over cleverness",
        "Debuggability is critical (observable state, clear errors)",
        "Document tradeoffs clearly"
    ],
    "should": [
        "Prefer explicit over implicit",
        "Minimize dependencies"
    ]
}


def load_constraints(constraints_file: Optional[Path] = None) -> dict:
    """
    Load project constraints from markdown file.

    Args:
        constraints_file: Path to constraints markdown file
                         If None, looks for .architect/project-constraints.md

    Returns:
        Dict with keys: context, must, should

    Falls back to DEFAULT_CONSTRAINTS if file not found.
    """
    if constraints_file is None:
        constraints_file = PROJECT_ROOT / ".architect" / "project-constraints.md"

    if not constraints_file.exists():
        return DEFAULT_CONSTRAINTS

    content = constraints_file.read_text()

    # Parse markdown sections
    constraints = {
        "context": "",
        "must": [],
        "should": []
    }

    # Extract context (first paragraph after "## Context")
    context_match = re.search(r'## Context\s+(.+?)(?=\n##|\Z)', content, re.DOTALL)
    if context_match:
        constraints["context"] = context_match.group(1).strip()

    # Extract MUST requirements (bullet points after "## MUST Requirements" until next ##)
    must_match = re.search(r'## MUST Requirements[^\n]*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if must_match:
        must_section = must_match.group(1)
        constraints["must"] = [
            line.strip()[2:].strip() for line in must_section.split('\n')
            if line.strip().startswith('-')
        ]

    # Extract SHOULD preferences (bullet points after "## SHOULD Preferences" until next ##)
    should_match = re.search(r'## SHOULD Preferences[^\n]*\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if should_match:
        should_section = should_match.group(1)
        constraints["should"] = [
            line.strip()[2:].strip() for line in should_section.split('\n')
            if line.strip().startswith('-')
        ]

    return constraints if constraints["must"] or constraints["should"] else DEFAULT_CONSTRAINTS


def format_constraints_prompt(constraints: dict) -> str:
    """Format constraints dict into XML prompt section."""
    must_items = '\n'.join(f'- {item}' for item in constraints['must'])
    should_items = '\n'.join(f'- {item}' for item in constraints['should'])

    return f"""<constraints>
MUST (hard requirements):
{must_items}

SHOULD (preferences):
{should_items}
</constraints>"""


def call_gemini(description: str, constraints: Optional[dict] = None, constraints_file: Optional[Path] = None, prompt_variant: str = "baseline") -> str:
    """
    Call Gemini to generate a proposal.

    Uses the gemini CLI wrapper.

    Args:
        description: Problem description
        constraints: Constraints dict (overrides file loading)
        constraints_file: Path to constraints file (default: .architect/project-constraints.md)
        prompt_variant: Prompt variant to use ('baseline', 'variant-a')
    """
    # Load constraints if not provided
    if constraints is None:
        constraints = load_constraints(constraints_file)

    # Get prompt from prompts module if available, else use baseline
    if prompts:
        prompt = prompts.get_prompt("gemini", description, constraints, prompt_variant)
    else:
        # Fallback to baseline prompt
        role = f"You are an architectural advisor.\n\nProject context: {constraints['context']}" if constraints['context'] else "You are an architectural advisor."

        prompt = f"""<role>
{role}
</role>

{format_constraints_prompt(constraints)}

<task>
Generate an implementation proposal for:

{description}

REQUIRED sections:
1. Core approach (2-3 sentences)
2. Key components and their responsibilities
3. Data structures and storage
4. Pros and cons (be honest about tradeoffs)
5. Red flags to watch for during implementation
</task>

<output_format>
Use markdown with clear headings.
Be concise - aim for 1-2 pages total.
Use bullet points over paragraphs where possible.
</output_format>
"""

    try:
        # Use llmx with google provider - uses default gemini/gemini-2.5-pro
        # (no need to specify model since 2.5 Pro is the default)
        # Note: Gemini doesn't support reasoning_effort parameter
        result = subprocess.run(
            ['llmx', '--provider', 'google'],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Gemini call failed: {e.stderr}") from e
    except FileNotFoundError:
        raise RuntimeError("llmx CLI not found - ensure it's installed (uv tool install /Users/alien/Projects/llmx)") from None


def call_codex(description: str, constraints: Optional[dict] = None, constraints_file: Optional[Path] = None, prompt_variant: str = "baseline") -> str:
    """
    Call OpenAI Codex (GPT-5) to generate a proposal.

    Uses the codex CLI wrapper with model_reasoning_effort="high".

    Args:
        description: Problem description
        constraints: Constraints dict (overrides file loading)
        constraints_file: Path to constraints file (default: .architect/project-constraints.md)
        prompt_variant: Prompt variant to use ('baseline', 'variant-a')
    """
    # Load constraints if not provided
    if constraints is None:
        constraints = load_constraints(constraints_file)

    # Get prompt from prompts module if available, else use baseline
    if prompts:
        prompt = prompts.get_prompt("codex", description, constraints, prompt_variant)
    else:
        # Fallback to baseline prompt
        role = f"You are an architectural advisor.\n\nProject context: {constraints['context']}" if constraints['context'] else "You are an architectural advisor."

        prompt = f"""<role>
{role}
</role>

{format_constraints_prompt(constraints)}

<task>
Generate an implementation proposal for:

{description}

REQUIRED sections:
1. Core approach (2-3 sentences)
2. Key components and their responsibilities
3. Data structures and storage
4. Pros and cons (be honest about tradeoffs)
5. Red flags to watch for during implementation
</task>

<output_format>
Use markdown with clear headings.
Be concise - aim for 1-2 pages total.
Use bullet points over paragraphs where possible.
</output_format>
"""

    try:
        # Use llmx with openai provider - uses default gpt-5-pro
        # NOTE: GPT-5 models only support temperature=1 (enforced by OpenAI API)
        result = subprocess.run(
            ['llmx', '--provider', 'openai', '--temperature', '1', '--reasoning-effort', 'high'],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Codex (GPT-5 Pro) call failed: {e.stderr}") from e
    except FileNotFoundError:
        raise RuntimeError("llmx CLI not found - ensure it's installed (uv tool install /Users/alien/Projects/llmx)") from None


def call_grok(description: str, constraints: Optional[dict] = None, constraints_file: Optional[Path] = None, prompt_variant: str = "baseline") -> str:
    """
    Call Grok to generate a proposal.

    Uses llmx CLI with xai provider and grok-4-latest model.

    Args:
        description: Problem description
        constraints: Constraints dict (overrides file loading)
        constraints_file: Path to constraints file (default: .architect/project-constraints.md)
        prompt_variant: Prompt variant to use ('baseline', 'variant-a')
    """
    # Load constraints if not provided
    if constraints is None:
        constraints = load_constraints(constraints_file)

    # Get prompt from prompts module if available, else use baseline
    if prompts:
        prompt = prompts.get_prompt("grok", description, constraints, prompt_variant)
    else:
        # Fallback to baseline prompt
        role = f"You are an architectural advisor.\n\nProject context: {constraints['context']}" if constraints['context'] else "You are an architectural advisor."

        prompt = f"""<role>
{role}
</role>

{format_constraints_prompt(constraints)}

<task>
Generate an implementation proposal for:

{description}

REQUIRED sections:
1. Core approach (2-3 sentences)
2. Key components and their responsibilities
3. Data structures and storage
4. Pros and cons (be honest about tradeoffs)
5. Red flags to watch for during implementation
</task>

<output_format>
Use markdown with clear headings.
Be concise and direct - aim for 1-2 pages total.
Use bullet points over paragraphs where possible.
</output_format>
"""

    try:
        # Note: Grok doesn't support reasoning_effort parameter
        result = subprocess.run(
            ['llmx', '--provider', 'xai', '-m', 'grok-4-latest', '--no-stream'],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Grok call failed: {e.stderr}") from e
    except FileNotFoundError:
        raise RuntimeError("llmx CLI not found - ensure it's installed (uv tool install /Users/alien/Projects/llmx)") from None


def call_kimi2(description: str, constraints: Optional[dict] = None, constraints_file: Optional[Path] = None, prompt_variant: str = "baseline") -> str:
    """
    Call Kimi 2 Thinking to generate a proposal.

    Uses llmx CLI with moonshot provider and kimi2-thinking model.

    Args:
        description: Problem description
        constraints: Constraints dict (overrides file loading)
        constraints_file: Path to constraints file (default: .architect/project-constraints.md)
        prompt_variant: Prompt variant to use ('baseline', 'variant-a')
    """
    # Load constraints if not provided
    if constraints is None:
        constraints = load_constraints(constraints_file)

    # Get prompt from prompts module if available, else use baseline
    if prompts:
        prompt = prompts.get_prompt("kimi2", description, constraints, prompt_variant)
    else:
        # Fallback to baseline prompt
        role = f"You are an architectural advisor.\n\nProject context: {constraints['context']}" if constraints['context'] else "You are an architectural advisor."

        prompt = f"""<role>
{role}
</role>

{format_constraints_prompt(constraints)}

<task>
Generate an implementation proposal for:

{description}

REQUIRED sections:
1. Core approach (2-3 sentences)
2. Key components and their responsibilities
3. Data structures and storage
4. Pros and cons (be honest about tradeoffs)
5. Red flags to watch for during implementation
</task>

<output_format>
Use markdown with clear headings.
Be concise and direct - aim for 1-2 pages total.
Use bullet points over paragraphs where possible.
</output_format>
"""

    try:
        # Use model inference (kimi-k2-thinking auto-infers kimi provider)
        # Note: Kimi doesn't support reasoning_effort parameter (it's inherent to k2-thinking model)
        result = subprocess.run(
            ['llmx', '--model', 'kimi-k2-thinking', '--no-stream'],
            input=prompt,
            capture_output=True,
            text=True,
            check=True,
            cwd=PROJECT_ROOT,
        )
        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Kimi2 call failed: {e.stderr}") from e
    except FileNotFoundError:
        raise RuntimeError("llmx CLI not found - ensure it's installed (uv tool install /Users/alien/Projects/llmx)") from None


def call_provider(provider_name: str, description: str, constraints: Optional[dict] = None, constraints_file: Optional[Path] = None, prompt_variant: str = "baseline") -> str:
    """
    Call a provider by name.

    Args:
        provider_name: One of 'gemini', 'codex', 'grok', 'kimi2'
        description: Problem description
        constraints: Constraints dict (overrides file loading)
        constraints_file: Path to constraints file (default: .architect/project-constraints.md)
        prompt_variant: Prompt variant to use ('baseline', 'variant-a')

    Returns:
        Proposal text

    Raises:
        ValueError: If provider_name is unknown
        RuntimeError: If provider call fails
    """
    providers = {
        "gemini": call_gemini,
        "codex": call_codex,
        "grok": call_grok,
        "kimi2": call_kimi2,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {', '.join(providers.keys())}")

    return providers[provider_name](description, constraints=constraints, constraints_file=constraints_file, prompt_variant=prompt_variant)
