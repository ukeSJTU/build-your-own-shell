import os
import subprocess
import sys


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


BUILTINS = {
    "exit": handle_exit,
    "echo": handle_echo,
    "pwd": handle_pwd,
    "cd": handle_cd,
    "type": handle_type,
}


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


def execute_external(cmd, args):
    flag, full_path = find_exe_in_path(cmd)
    if flag:
        try:
            subprocess.run([cmd] + args)
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"{cmd}: command not found")


def parse_input(input_string):
    tokens = []
    current_token = []
    in_single_quote = False
    in_double_quote = False
    escape_next = False

    for char in input_string:
        # Handle escape character
        if escape_next:
            current_token.append(char)
            escape_next = False
            continue
        # In single quote mode, only another single quote ' can end this state
        if in_single_quote:
            if char == "'":
                in_single_quote = False # Closing single quote
            else:
                current_token.append(char)
        # In double quote mode, only another double quote " can end this state
        elif in_double_quote:
            if char == '"':
                in_double_quote = False
            else:
                current_token.append(char)
        # In normal mode
        else: 
            if char == '\\':
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

        try:
            # parts = shlex.split(user_input)
            parts = parse_input(user_input)
        except ValueError:
            print("Syntax error: unbalanced quotes")
            continue

        if not parts:
            continue

        cmd = parts[0]
        args = parts[1:]

        if cmd in BUILTINS:
            BUILTINS[cmd](args)
        else:
            execute_external(cmd, args)


if __name__ == "__main__":
    main()
