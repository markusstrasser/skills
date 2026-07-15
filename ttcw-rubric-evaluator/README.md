# TTCW Rubric Evaluator Skill

A Claude Code skill for evaluating creative fiction writing using the TTCW (Tall Tale Creative Writing) rubric from the CHI '24 research paper "Art or Artifice? Large Language Models and the False Promise of Creativity."

## Overview

This skill provides expert-level evaluation of creative fiction across 13 binary criteria organized into four dimensions:

- **Fluency** (5 criteria): Narrative pacing, scene/exposition balance, language proficiency, endings, coherence
- **Flexibility** (3 criteria): Perspective diversity, emotional range, structural innovation
- **Originality** (3 criteria): Theme novelty, avoiding clichés, form innovation
- **Elaboration** (2 criteria): Character complexity, rhetorical depth/subtext

## Architecture

The skill uses a **subagent-per-criterion architecture**:
- Each of the 13 criteria is evaluated by a dedicated subagent
- Subagents run in parallel for efficiency (4 batches)
- Each subagent receives the exact rubric definition and evaluation instructions
- Main agent synthesizes results into comprehensive report

## Files

- **SKILL.md**: Main skill file with instructions for Claude Code
- **CRITERIA.md**: Complete rubric with exact phrasing from research paper
- **EXAMPLES.md**: Sample evaluations and usage patterns
- **README.md**: This file

## Usage

### In Claude Code

```
Evaluate this story using the TTCW rubric:
[paste your story]
```

Or for specific dimensions:
```
Evaluate the Fluency and Originality criteria for this story:
[paste your story]
```

### Linking the Skill

**For development:**
```bash
# From this repository
cd ~/Projects/skills
./skill-authoring/scripts/link-skill.sh
# Select: ttcw-rubric-evaluator
```

**For production:**
```bash
# Link to Claude Code skills directory
ln -s ~/Projects/skills/ttcw-rubric-evaluator ~/.claude/skills/ttcw-rubric-evaluator

# Or for project-specific use
ln -s ~/Projects/skills/ttcw-rubric-evaluator .claude/skills/ttcw-rubric-evaluator
```

## Evaluation Process

When you request an evaluation:

1. **Claude reads CRITERIA.md** to get exact criterion definitions
2. **Launches 13 subagents in parallel** (4 batches):
   - Batch 1: 5 Fluency criteria
   - Batch 2: 3 Flexibility criteria
   - Batch 3: 3 Originality criteria
   - Batch 4: 2 Elaboration criteria
3. **Each subagent evaluates one criterion**:
   - Analyzes story using exact LLM instruction from rubric
   - Provides step-by-step reasoning
   - Returns Yes/No answer with justification
4. **Main Claude synthesizes** results into comprehensive report with:
   - Overall scores by dimension
   - Detailed results for each criterion
   - Identified strengths and weaknesses
   - Actionable improvement suggestions

## Report Format

```markdown
# TTCW Rubric Evaluation Report

## Overall Scores
- Fluency: X/5
- Flexibility: X/3
- Originality: X/3
- Elaboration: X/2
- Total: X/13

## Detailed Results
[Yes/No for each criterion with reasoning]

## Strengths
[What the story does well]

## Areas for Improvement
[Specific, actionable suggestions]

## Overall Assessment
[Holistic synthesis]
```

## Use Cases

### For Writers
- Get objective, detailed feedback on your creative fiction
- Identify specific areas for revision
- Track improvement across drafts
- Understand craft fundamentals vs originality issues

### For Educators
- Consistent evaluation rubric for creative writing courses
- Transparent grading criteria for students
- Track student progress over semester
- Calibrate peer reviews against expert standards

### For Researchers
- Systematic evaluation of AI-generated vs human writing
- Study correlation between criteria and reader preference
- Validate rubric against human expert judgments
- Compare different writing approaches/prompts

### For Editors
- First-pass evaluation of submissions
- Generate specific revision requests
- Identify patterns in successful vs unsuccessful stories
- Track whether revisions address identified issues

## Criteria Summary

| # | Criterion | Question |
|---|-----------|----------|
| 1 | Narrative Pacing | Does time compression/stretching feel appropriate? |
| 2 | Scene vs Exposition | Appropriate balance between scene and summary? |
| 3 | Language Proficiency | Sophisticated use of idiom/metaphor/allusion? |
| 4 | Narrative Ending | Ending feels natural and earned? |
| 5 | Coherence | Elements form unified, engaging whole? |
| 6 | Perspective Flexibility | Diverse perspectives, convincing characters? |
| 7 | Emotional Flexibility | Good balance interiority/exteriority? |
| 8 | Structural Flexibility | Turns both surprising and appropriate? |
| 9 | Theme Originality | Reader gains unique/original ideas? |
| 10 | Thought Originality | Original writing without clichés? |
| 11 | Form Originality | Shows originality in form/structure? |
| 12 | Character Development | Characters appropriately complex? |
| 13 | Rhetorical Complexity | Subtext enriches the story? |

## Scoring Interpretation

- **10-13/13**: Exceptional craft quality with original execution
- **7-9/13**: Solid fundamentals with some areas for growth
- **4-6/13**: Developing craft with significant revision needed
- **0-3/13**: Substantial craft issues across multiple dimensions

Note: Scoring is intentionally rigorous. "Yes" means clearly successful at a high level.

## Limitations

- **Binary scoring**: Doesn't capture gradations of quality
- **Genre-agnostic**: Same standards for all fiction types
- **Academic focus**: Reflects creative writing MFA values
- **Single aesthetic**: May not align with all literary traditions
- **Craft vs taste**: Evaluates technical execution, not personal preference

## References

- **Paper**: "Art or Artifice? Large Language Models and the False Promise of Creativity"
- **Conference**: CHI '24 (May 11-16, 2024, Honolulu, Hawaii)
- **Authors**: Chakrabarty, et al.
- **Rubric**: TTCW (Tall Tale Creative Writing) evaluation framework

## Development

### Testing

Test the skill with various story types:
- Flash fiction (< 1000 words)
- Short stories (1000-7500 words)
- Different genres (literary, sci-fi, fantasy, horror)
- AI-generated vs human-written
- Published vs unpublished work

### Contributing

To improve this skill:
1. Test with diverse stories and document edge cases
2. Refine subagent prompts for more consistent evaluation
3. Add more examples to EXAMPLES.md
4. Compare against human expert evaluations
5. Optimize parallel execution for performance

### Version History

- **v1.0** (2024-11-13): Initial release with 13 criteria, subagent architecture

## License

This skill implements the TTCW rubric from published research. The rubric methodology is based on academic research (Chakrabarty, et al., CHI '24). This implementation is provided for educational and research purposes.

## Contact

For issues, questions, or contributions related to this skill implementation, please file an issue in the skills repository.
