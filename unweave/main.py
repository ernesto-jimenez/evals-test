import argparse
import logging
import os
import shlex
import sys
from typing import Any, Mapping, Optional, Union, cast

import evals
import evals.api
import evals.base
import evals.record
import openai
from evals.api import CompletionFn, CompletionResult, DummyCompletionResult
from evals.base import CompletionFnSpec
from evals.eval import Eval
from evals.prompt.base import (OpenAICreateChatPrompt, OpenAICreatePrompt,
                               Prompt)
from evals.registry import Registry
from fastapi import FastAPI

logger = logging.getLogger(__name__)

def _purple(str: str) -> str:
    return f"\033[1;35m{str}\033[0m"


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run evals through the API")
    parser.add_argument("eval", type=str, help="Name of an eval. See registry.", default="test-match")
    parser.add_argument("--extra_eval_params", type=str, default="")
    parser.add_argument("--max_samples", type=int, default=None)
    parser.add_argument("--visible", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--seed", type=int, default=20220722)
    parser.add_argument("--user", type=str, default="")
    parser.add_argument(
        "--log_to_file", type=str, default=None, help="Log to a file instead of stdout"
    )
    parser.add_argument(
        "--registry_path",
        type=str,
        default=None,
        action="append",
        help="Path to the registry",
    )
    parser.add_argument("--local-run", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--dry-run", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--dry-run-logging", action=argparse.BooleanOptionalAction, default=True)
    return parser


class OaiEvalArguments:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    eval: str
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

def run(completion_fn: CompletionFn, registry: Optional[Registry] = None) -> str:
    args = new_args()

    visible = args.visible if args.visible is not None else (args.max_samples is None)

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
    recorder = evals.record.DummyRecorder(run_spec, log=True)

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
            except:
                pass
            try:
                return float(x)
            except:
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
    result = eval.run(recorder)
    recorder.record_final_report(result)

    return run_spec.run_id

def new_args() -> OaiEvalArguments:
    return OaiEvalArguments(
            eval=os.environ.get("EVAL", "test-match"),
            )

def init() -> None:
    args = new_args()
    print(args.eval)
    print(args.visible)
    logging.basicConfig(
        format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s",
        level=logging.INFO,
    )

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    init()

@app.get("/dataset")
async def root():
    fn = CompletionFnFake()
    run(fn)
    return {
            "data": [{"input": prompt} for prompt in fn.prompts]
            }

class CompletionFnFake(CompletionFn):
    prompts: list[dict[str, Any]] = []
    def __call__(
        self,
        prompt: Union[str, Prompt, OpenAICreateChatPrompt, OpenAICreatePrompt],
        **kwargs,
    ) -> DummyCompletionResult:
        self.prompts.append(prompt)
        return DummyCompletionResult()
