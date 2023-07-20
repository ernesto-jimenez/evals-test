# POC: OpenAI evals in unweave

## Usage

```bash
$ gh clone ernesto-jimenez/evals-test
$ cd evals-test
$ just set-up
$ just check
```

## About

For now, I'm just deploying the same app as the endpoint and eval, similar to Zak's `evalmock`

**What's in the repository?**

* Submodule to `openai/evals`.
* `main.py` contains the fastapi server for our eval.
* `Dockerfile` to build docker image we use for the model and eval.
* `Justfile` to easily test things out.

**What's nice with the approach?**

* It would be trivial to set-up `dependabot` on the repo to automatically create PRs when `openai/evals` gets updated.
* We could have a github workflow doing continuous delivery of the evals.

