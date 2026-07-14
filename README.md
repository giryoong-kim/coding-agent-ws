# agentcore-coding-agents-starter

The "before AgentCore" starter project for the **Coding Agents on Amazon Bedrock
AgentCore Runtime** workshop. This is a GitHub **template**: create your own
repository from it (green **Use this template** button, or
`gh repo create <you>/<name> --template didhd/agentcore-coding-agents-starter`).
That repository is the project the workshop's coding agents enhance, and the pull
request they open lands as a real diff against it, under a GitHub App the workshop
brokers for you.

## What's here

- `cost_analyzer.py` - a plain, dependency-free Python module: a small AWS sizing
  and pricing calculator with five pure functions (estimate EC2 / EBS / S3 cost,
  recommend an instance, price a whole stack). It has no server, no UI, and no
  agent anywhere in it. That is the point: it is the raw material the agents build
  on top of.

## What the workshop does with it

In Lab 1 you run Claude Code to wrap the module as a remote MCP server. In Lab 2 an
autonomous orchestrator routes one task across three agents (a backend MCP server,
a chatbot UI, and a `pytest` acceptance gate) and composes their work into a single
pull request opened on **your** repository. In Lab 3 you operate the fleet: per-user
cost attribution, a graded MCP backend behind a Gateway, and the kill switch.

The dollar figures the calculator produces are **illustrative** (static, rounded,
not live AWS pricing).

## Use it

1. Click **Use this template -> Create a new repository** (keep it private), or run
   `gh repo create <you>/<name> --template didhd/agentcore-coding-agents-starter --private`.
   This gives every attendee an isolated repository, with no shared credentials and
   no fork conflicts.
2. In Lab 2 you deploy the **GitHub MCP Gateway** and install a GitHub App on this
   repository. The App credential lives inside the Gateway runtime; the coordinator
   and coding agents never hold a token.
3. Connect your `owner/repository` in the workshop console's **Settings** card.
   There is no token field: the Gateway holds the GitHub credential, so the console
   only records where your pull request should land.
