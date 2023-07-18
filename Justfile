set dotenv-load := true

username := env_var('UNWEAVE_USERNAME')
project := env_var_or_default('UNWEAVE_PROJECT', 'sample_project')
env := env_var_or_default('UNWEAVE_ENV', 'production')
unweave := env_var_or_default('UNWEAVE_COMMAND', 'unweave')

login:
  yes | {{unweave}} login

set-up: login
  if [ ! -d .unweave ]; then {{unweave}} link {{username}}/{{project}}; fi

terminate: exec-id
  cat .exec_id | grep -v "null" | while read id; do yes | {{unweave}} terminate $id; done

create-exec: terminate
  {{unweave}} exec --no-copy -i ghcr.io/ernesto-jimenez/evals-test:main -- "oaieval -h"
  just exec-id

create-endpoint: create-exec
  {{unweave}} endpoint new `cat .exec_id` --json | jq -r .id > .endpoint_id

create-eval: create-exec
  {{unweave}} eval new `cat .exec_id` --json | jq -r .id > .eval_id

attach-eval: create-eval create-endpoint
  {{unweave}} --debug endpoint attach-eval `cat .endpoint_id` `cat .eval_id`

check: attach-eval
  {{unweave}} --debug endpoint check `cat .endpoint_id`

endpoints:
  {{unweave}} endpoint ls

unweave *args:
  {{unweave}} {{args}}

ls *args:
  {{unweave}} ls {{args}}

logs *args: exec-id
  {{unweave}} logs `cat .exec_id` {{args}}

ssh *args: exec-id
  {{unweave}} ssh `cat .exec_id` {{args}}

exec-id:
  {{unweave}} ls --json | jq -r 'first | .id' > .exec_id
  echo `cat .exec_id`
