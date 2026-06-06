# Weakest-Link Audit Lens

Use when a causal story is plausible but may fail inside the mechanism chain.

1. Write the mechanism as `A -> B -> C -> D`.
2. For each link, ask:
   - Is direction established?
   - Is the link necessary?
   - Is the magnitude proportional?
   - Is there a confounder?
   - Is there a bad-control or collider risk?
3. Identify the weakest link.
4. Specify the cheapest test that would strengthen or break that link.

Output:

- mechanism chain
- weakest link
- evidence needed
- whether the story survives without that link
