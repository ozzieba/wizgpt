import openai
from marshmallow_dataclass import dataclass
from typing import List, Tuple, Optional
import json
import sys
from time import sleep
import builtins
import traceback as tb


@dataclass
class Arg:
    name: str
    argtype: Optional[str]


@dataclass
class FunctionSignature:
    returnType: str
    name: str
    args: Optional[List[Arg]]  # each arg has a name and a type


@dataclass
class Import:
    name: str
    alias: Optional[str] = None
    pip_install: Optional[str] = None  # package to install via pip


@dataclass
class Environment:
    specs: Optional[List["FunctionSpec"]] = None
    impls: Optional[List["Function"]] = None
    imports: Optional[List["Import"]] = None


@dataclass
class FunctionSpec:
    env: Environment
    sig: FunctionSignature
    comment: str  # description in natural language of what the function does


@dataclass
class Function:
    sig: FunctionSignature
    impl: str  # code that actually implements the function
    env: Environment


def call_gpt4(system_prompt, user_prompt, stream=True):
    sys.stderr.write(user_prompt)
    sys.stderr.flush()
    sleep(5)
    return openai.ChatCompletion.create(
        model="gpt-4",
        temperature=0.9,
        n=1,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=stream,
    )


def request_gpt4_implementation(spec: FunctionSpec):
    system_prompt = open("system_prompt").read()
    user_prompt = json.dumps(FunctionSpec.Schema().dumps(spec))
    stream = True
    for i in range(5):
        try:
            resp = call_gpt4(system_prompt, user_prompt)
            if not stream:
                resp = [resp]

            content = ""
            for part in resp:
                choices = part["choices"]
                for c_idx, c in enumerate(sorted(choices, key=lambda s: s["index"])):
                    if stream:
                        delta = c["delta"]
                        if "content" in delta:
                            sys.stderr.write(delta["content"])
                            content += delta["content"]
                    else:
                        sys.stderr.write(c["message"]["content"])
                        content = c["message"]["content"]
                    sys.stderr.flush()

            return Function.Schema().loads(content)
        except Exception as e:
            sys.stderr.write(tb.format_exc(e))
            continue


class CustomGlobalNamespace(dict):
    def __missing__(self, key):
        return self.handle_undefined(key)

    def handle_undefined(self, key):
        print(f"{key} is not defined. implementing...")
        # sys.stderr.write(str(self.env.specs))
        spec = next(f for f in self.env.specs if f.sig.name == key)
        return lambda *args, **kwargs: execute_function(
            request_gpt4_implementation(spec), self.env, *args, **kwargs
        )

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.__missing__(key)


def fix_code(code, ns, error):
    sys.stderr.write(f"\nfixing code...")
    system_prompt = "You are a code fixing machine. Please fix the following Python code. Return only Python code, as it will be executed automatically and directly. Do not enclose in a code block, nor include any other prose. Do not use recursion"
    user_prompt = f"```\n${code}\n``` runtime environment: ${json.dumps({k:str(v) for k, v in ns.items()})}"
    stream = True
    for i in range(5):
        try:
            resp = call_gpt4(system_prompt, user_prompt)
            if not stream:
                resp = [resp]

            content = ""
            for part in resp:
                choices = part["choices"]
                for c_idx, c in enumerate(sorted(choices, key=lambda s: s["index"])):
                    if stream:
                        delta = c["delta"]
                        if "content" in delta:
                            sys.stderr.write(delta["content"])
                            content += delta["content"]
                    else:
                        sys.stderr.write(c["message"]["content"])
                        content = c["message"]["content"]
                    sys.stderr.flush()

            return content
        except Exception as e:
            sys.stderr.write(str(e) + "\n")
            continue


def execute_function(function: Function, *args, **kwargs):
    ns = CustomGlobalNamespace({**globals(), **builtins.__dict__})
    ns.env = function.env
    for i, a in enumerate(args[1:]):
        sys.stderr.write(f"arg {i}: {a}")
        ns[function.sig.args[i].name] = a
    for k, v in kwargs.items():
        ns[k] = v
    impl = function.impl
    for i in range(5):
        try:
            sys.stderr.write(impl + "\n")
            # sys.stderr.write(json.dumps({k: str(v) for k, v in ns.items()}) + "\n")
            sleep(5)
            exec(
                "\n".join(
                    [
                        f"import {i.name} as {i.alias or i.name}"
                        for i in (function.env.imports or [])
                    ]
                    + [impl]
                ),
                ns,
            )
            return ns["result"]
        except Exception as e:

            print(tb.format_exc())

            impl = fix_code(impl, ns, tb.format_exc())
            continue


print(
    execute_function(
        request_gpt4_implementation(
            FunctionSpec.Schema().loads(
                '{"sig": {"returnType":"str","name":"run_fib42_in_docker","args":[]},"comment":"use docker to run cowsay with the 42nd Fibonacci number","env":{}}'
            )
        ),
    )
)
