# Day 10 Design: Bounded Critique and Revision

## Goal

Measure whether a bounded answer-critic-revision workflow improves the Day 9 single-pass grounded QA baseline while preserving deterministic citation validation and predictable cost.

## Control flow

1. Retrieve hybrid SEC evidence exactly as in Day 9.
2. Generate the initial grounded answer.
3. Run a critic over the question, evidence, and initial answer.
4. Revise only when the critic requests revision or deterministic citation validation fails.
5. Permit at most one revision.
6. Run one final critic review after a revision, but never revise a second time.
7. Record unresolved failures rather than creating an unbounded loop.

## Why the loop is bounded

Unbounded agent loops create unpredictable latency, token cost, and failure behavior. A maximum of one revision makes the workflow testable and gives the project an explicit termination condition.

## Critic contract

The critic returns structured JSON with:

- `verdict`: `accept` or `revise`
- `summary`: short observable assessment
- `issues`: actionable problems only
- `should_abstain`: whether the evidence is insufficient

The critic may not use outside knowledge and is not asked to expose chain-of-thought.

## Revision contract

The reviser receives the same SEC evidence, the original answer, and the critic decision. It must preserve the Day 9 citation format and use `INSUFFICIENT_EVIDENCE:` when the evidence does not support an answer.

## Models

The default generator, critic, and reviser all use `us.amazon.nova-2-lite-v1:0`. Keeping the model fixed isolates the effect of the workflow from the effect of switching models. The CLI accepts separate model IDs so later experiments can use a distinct critic.

## Evaluation

The frozen q001-q015 relevance dataset remains unchanged. Day 10 records initial and final:

- citation validity
- gold-evidence hit rate
- cited-gold precision
- cited-gold recall
- critic acceptance rate
- revision rate
- unresolved-after-revision rate
- model calls
- token usage

Manual review is still required because a model critic can agree with an incorrect model answer.
