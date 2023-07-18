set dotenv-load := true

username := env_var('UNWEAVE_USERNAME')
project := env_var_or_default('UNWEAVE_PROJECT', 'sample_project')
env := env_var_or_default('UNWEAVE_ENV', 'production')
unweave := env_var_or_default('UNWEAVE_COMMAND', 'unweave')
tag := env_var_or_default('GITHUB_SHA', `git rev-parse HEAD`)

login:
  yes | {{unweave}} login

set-up: login
  if [ ! -d .unweave ]; then {{unweave}} link {{username}}/{{project}}; fi

terminate:
  {{unweave}} ls --json | jq -r '.[] | .id' | grep -v "null" | while read -r id; do yes | {{unweave}} terminate $id; done

create-exec:
  {{unweave}} exec --json --no-copy --port 8080 -i ghcr.io/ernesto-jimenez/evals-test:{{tag}} -- eval-server :8080 | jq -r .id > .exec_id

create-endpoint:
  {{unweave}} deploy --cmd "eval-server :8080" -i ghcr.io/ernesto-jimenez/evals-test:{{tag}} --json | jq -r .endpoint.id > .endpoint_id

create-eval: create-exec
  {{unweave}} eval new `cat .exec_id` --json | jq -r .id > .eval_id

attach-eval: create-eval create-endpoint
  {{unweave}} endpoint attach-eval `cat .endpoint_id` `cat .eval_id`

check: terminate attach-eval wait-all check-only

check-only:
  {{unweave}} endpoint check `cat .endpoint_id` --json | jq -r .checkID > .check_id
  cat .check_id

endpoints:
  {{unweave}} endpoint ls

unweave *args:
  {{unweave}} {{args}}

ls *args:
  {{unweave}} ls {{args}}

wait url:
  while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' https://{{url}})" != "405" ]]; do echo "Waiting for server..."; sleep 5; done

wait-endpoint:
  just wait `{{unweave}} endpoint ls --json | jq -r 'last.httpAddress'`

wait-eval:
  just wait `{{unweave}} eval ls --json | jq -r 'last.httpEndpoint'`

wait-all: wait-eval wait-endpoint

logs *args:
  {{unweave}} logs `cat .exec_id` {{args}}

ssh *args:
  {{unweave}} ssh `cat .exec_id` {{args}}
