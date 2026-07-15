# TTCW Rubric Evaluator - Implementation Notes

## Critical Design Decisions

### 1. Exact Phrasing Requirement

**Problem**: Each subagent must use the EXACT wording from the research paper for valid evaluation.

**Solution**:
- CRITERIA.md contains word-for-word transcription from PDF
- SKILL.md explicitly instructs Claude to:
  1. Read CRITERIA.md BEFORE launching subagents
  2. Copy exact text (not paraphrase) into each subagent prompt
  3. Include complete example showing exact phrasing

**Verification**: Each subagent receives three exact texts:
1. **Expert Measure**: The binary question
2. **Expanded Expert Measure**: The detailed concept explanation
3. **LLM Instruction**: The specific evaluation methodology

### 2. Subagent-Per-Criterion Architecture

**Why**: Ensures focused, independent evaluation of each criterion without cross-contamination.

**How**:
- 13 dedicated subagents (one per criterion)
- Each receives only its criterion definition + story
- Main Claude synthesizes results

**Benefits**:
- Parallel execution (4 batches)
- Independent judgments
- Consistent methodology per criterion
- Scalable to additional criteria

### 3. Missing Elaboration1

**Issue**: PDF pages provided show Tables 15-27, but:
- Table 26 = Elaboration2 (Character Development)
- Table 27 = Elaboration3 (Rhetorical Complexity)
- **Table 14 = Elaboration1 is NOT in the provided pages**

**Current Status**:
- Skill implements 13 criteria (all visible in PDF)
- Elaboration1 needs to be added when full PDF is available

**To Fix**:
1. Obtain page with Table 14: TTCW Elaboration1
2. Add to CRITERIA.md with exact phrasing
3. Update SKILL.md to include 14th subagent
4. Update all counts from 13→14

### 4. Exact Text Transcription

All criterion text in CRITERIA.md is verbatim from PDF tables:

**Fluency (5):**
- Table 15: Narrative Pacing ✓
- Table 16: Scene vs Exposition ✓
- Table 17: Language Proficiency & Literary Devices ✓
- Table 18: Narrative Ending ✓
- Table 19: Understandability & Coherence ✓

**Flexibility (3):**
- Table 20: Perspective & Voice Flexibility ✓
- Table 21: Emotional Flexibility ✓
- Table 22: Structural Flexibility ✓

**Originality (3):**
- Table 23: Originality in Theme and Content ✓
- Table 24: Originality in Thought ✓
- Table 25: Originality in Form ✓

**Elaboration (2 of 3):**
- Table 14: **MISSING** - Elaboration1
- Table 26: Character Development ✓
- Table 27: Rhetorical Complexity ✓

## Usage Pattern

```
User: "Evaluate this story using TTCW rubric: [story]"
    ↓
Claude: Reads CRITERIA.md
    ↓
Claude: Launches 13 subagents in 4 batches
    ↓
Batch 1 (5 parallel): Fluency1-5
Batch 2 (3 parallel): Flexibility1-3
Batch 3 (3 parallel): Originality1-3
Batch 4 (2 parallel): Elaboration2-3
    ↓
Each subagent gets EXACT text from CRITERIA.md:
  - Expert Measure
  - Expanded Expert Measure
  - LLM Instruction
    ↓
Each subagent returns: Reasoning + Yes/No
    ↓
Claude synthesizes: Report with scores + feedback
```

## File Structure

```
ttcw-rubric-evaluator/
├── SKILL.md (299 lines)
│   ├── Frontmatter with description
│   ├── Overview of 13 criteria
│   ├── Instructions for Claude
│   │   ├── Step 1: Prepare story
│   │   ├── Step 2: Launch subagents (with EXACT phrasing requirement)
│   │   ├── Step 3: Parallel execution strategy
│   │   └── Step 4: Generate report
│   ├── Evaluation guidelines
│   ├── Advanced usage examples
│   └── Architecture diagram
│
├── CRITERIA.md (290 lines)
│   ├── All 13 criteria with exact phrasing
│   ├── For each criterion:
│   │   ├── Expert Measure (question)
│   │   ├── Expanded Expert Measure (concept)
│   │   └── LLM Instruction (methodology)
│   └── Summary table
│
├── EXAMPLES.md (266 lines)
│   ├── Flash fiction evaluation example
│   ├── Detailed subagent analysis example
│   ├── How subagents work together
│   ├── Usage tips for different audiences
│   ├── Common scoring patterns
│   └── Limitations and considerations
│
├── README.md (206 lines)
│   ├── Overview and architecture
│   ├── Usage instructions
│   ├── Linking instructions
│   ├── Evaluation process
│   ├── Report format
│   ├── Use cases
│   ├── Criteria summary table
│   └── References
│
└── IMPLEMENTATION_NOTES.md (this file)
    └── Technical decisions and exact phrasing details
```

## Quality Assurance Checklist

- [x] CRITERIA.md has exact text from PDF (verified against Tables 15-27)
- [x] SKILL.md explicitly requires exact phrasing
- [x] SKILL.md provides complete example with exact text
- [x] Each criterion has all three components (Expert Measure, Expanded, LLM Instruction)
- [x] LLM Instructions use exact wording from PDF
- [x] Architecture ensures each subagent evaluates exactly one criterion
- [x] Parallel execution strategy documented
- [ ] **TODO**: Add Elaboration1 when Table 14 is available
- [ ] **TODO**: Update all counts from 13 to 14 when complete

## Testing Checklist

When testing the skill:

1. **Verify exact phrasing**:
   - Compare subagent prompts to CRITERIA.md
   - Ensure no paraphrasing occurred
   - Check all three text blocks are complete

2. **Verify subagent independence**:
   - Each subagent should only reference its criterion
   - No cross-criterion contamination
   - No premature synthesis

3. **Verify parallel execution**:
   - Multiple subagents launched in single message
   - Check timing/efficiency

4. **Verify synthesis**:
   - All 13 evaluations included in report
   - Scores calculated correctly
   - Patterns identified across dimensions

## Future Improvements

1. **Add Elaboration1**: When full PDF available
2. **Validation**: Compare against human expert evaluations
3. **Performance**: Optimize prompt length while maintaining exactness
4. **Flexibility**: Add options for subset evaluation (e.g., only Fluency)
5. **Output formats**: JSON, CSV, or detailed HTML reports

## Research Paper Reference

- **Title**: "Art or Artifice? Large Language Models and the False Promise of Creativity"
- **Conference**: CHI '24 (May 11-16, 2024, Honolulu, Hawaii)
- **Authors**: Chakrabarty, et al.
- **Rubric**: TTCW (Tall Tale Creative Writing)
- **Pages Implemented**: Tables 15-27 (13 criteria)
- **Missing**: Table 14 (Elaboration1)
