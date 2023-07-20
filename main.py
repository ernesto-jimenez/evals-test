import json
import logging
import math
import shlex
import sys
from typing import Annotated, Any, Dict, Mapping, Optional, Union

import evals
import evals.api
import evals.base
import evals.record
import openai
from evals.api import (CompletionFn, CompletionResult, DummyCompletionFn,
                       DummyCompletionResult)
from evals.base import CompletionFnSpec
from evals.eval import Eval
from evals.prompt.base import (OpenAICreateChatPrompt, OpenAICreatePrompt,
                               Prompt)
from evals.registry import Registry
from fastapi import Body, Header, FastAPI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI()

# This is optional to configure a custom URL to run the model rather than
# calling the endpoint directly


@app.get("/")
async def manifest():
    return {
        "runURL": "/run",
    }


@app.get("/dataset")
async def dataset(eval: str = "test-match"):
    args = new_args(eval)
    fn = DummyCompletionFn()
    samples = gather_samples(args, fn)
    inputs = [{"input": sample} for sample in samples]
    return {"data": inputs}


@app.post("/run")
async def run_model(
        request: Annotated[Dict[str, Any], Body(embedded=True)],
        x_unweave_target_endpoint_url: Annotated[str | None, Header()] = None
        ):
    print(f"request: {request}")
    eval = str(request["eval"])
    del request["eval"]

    endpointURL = x_unweave_target_endpoint_url
    sample = request

    print(f"endpointURL: {endpointURL}")
    print(f"eval: {eval}")
    print(f"sample: {sample}")

    args = new_args(eval)

    # TODO: Replace for a completion function that calls
    # the endpoint x_unweave_target_endpoint_url
    fn = CompletionFnFake()

    result = run(args, fn, sample)

    print(f"result: {result}")
    clean_result = {
            key: value for key,
            value in result.items() if not math.isnan(value)
            }

    try:
        print(json.dumps(clean_result, allow_nan=False))
        print("encoded")
        return clean_result
    except ValueError:
        return f"RESULT: {result}"


@app.post("/assert")
async def assert_response(data: Annotated[Any, Body(embedded=True)]):
    print(f"assert data: {data}")
    return {
        "result": "unimplemented",
    }


@app.on_event("startup")
async def startup_event():
    logging.basicConfig(
        format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s",
        level=logging.INFO,
    )


class CompletionFnFake(CompletionFn):
    def __init__(self):
        self.prompts: list[dict[str, Any]] = []

    def __call__(
        self,
        prompt: Union[str, Prompt, OpenAICreateChatPrompt, OpenAICreatePrompt],
        **kwargs,
    ) -> DummyCompletionResult:
        self.prompts.append(prompt)
        return DummyCompletionResult()


def _purple(str: str) -> str:
    return f"\033[1;35m{str}\033[0m"


class OaiEvalArguments:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    extra_eval_params: str = ""
    max_samples: Optional[int] = None
    visible: Optional[bool] = None
    seed: int = 20220722
    user: str = ""
    log_to_file: Optional[str] = None
    registry_path: Optional[str] = None
    local_run: bool = True
    dry_run: bool = False
    dry_run_logging: bool = True


def setup(args: OaiEvalArguments,
          completion_fn: CompletionFn,
          registry: Optional[Registry] = None) -> (Eval,
                                                   evals.record.RecorderBase):
    visible = args.visible if args.visible is not None else (
        args.max_samples is None)

    if args.max_samples is not None:
        evals.eval.set_max_samples(args.max_samples)

    registry = registry or Registry()
    if args.registry_path:
        registry.add_registry_paths(args.registry_path)

    eval_spec = registry.get_eval(args.eval)
    assert (
        eval_spec is not None
    ), f"Eval {args.eval} not found. Available: {list(sorted(registry._evals.keys()))}"

    run_config = {
        "completion_fns": ["unweave"],
        "eval_spec": eval_spec,
        "seed": args.seed,
        "max_samples": args.max_samples,
        "command": " ".join(map(shlex.quote, sys.argv)),
        "initial_settings": {
            "visible": visible,
        },
    }

    eval_name = eval_spec.key
    if eval_name is None:
        raise Exception("you must provide a eval name")

    run_spec = evals.base.RunSpec(
        completion_fns=["unweave"],
        eval_name=eval_name,
        base_eval=eval_name.split(".")[0],
        split=eval_name.split(".")[1],
        run_config=run_config,
        created_by=args.user,
    )

    recorder: evals.record.RecorderBase
    recorder = evals.record.DummyRecorder(run_spec, log=False)

    run_url = f"{run_spec.run_id}"
    logger.info(_purple(f"Run started: {run_url}"))

    def parse_extra_eval_params(
        param_str: Optional[str],
    ) -> Mapping[str, Union[str, int, float]]:
        """Parse a string of the form "key1=value1,key2=value2" into a dict."""
        if not param_str:
            return {}

        def to_number(x: str) -> Union[int, float, str]:
            try:
                return int(x)
            except BaseException:
                pass
            try:
                return float(x)
            except BaseException:
                pass
            return x

        str_dict = dict(kv.split("=") for kv in param_str.split(","))
        return {k: to_number(v) for k, v in str_dict.items()}

    extra_eval_params = parse_extra_eval_params(args.extra_eval_params)

    eval_class = registry.get_class(eval_spec)
    eval: Eval = eval_class(
        completion_fns=[completion_fn],
        seed=args.seed,
        name=eval_name,
        registry=registry,
        **extra_eval_params,
    )
    return (eval, recorder)


def gather_samples(
        args: OaiEvalArguments,
        completion_fn: CompletionFn,
        registry: Optional[Registry] = None) -> list[Any]:
    eval, recorder = setup(args, completion_fn, registry)
    samples = list()
    # original_method = eval.eval_sample

    def other_method(sample, rand):
        samples.append({**sample, "eval": args.eval})
        # return original_method(sample, rand)

    eval.eval_sample = other_method
    eval.run(recorder)

    return samples


def run(
        args: OaiEvalArguments,
        completion_fn: CompletionFn,
        sample: Any,
        registry: Optional[Registry] = None) -> Any:
    eval, recorder = setup(args, completion_fn, registry)
    original_method = eval.eval_all_samples

    def stub(
        recorder: evals.record.RecorderBase,
        samples,
        show_progress=True,
        record_raw_sample=True,
        **_kwargs: Any,
    ):
        return original_method(
            recorder,
            [sample],
            show_progress,
            record_raw_sample)

    eval.eval_all_samples = stub
    result = eval.run(recorder)
    recorder.record_final_report(result)

    return result


def new_args(eval: str) -> OaiEvalArguments:
    return OaiEvalArguments(eval=eval)
