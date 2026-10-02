"""python -m ocm <build | serve | mcp | measure | calc> ...  (see README.md)"""
import sys


def main():
    cmds = {"build": "build", "serve": "server", "mcp": "mcp", "measure": "measure", "calc": "calc"}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__); sys.exit(2)
    import importlib
    importlib.import_module(f"ocm.{cmds[sys.argv[1]]}").main(sys.argv[2:])


if __name__ == "__main__":
    main()
