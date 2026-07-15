---
name: ttcw-rubric-evaluator
description: Evaluate creative fiction writing using the TTCW (Tall Tale Creative Writing) rubric with 14 criteria across Fluency, Flexibility, Originality, and Elaboration. Use when the user wants to assess story quality, evaluate creative writing, get detailed feedback on narrative elements, or mentions TTCW rubric evaluation.
---

# TTCW Rubric Evaluator

Expert evaluation of creative fiction writing using the comprehensive TTCW rubric. Each criterion is evaluated by a specialized subagent for thorough analysis.

## Overview

The TTCW rubric evaluates creative writing across 14 binary criteria (Yes/No) organized into four dimensions:

- **Fluency** (5 criteria): Narrative flow, pacing, language, coherence
- **Flexibility** (3 criteria): Perspective, emotional range, structural innovation
- **Originality** (3 criteria): Theme, thought, form
- **Elaboration** (3 criteria): Character depth, rhetorical complexity, development

## Quick Start

To evaluate a story:

```
Evaluate this story using the TTCW rubric:
[paste story text]
```

Or for a specific dimension:

```
Evaluate the Fluency criteria for this story:
[paste story text]
```

## Evaluation Process

When evaluating a story, Claude will:

1. **Launch specialized subagents**: Each criterion is evaluated by a dedicated subagent for thorough analysis
2. **Analyze systematically**: Each subagent follows the LLM instruction pattern from the rubric
3. **Provide detailed reasoning**: Step-by-step explanation before Yes/No answer
4. **Generate summary report**: Overall scores and key findings

## The 13 Criteria (14 in original - 13 captured in PDF)

### Fluency (5 criteria)

1. **Narrative Pacing**: Does the manipulation of time in terms of compression or stretching feel appropriate and balanced?
2. **Scene vs Exposition**: Does the story have an appropriate balance between scene and summary/exposition or it relies on one of the elements heavily compared to the other?
3. **Language Proficiency**: Does the story make sophisticated use of idiom or metaphor or literary allusion?
4. **Narrative Ending**: Does the end of the story feel natural and earned, as opposed to arbitrary or abrupt?
5. **Coherence**: Do the different elements of the story work together to form a unified, engaging, and satisfying whole?

### Flexibility (3 criteria)

6. **Perspective Flexibility**: Does the story provide diverse perspectives, and if there are unlikeable characters, are their perspectives presented convincingly and accurately?
7. **Emotional Flexibility**: Does the story achieve a good balance between interiority and exteriority, in a way that feels emotionally flexible?
8. **Structural Flexibility**: Does the story contain turns that are both surprising and appropriate?

### Originality (3 criteria)

9. **Theme Originality**: Will an average reader of this story obtain a unique and original idea from reading it?
10. **Thought Originality**: Is the story an original piece of writing without any cliches?
11. **Form Originality**: Does the story show originality in its form?

### Elaboration (2 criteria captured)

12. **Character Development**: Does each character in the story feel developed at the appropriate complexity level, ensuring that no character feels like they are present simply to satisfy a plot requirement?
13. **Rhetorical Complexity**: Are there passages in the story that involve subtext and when there is subtext, does it enrich the story's setting or does it feel forced?

## Instructions for Claude

When a user requests TTCW rubric evaluation:

### Step 1: Prepare the Story
- Confirm you have the complete story text
- If story is in a file, read it first
- If story is very long, confirm with user before proceeding

### Step 2: Launch Subagent Evaluators

**CRITICAL**: Launch ONE dedicated subagent for EACH criterion using the Task tool.

**BEFORE launching subagents:**
1. **Read CRITERIA.md** to get the exact phrasing for all criteria
2. Use the EXACT text from CRITERIA.md - do not paraphrase or summarize

**Each subagent receives:**
1. The complete story text
2. The exact Expert Measure question from CRITERIA.md
3. The exact Expanded Expert Measure from CRITERIA.md (word-for-word)
4. The exact LLM Instruction from CRITERIA.md (word-for-word)

**Template for each subagent:**

```
Task tool with subagent_type="general-purpose"
description: "Evaluate [Criterion Name]"
prompt: "You are evaluating a creative fiction story against a specific TTCW rubric criterion.

STORY:
[paste complete story text]

EXPERT MEASURE:
[Copy EXACT Expert Measure question from CRITERIA.md]

EXPANDED EXPERT MEASURE:
[Copy EXACT Expanded Expert Measure text from CRITERIA.md - every word]

LLM INSTRUCTION:
[Copy EXACT LLM Instruction from CRITERIA.md - every word]

REQUIREMENTS:
- Follow the LLM Instruction exactly as written
- Provide step-by-step reasoning as specified in the instruction
- List specific examples from the story as requested
- End with a clear 'Yes' or 'No' answer only
- Provide a 2-3 sentence summary of your reasoning"
```

**Example for Fluency1:**

```
Task tool with subagent_type="general-purpose"
description: "Evaluate Narrative Pacing"
prompt: "You are evaluating a creative fiction story against a specific TTCW rubric criterion.

STORY:
[paste complete story text]

EXPERT MEASURE:
Does the manipulation of time in terms of compression or stretching feel appropriate and balanced?

EXPANDED EXPERT MEASURE:
'Compression/stretching of time' in fiction writing, also known as pacing, refers to the manipulation of time in storytelling for dramatic effect, pacing, or other narrative purposes. Essentially, it's about controlling the perceived speed and rhythm at which a story unfolds.

Compression of time refers to when events that take a long time (hours, days, weeks, or even years) are summarized or condensed into a brief narrative span. For example, a writer might compress several years of a character's life into a few paragraphs to quickly convey important changes or developments.

On the other hand, stretching of time is when a brief moment or event is drawn out over pages or chapters. It's often used to create suspense, emphasize details, or delve deeper into a character's thoughts and feelings. For example, the few seconds it takes for a dropped glass to hit the floor might be stretched out with detailed descriptions of the action, reactions, and thoughts of characters involved.

Storytime refers to the time within the world of the story, while real-world time refers to the time it takes for the reader to read the story. A skilled writer can manipulate the relationship between these two to affect the pacing of the narrative, either speeding it up (compression) or slowing it down (stretching). This technique plays a crucial role in shaping the reader's experience and engagement with the story.

LLM INSTRUCTION:
Given the story above, list out the scenes in the story in which time compression or time stretching is used, and argue for each whether it is successfully implemented. Then overall, give your reasoning about the question below and give an answer to it between 'Yes' or 'No' only

Q) Does the manipulation of time in terms of compression or stretching feel appropriate and balanced?

REQUIREMENTS:
- Follow the LLM Instruction exactly as written
- List out scenes with time compression/stretching
- Argue for each whether successfully implemented
- Provide overall reasoning
- Answer 'Yes' or 'No' only"
```

### Step 3: Parallel Evaluation Strategy

Launch subagents in parallel for efficiency. Recommended batches:

**Batch 1 - Fluency (5 subagents):**
- Subagent 1: Fluency1 - Narrative Pacing
- Subagent 2: Fluency2 - Scene vs Exposition
- Subagent 3: Fluency3 - Language Proficiency
- Subagent 4: Fluency4 - Narrative Ending
- Subagent 5: Fluency5 - Coherence

**Batch 2 - Flexibility (3 subagents):**
- Subagent 6: Flexibility1 - Perspective Flexibility
- Subagent 7: Flexibility2 - Emotional Flexibility
- Subagent 8: Flexibility3 - Structural Flexibility

**Batch 3 - Originality (3 subagents):**
- Subagent 9: Originality1 - Theme Originality
- Subagent 10: Originality2 - Thought Originality
- Subagent 11: Originality3 - Form Originality

**Batch 4 - Elaboration (2 subagents):**
- Subagent 12: Elaboration2 - Character Development
- Subagent 13: Elaboration3 - Rhetorical Complexity

Use a single message with multiple Task tool calls for each batch.

### Step 4: Generate Summary Report

After all 13 subagents complete, synthesize their findings into a comprehensive report:

```markdown
# TTCW Rubric Evaluation Report

## Story Overview
[Brief 2-3 sentence summary of the story]

## Overall Scores
- Fluency: X/5
- Flexibility: X/3
- Originality: X/3
- Elaboration: X/2
- **Total: X/13**

## Detailed Results

### Fluency (X/5)
1. [Yes/No] **Narrative Pacing**: [1-2 sentence summary from subagent]
2. [Yes/No] **Scene vs Exposition**: [1-2 sentence summary from subagent]
3. [Yes/No] **Language Proficiency**: [1-2 sentence summary from subagent]
4. [Yes/No] **Narrative Ending**: [1-2 sentence summary from subagent]
5. [Yes/No] **Coherence**: [1-2 sentence summary from subagent]

### Flexibility (X/3)
6. [Yes/No] **Perspective Flexibility**: [1-2 sentence summary from subagent]
7. [Yes/No] **Emotional Flexibility**: [1-2 sentence summary from subagent]
8. [Yes/No] **Structural Flexibility**: [1-2 sentence summary from subagent]

### Originality (X/3)
9. [Yes/No] **Theme Originality**: [1-2 sentence summary from subagent]
10. [Yes/No] **Thought Originality**: [1-2 sentence summary from subagent]
11. [Yes/No] **Form Originality**: [1-2 sentence summary from subagent]

### Elaboration (X/2)
12. [Yes/No] **Character Development**: [1-2 sentence summary from subagent]
13. [Yes/No] **Rhetorical Complexity**: [1-2 sentence summary from subagent]

## Strengths
[3-5 bullet points highlighting what the story does well, based on "Yes" evaluations]

## Areas for Improvement
[3-5 bullet points with specific, actionable suggestions based on "No" evaluations]

## Overall Assessment
[2-3 paragraphs synthesizing the evaluation results, discussing patterns across dimensions, and providing holistic feedback on the story's creative writing quality]
```

## Evaluation Guidelines

### For Each Criterion:
1. **Read the story carefully** through the lens of that specific criterion
2. **Identify specific examples** from the text that support your evaluation
3. **Consider context**: Genre, style, and authorial intent matter
4. **Apply nuance**: A "No" doesn't mean the story fails completely
5. **Explain reasoning**: Always provide step-by-step justification

### Subagent Prompts:
Use the LLM instruction patterns from the rubric:

- **List-based analysis**: "List out all X in the story, evaluate each, then answer"
- **Step-by-step reasoning**: "Explain reasoning step by step, then answer Yes/No"
- **Element identification**: "Identify elements, assess success, then answer"

### Quality Standards:
- **Yes** means the criterion is successfully met at a high level
- **No** doesn't mean complete failure, just that it doesn't meet the high bar
- Be rigorous but fair
- Consider the story as a whole, not just isolated moments

## Advanced Usage

### Evaluate Specific Dimensions
```
Evaluate only the Originality criteria for this story
```

### Compare Multiple Stories
```
Evaluate both stories using TTCW rubric and compare results
```

### Focus on Specific Criteria
```
Evaluate criteria 1, 3, and 12 for this story
```

### Developmental Feedback
```
Evaluate this story draft and provide specific revision suggestions for each failing criterion
```

## Best Practices

1. **Be thorough**: Each criterion deserves careful attention
2. **Be specific**: Cite actual passages and examples
3. **Be balanced**: Acknowledge both strengths and weaknesses
4. **Be constructive**: Frame criticism as opportunities for improvement
5. **Be consistent**: Apply the same standards across all criteria

## Detailed Criteria Reference

For detailed explanations of each criterion, including:
- Expanded expert measure definitions
- Literary concepts and terminology
- Examples of success and failure
- Common pitfalls

See [CRITERIA.md](CRITERIA.md)

## Example Evaluations

For sample evaluations showing the rubric in action:

See [EXAMPLES.md](EXAMPLES.md)

## Notes

- Each evaluation requires 13 separate subagent analyses - plan for sufficient time
- Subagents work in parallel for efficiency (4 batches recommended)
- The rubric is designed for creative fiction (short stories, flash fiction, etc.)
- Binary (Yes/No) answers are required, but detailed reasoning is crucial
- Each criterion has specific evaluation instructions that must be followed exactly
- Based on the research paper "Art or Artifice? Large Language Models and the False Promise of Creativity" (CHI '24)

## Architecture

The TTCW evaluation uses a **subagent-per-criterion architecture**:

```
User provides story
       ↓
Main Claude reads CRITERIA.md for exact definitions
       ↓
Launches 13 parallel subagents (in 4 batches)
       ↓
Each subagent evaluates ONE criterion:
  - Receives: story + criterion definition + LLM instruction
  - Analyzes: following exact evaluation pattern
  - Returns: reasoning + Yes/No answer
       ↓
Main Claude synthesizes all results
       ↓
Generates comprehensive evaluation report
```

This ensures:
- **Focused evaluation**: Each subagent concentrates on a single criterion
- **Consistent methodology**: Each uses the exact LLM instruction from the rubric
- **Parallel efficiency**: 13 evaluations happen simultaneously
- **Expert-level analysis**: Follows research-validated evaluation patterns

## References

- Original rubric: TTCW (Tall Tale Creative Writing) evaluation framework
- Source: CHI '24 Conference (May 11-16, 2024, Honolulu, Hawaii)
- Paper: Chakrabarty, et al.
