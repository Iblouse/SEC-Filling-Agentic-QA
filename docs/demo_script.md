# Demonstrating the SEC Filing Agentic QA API

The demonstration workflow separates infrastructure validation from the
question shown during an interview.

## Before the interview

Start the API and confirm that it is ready:

```bash
./scripts/resume_api.sh
./scripts/status_api.sh
./scripts/smoke_test_api.sh
```

The smoke test validates the production API, authentication, grounded-answer
path, citations, feedback endpoint, and deployment state. It is not tied to a
development day or release stage.

## List available questions

The interactive demonstration reads questions from the active evaluation
catalog:

```bash
./scripts/demo.sh --list
```

## Select a question interactively

```bash
./scripts/demo.sh
```

The script displays the available benchmark questions and prompts you to select
one.

Enter `0` to provide a custom question.

## Run a question by number

```bash
./scripts/demo.sh --index 1
```

Use the number displayed by:

```bash
./scripts/demo.sh --list
```

## Enter a custom question

```bash
./scripts/demo.sh --custom
```

The script prompts for:

- Question
- Issuer or CIK
- Filing form
- Optional section label

## Saved response

The complete response is saved to:

```text
/tmp/sec-qa-demo-response.json
```

Display the saved response as an offline fallback:

```bash
jq . /tmp/sec-qa-demo-response.json
```

## After the interview

Return the API to zero running tasks:

```bash
./scripts/pause_api.sh
./scripts/status_api.sh
```

The expected final ECS state is:

```text
desired: 0
running: 0
pending: 0
```
