# POC: OpenAI evals in unweave

## Usage

```bash
$ gh clone ernesto-jimenez/evals-test
$ cd evals-test
$ just set-up
$ just check
```

## About

For now, I'm just deploying OpenAI's evals as the model and eval, similar to Zak's `evalmock`:
* model: receives the name of an OpenAI eval and runs all the checks for that eval and returns the final report
* `/datasets`: list of OpenAI evals to run (right now hard-coded to `test-match`)
* `/validate`

**What's in the repository?**

* Submodule to `openai/evals`
* Dummy unweave `Completion Func` that currently just always returns a stubbed response.
* `completion_fns/unweave.yml` to load our dummy completion function into `oaieval`'s registry
* A go file to serve the HTTP server for the endpoint and eval
* `Dockerfile` to build docker image we use for the model and eval.
* `Justfile` to easily test things out.

**What's nice with the approach?**

* It would be trivial to set-up `dependabot` on the repo to automatically create PRs when `openai/evals` gets updated.
* We could have a github workflow doing continuous delivery of the evals.

**Next steps**

If this is looking good, next steps would be:
* Try scheduling an eval job that pushes check statuses, rather than the current approach of `platform` coordinating a check. Don't know how straightforward it will be to do it based on execs, given the set-up over SSH.
* Enable setting env variables for the containers, so we can inject the API endpoint and credentials to push check statuses.
* How would we handle releasing new versions of evals?

**What rough edges did I encounter?**

* Had to make contributions to `cli` to be able to script the tests (the scripting made it a lot quicker to test changes)
* If an exec's command fails or crashes, the exec is still around since the main process is `sshd`, so it appears as `running` when the command is actually not running, and the endpoint would return `Bad Gateway`
* I had to implement a liveness check in the script myself, since it was possible for the script to create a check when the eval or endpoint were still not running.
* Opaque errors because of the current logic of the coordinator.
* Had to do a quick and dirty implementation in `infra` of logging HTTP requests/responses and SQL requests in order to better debug the opaque errors.


