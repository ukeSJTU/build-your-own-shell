import contextlib
import os
import subprocess
import sys
from typing import Literal

HISTORY = []

def handle_exit(args):
    sys.exit(0)


def handle_echo(args):
    print(" ".join(args))


def handle_pwd(args):
    print(os.getcwd())


def handle_cd(args):
    path = os.path.expanduser(args[0])
    try:
        os.chdir(path)
    except FileNotFoundError:
        print(f"cd: {path}: No such file or directory")


def handle_type(args):
    target = args[0]
    if target in BUILTINS:
        print(f"{target} is a shell builtin")
    else:
        flag, full_path = find_exe_in_path(target)
        if flag:
            print(f"{target} is {full_path}")
        else:
            print(f"{target}: not found")

def handle_history(args):
    for i, h in enumerate(HISTORY):
        print(f"    {i+1}: {h}")

BUILTINS = {
    "exit": handle_exit,
    "echo": handle_echo,
    "pwd": handle_pwd,
    "cd": handle_cd,
    "type": handle_type,
    "history": handle_history,
}


@contextlib.contextmanager
def manage_io(redirects):
    opened_files = []
    original_stdout = sys.stdout
    original_stderr = sys.stderr

    stdout_handle = None
    stderr_handle = None

    try:
        # Handle stdout redirect
        if 1 in redirects:
            filename, mode = redirects[1]
            f = open(filename, mode)
            opened_files.append(f)
            stdout_handle = f
            sys.stdout = f

        # Handle stderr redirect
        if 2 in redirects:
            filename, mode = redirects[2]
            f = open(filename, mode)
            opened_files.append(f)
            stderr_handle = f
            sys.stderr = f

        yield stdout_handle, stderr_handle

    finally:
        # Cleanup
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        for f in opened_files:
            f.close()


def find_exe_in_path(exe: str):
    PATH = os.getenv("PATH")
    for dir in PATH.split(os.pathsep):
        # 1. Check if a file with the command name exists.
        full_path = os.path.join(dir, exe)
        if os.path.exists(full_path):
            # 2. Check if the file has execute permissions.
            if os.access(full_path, os.X_OK):
                # 3. If the file exists and has execute permissions, print <command> is <full_path> and stop.
                return True, full_path
            else:
                # 4. If the file exists but lacks execute permissions, skip it and continue to the next directory.
                continue
    else:
        return False, "not found"


def execute_external(cmd, args, stdout_handle=None, stderr_handle=None):
    flag, full_path = find_exe_in_path(cmd)
    if flag:
        try:
            subprocess.run([cmd] + args, stdout=stdout_handle, stderr=stderr_handle)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"{cmd}: command not found")


def parse_input(input_string):
    tokens = []
    current_token = []
    in_single_quote = False
    in_double_quote = False

    escape_next = False  # Used when in unquoted mode
    double_quote_escape = False  # Used when in double quoted mode

    for char in input_string:
        # Handle escape character
        if escape_next:
            current_token.append(char)
            escape_next = False
            continue
        # In single quote mode, only another single quote ' can end this state
        if in_single_quote:
            if char == "'":
                in_single_quote = False  # Closing single quote
            else:
                current_token.append(char)
        # In double quote mode, only another double quote " can end this state
        elif in_double_quote:
            # If a backslash has been met before
            if double_quote_escape:
                if char in ["\\", '"']:
                    current_token.append(char)
                else:
                    current_token.append("\\")
                    current_token.append(char)

                # 重置双引号内的转义状态
                double_quote_escape = False
            else:
                if char == '"':
                    in_double_quote = False
                elif char == "\\":
                    double_quote_escape = True
                else:
                    current_token.append(char)
        # In normal mode
        else:
            if char == "\\":
                # If a backslash is met, enter escape next mode
                escape_next = True
            elif char == "'":
                in_single_quote = True
            elif char == '"':
                in_double_quote = True
            elif char == " ":
                if len(current_token) > 0:
                    tokens.append("".join(current_token))
                    current_token = []
                else:
                    # Encountering a space while token is empty, we can just ignore it
                    pass
            else:
                current_token.append(char)

    if len(current_token) > 0:
        tokens.append("".join(current_token))

    return tokens


def parse_redirection(parts):
    command_parts = []
    redirection_map: dict[str, tuple[Literal[1, 2], Literal["w", "a"]]] = {
        ">": (1, "w"),
        "1>": (1, "w"),
        ">>": (1, "a"),
        "1>>": (1, "a"),
        "2>": (2, "w"),
        "2>>": (2, "a"),
    }
    # Save result in `redirects`: {1: ('file.txt', 'w'), 2: ('err.log', 'a')}
    redirects = {}

    i = 0
    while i < len(parts):
        token = parts[i]
        if token in redirection_map:
            # Next token should be the filename
            if i + 1 >= len(parts):
                print("Syntax error: expected filename after redirection operator")
                return None, None
            filename = parts[i + 1]
            fd, mode = redirection_map[token]
            redirects[fd] = (filename, mode)
            i += 2
        else:
            command_parts.append(parts[i])
            i += 1

    return command_parts, redirects


def main():
    while True:
        sys.stdout.write("$ ")
        sys.stdout.flush()

        try:
            user_input = input()
        except EOFError:
            break

        if not user_input:
            continue

        HISTORY.append(user_input)

        try:
            # parts = shlex.split(user_input)
            parts = parse_input(user_input)
        except ValueError:
            print("Syntax error: unbalanced quotes")
            continue

        if not parts:
            continue

        command_parts, redirects = parse_redirection(parts)

        # Syntax error occurred
        if command_parts is None:
            continue

        # Empty command
        if not command_parts:
            continue

        cmd = command_parts[0]
        args = command_parts[1:]

        try:
            with manage_io(redirects) as (out_handle, err_handle):
                if cmd in BUILTINS:
                    BUILTINS[cmd](args)
                else:
                    execute_external(
                        cmd, args, stdout_handle=out_handle, stderr_handle=err_handle
                    )
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
