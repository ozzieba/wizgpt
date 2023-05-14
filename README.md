My take on AutoGPT and co

very early WIP

use code instead of natural language as the metalanguage to plan tasks etc

eg:

```

``` sh
$ python3 main.py
"{\"env\": {\"imports\": null, \"specs\": null, \"impls\": null}, \"comment\": \"use docker to run cowsay with the 42nd Fibonacci number\", \"sig\": {\"name\": \"run_fib42_in_docker\", \"returnType\": \"str\", \"args\": []}}"{
  "sig": {
    "returnType": "str",
    "name": "run_fib42_in_docker",
    "args": []
  },
  "impl": "fib42 = compute_nth_fibonacci(42)\n\nresult = execute_docker_cowsay(fib42)",
  "env": {
    "imports": [
      {
        "name": "subprocess",
        "alias": null,
        "pip_install": null
      }
    ],
    "specs": [
      {
        "env": {
          "imports": null,
          "specs": null,
          "impls": null
        },
        "sig": {
          "returnType": "int",
          "name": "compute_nth_fibonacci",
          "args": [
            {
              "name": "n",
              "argtype": "int"
            }
          ]
        },
        "comment": "compute the nth Fibonacci number"
      },
      {
        "env": {
          "imports": [
            {
              "name": "subprocess",
              "alias": null,
              "pip_install": null
            }
          ],
          "specs": null,
          "impls": null
        },
        "sig": {
          "returnType": "str",
          "name": "execute_docker_cowsay",
          "args": [
            {
              "name": "message",
              "argtype": "str"
            }
          ]
        },
        "comment": "run the cowsay command in a Docker container with the specified message"
      }
    ],
    "impls": null
  }
}fib42 = compute_nth_fibonacci(42)

result = execute_docker_cowsay(fib42)
compute_nth_fibonacci is not defined. implementing...
"{\"env\": {\"imports\": null, \"specs\": null, \"impls\": null}, \"comment\": \"compute the nth Fibonacci number\", \"sig\": {\"name\": \"compute_nth_fibonacci\", \"returnType\": \"int\", \"args\": [{\"argtype\": \"int\", \"name\": \"n\"}]}}"{
  "sig": {
    "name": "compute_nth_fibonacci",
    "returnType": "int",
    "args": [
      {
        "name": "n",
        "argtype": "int"
      }
    ]
  },
  "impl": "if n == 0:\n    result = 0\nelif n == 1:\n    result = 1\nelse:\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    result = b",
  "env": {
    "imports": null,
    "specs": null,
    "impls": null
  }
}arg 0: 42if n == 0:
    result = 0
elif n == 1:
    result = 1
else:
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    result = b
execute_docker_cowsay is not defined. implementing...
"{\"env\": {\"imports\": [{\"name\": \"subprocess\", \"alias\": null, \"pip_install\": null}], \"specs\": null, \"impls\": null}, \"comment\": \"run the cowsay command in a Docker container with the specified message\", \"sig\": {\"name\": \"execute_docker_cowsay\", \"returnType\": \"str\", \"args\": [{\"argtype\": \"str\", \"name\": \"message\"}]}}"{
  "sig": {
    "returnType": "str",
    "name": "execute_docker_cowsay",
    "args": [
      {
        "name": "message",
        "argtype": "str"
      }
    ]
  },
  "impl": "docker_command = f'docker run -it --rm docker/whalesay cowsay {message}'\nresult = subprocess.getoutput(docker_command)",
  "env": {
    "imports": [
      {
        "name": "subprocess",
        "alias": null,
        "pip_install": null
      }
    ],
    "specs": null,
    "impls": null
  }
}arg 0: 267914296docker_command = f'docker run -it --rm docker/whalesay cowsay {message}'
result = subprocess.getoutput(docker_command)
 ___________
< 267914296 >
 -----------
                                   ##        .
              ## ## ##       ==
           ## ## ## ##      ===
       /""""""""""""""""___/ ===
  ~~~ {~~ ~~~~ ~~~ ~~~~ ~~ ~ /  ===- ~~~
       \______ o          __/
        \    \        __/
          \____\______/

```
b
```

```

```
