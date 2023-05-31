import openai
import tiktoken
from subprocess import run, PIPE
from marshmallow_dataclass import dataclass
from typing import List, Tuple, Optional
import json
import sys
import os
from time import sleep
import builtins
import traceback as tb
import logging
import readline
import io


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


def prefill_input(prompt, prefill=""):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()

enc = tiktoken.encoding_for_model('gpt-4')
def call_gpt4(
    system_prompt,
    user_prompt,
    stream=True,
    log_prompt=False,
    log_response=True,
    allow_edit=True,
):
    tokenized=enc.encode(f"{system_prompt}\n{user_prompt}")
    max_len=8192-len(tokenized)-100
    if log_prompt:
        sys.stderr.write(user_prompt)
        sys.stderr.flush()
    if allow_edit:
        system_prompt, user_prompt = edit_or_abort(system_prompt, user_prompt)
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        # model="gpt-3.5-turbo",
        temperature=0.9,
        n=1,
        #max_tokens=min(2*len(tokenized),max_len),
        max_tokens=500,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=stream,
    )
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


def edit_or_abort(system_prompt, user_prompt):
    edited = prefill_input(
        f"edit before sending to gpt-4", f"{system_prompt}\n-------\n{user_prompt}"
    )
    print(edited)
    if not edited:
        return (False,)
    system_prompt, user_prompt = edited.split("\n-------\n")
    return system_prompt, user_prompt


def get_human_approval(message):
    feedback = input(message)
    if (feedback or "y")[0] in "YyTt1":
        return True
    if feedback[:3] == "err":
        raise RuntimeError(f"got err feedback from user: ${feedback}")
    return False


def request_gpt4_implementation(spec: FunctionSpec):
    system_prompt = open("system_prompt").read()
    user_prompt = json.dumps(FunctionSpec.Schema().dumps(spec))
    while True:
        while not (
            get_human_approval(
                f"got this response:\n{(content:=call_gpt4(system_prompt, user_prompt))}\nuse it?"
            )
        ):
            continue
        try:
            return Function.Schema().loads(content)
        except Exception as e:
            sys.stderr.write(tb.format_exc())
            continue
    raise RuntimeError(
        f"failed to implement or did not get approval: prompt: {user_prompt}"
    )


class CustomGlobalNamespace(dict):
    # def __missing__(self, key):
    #    return self.handle_undefined(key)

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
            return self.handle_undefined(key)


env={}
def do_at_repl(task):
    session=io.StringIO()
    err=io.StringIO()
    session.write("""Python 3.8.2 (default, Mar 23 2020, 11:15:32)
[GCC 9.2.1 20191008] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> """)
    system_prompt = "You are an expert Python coder who likes to code from the Python repl; you manipulate files and run bash commands as necessary from the Python repl; you are now sitting at a Python repl; you are given a task which you are trying to complete as part of your job, as well as the record of the session so far. You return the next Python command you will run. You return only Python code, as it will be executed automatically and directly. Do not enclose in a code block, nor include any other prose. You output only one command at a time. You return 'exit()' when you are done with your task; your environment variables include GITHUB_TOKEN, and you can use the github api with that token. You do not type expressions to be evaluated directly in the repl, but rather you use print(). You are not interacting with any human, so whatever information you need you must use Python commands to get it; eg, never refer to 'your-username', but rather figure out the username from the repl using python commands; never run multiple Python statements together, always one per message, and then wait for the response if any"
    def syscmd(command):
        result = run(["bash","-c",command],stdout=PIPE,stderr=PIPE)
        session.write(result.stdout.decode("utf-8"))
        session.write(result.stderr.decode("utf-8"))
    ns = CustomGlobalNamespace({**globals(), **builtins.__dict__}, locals={})

    while True:
        user_prompt = json.dumps({"task": task, "err":err.getvalue(), "session": session.getvalue()})
        command = call_gpt4(system_prompt, user_prompt)
        if command[:6] == "exit()":
            break
        if get_human_approval(f"about to run command: ${command}"):
            try:
                oldout=sys.stdout
                olderr=sys.stderr
                oldsys=os.system
                session.write(f"{command}\n")
                sys.stdout=session
                sys.stderr=session
                os.system=syscmd
                ns['sys']=sys
                ns['os']=os
                exec(command, ns)
            except Exception as e:
                session.write(tb.format_exc())
            finally:
                sys.stdout=oldout
                sys.stderr=olderr
                os.system=oldsys
                session.write("\n>>> ")
                    


def fix_code(code, ns, error):
    sys.stderr.write(f"\nfixing code...")
    system_prompt = "You are a code fixing machine. Please fix the following Python code. Return only Python code, as it will be executed automatically and directly. Do not enclose in a code block, nor include any other prose. Do not use recursion"
    user_prompt = f"```\n${code}\n``` runtime environment: ${json.dumps({k:str(v) for k, v in ns.items()})}\nprevious error:\n{error}"
    while True:
        while not (
            get_human_approval(
                f"got this response:\n{(content:=call_gpt4(system_prompt, user_prompt))}\nuse it?"
            )
        ):
            continue
        try:
            return content
        except e:
            sys.stderr.write(tb.format_exc())
    raise RuntimeError(f"failed to fix or did not get approval: code: {code}")


def execute_function(function: Function, *args, **kwargs):
    ns = CustomGlobalNamespace({**globals(), **builtins.__dict__})
    impl = function.impl

    def setup_env():
        ns.env = function.env
        for i, a in enumerate(args[1:]):
            sys.stderr.write(f"arg {i}: {a}")
            ns[function.sig.args[i].name] = a
        for k, v in kwargs.items():
            ns[k] = v

    while get_human_approval(f"about to run the following code:\n{impl}\nProceed?"):
        setup_env()
        try:
            exec(
                "\n".join(
                    [
                        f"import {i.name} as {i.alias or i.name}"
                        if "." not in i.name
                        else f"from {'.'.join(i.name.split('.')[:-1])} import {i.name.split('.')[-1]} as {i.alias or i.name}"
                        for i in (function.env.imports or [])
                    ]
                    + [impl]
                ),
                ns,
            )
        except:
            impl = fix_code(impl, ns, tb.format_exc())
            continue
        if get_human_approval(f'\nresult: {ns["result"]}\nis that what you wanted?'):
            return ns["result"]
        else:
            comment = input("what went wrong?")
            impl = fix_code(impl, ns, f"Human feedback: {comment}")


prompt = input("what do you want to do today?")
do_at_repl(prompt)
# print(
#    execute_function(
#        request_gpt4_implementation(
#            FunctionSpec.Schema().loads(
#                #                '{"sig": {"returnType":"str","name":"do_what_the_comment_says","args":[]},"comment":"write a bit of code for a simple web site advertising wizgpt, an autonomous agent powered by gpt-4; use the gcloud cli to deploy it (use the gcloud environment configs for project, region, etc). If you use app engine, remember to create an app.yaml specifying how to deploy the html","env":{}}'
#                '{"sig": {"returnType":"str","name":"do_what_the_comment_says","args":[]},"comment":"'
#                + prompt
#                + '","env":{}}'
#            )
#        ),
#    )
# )
