This section reinforces the action-item extraction rules used within
summary.md — kept as a separate reference file per plan.md's prompts/
directory so action-item rules can be iterated on independently of the
overall summary prompt.

For every action item:
- task: a concise, specific description of the work.
- owner: the person clearly responsible, or null if not clearly stated.
- deadline: an ISO date if clearly stated, or null if not.
- priority: "low", "medium", or "high" based on urgency language in the transcript;
  default to "medium" when urgency isn't discussed.
- confidence: 0.0-1.0, how clearly the transcript supports this action item existing
  at all (not just its details).
