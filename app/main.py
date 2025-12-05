import contextlib
import os
import readline  # noqa: F401
import subprocess
import sys
from typing import Literal

HISTORY = []
HISTORY_WRITTEN_COUNT = 0

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
    global HISTORY_WRITTEN_COUNT

    if len(args) >= 2 and args[0] == "-r":
        path = args[1]
        try:
            with open(path, "r") as f:
                for line in f:
                    cmd = line.strip()
                    if cmd:
                        HISTORY.append(cmd)
        except FileNotFoundError:
            print(f"history: {path}: No such file or directory")

        return
    
    if len(args) >= 2 and args[0] == "-w":
        path = args[1]
        try:
            with open(path, "w") as f:
                for cmd in HISTORY:
                    f.write(cmd + "\n")

                HISTORY_WRITTEN_COUNT = len(HISTORY)

        except Exception as e:
            print(f"history: {e}")

        return
    
    if len(args) >= 2 and args[0] == "-a":
        path = args[1]
        try:
            with open(path, "a") as f:
                new_commands = HISTORY[HISTORY_WRITTEN_COUNT:]
                
                for cmd in new_commands:
                    f.write(cmd + "\n")

                HISTORY_WRITTEN_COUNT = len(HISTORY)
        except Exception as e:
            print(f"history: {e}")

        return

    limit = len(HISTORY)
    if args and args[0].isdigit():
        limit = int(args[0])

    history_to_show = HISTORY[-limit:] if limit < len(HISTORY) else HISTORY
    
    start_index = len(HISTORY) - len(history_to_show) + 1
    
    for i, h in enumerate(history_to_show, start=start_index):
        print(f"    {i}  {h}")

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

def parse_pipeline(tokens):
    # Convert a list of tokens into a list of commands separated by '|'
    # Given tokens: ['ls', '-l', '|', 'grep', 'py']
    # Return: [['ls', '-l'], ['grep', 'py']]
    if "|" not in tokens:
        return [tokens]
    
    commands = []
    current_cmd = []

    for token in tokens:
        if token == "|":
            if current_cmd:
                commands.append(current_cmd)
            current_cmd = []
        else:
            current_cmd.append(token)
        
    if current_cmd:
        commands.append(current_cmd)

    return commands

def run_pipeline(commands):
    processes = []

    prev_pipe_read = None # This holds the exit of previous pipe

    for i, cmd_tokens in enumerate(commands):
        is_last = (i == len(commands) - 1)

        cmd_parts, redirects = parse_redirection(cmd_tokens)
        if not cmd_parts:
            if prev_pipe_read is not None:
                os.close(prev_pipe_read)
            continue

        cmd_name = cmd_parts[0]
        cmd_args = cmd_parts[1:]

        # Prepare the next pipe
        current_pipe_read= None
        current_pipe_write= None

        stdout_dest = None
        stderr_dest = None

        if not is_last:
            r, w = os.pipe()
            current_pipe_read = r
            current_pipe_write = w
            stdout_dest = w # Current cmd should write into w
        else:
            # If is the last command, default write to screen which is None
            # Or will handled by parse_redirection
            pass

        # Determine Input
        stdin_source = prev_pipe_read

        # Track if file descriptors have been consumed by fdopen
        stdin_consumed = False
        stdout_consumed = False

        if cmd_name in BUILTINS:
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            original_stdin = sys.stdin

            try:
                # Handle stdin redirection
                if stdin_source is not None:
                    sys.stdin = os.fdopen(stdin_source, 'r')
                    stdin_consumed = True  # fdopen took ownership
                
                # Handle stdout redirection
                if stdout_dest is not None:
                    sys.stdout = os.fdopen(stdout_dest, 'w')
                    stdout_consumed = True  # fdopen took ownership
                elif 1 in redirects:
                     fname, mode = redirects[1]
                     sys.stdout = open(fname, mode)

                BUILTINS[cmd_name](cmd_args)
                
            except Exception as e:
                print(f"{cmd_name}: {e}", file=sys.stderr)
            finally:
                if sys.stdin != original_stdin:
                    sys.stdin.close()
                if sys.stdout != original_stdout:
                    sys.stdout.close()
                sys.stdin = original_stdin
                sys.stdout = original_stdout
                sys.stderr = original_stderr

        else:
            full_path_found, full_path = find_exe_in_path(cmd_name)
            if full_path_found:
                try:
                    if is_last and 1 in redirects:
                         fname, mode = redirects[1]
                         stdout_dest = open(fname, mode)
                    
                    p = subprocess.Popen(
                        [cmd_name] + cmd_args,
                        stdin=stdin_source,
                        stdout=stdout_dest,
                        stderr=stderr_dest
                    )
                    processes.append(p)
                    
                    # Close stdin/stdout after Popen - they're duplicated into child process
                    if stdin_source is not None:
                        stdin_consumed = True
                    if stdout_dest is not None:
                        stdout_consumed = True
                    
                    if is_last and 1 in redirects and hasattr(stdout_dest, 'close'):
                        stdout_dest.close()

                except Exception as e:
                    print(f"Error: {e}")
            else:
                print(f"{cmd_name}: command not found")

        # Close pipe file descriptors if they weren't consumed by fdopen
        if current_pipe_write is not None and not stdout_consumed:
            os.close(current_pipe_write)
            
        if prev_pipe_read is not None and not stdin_consumed:
            os.close(prev_pipe_read)
            
        prev_pipe_read = current_pipe_read

    for p in processes:
        p.wait()

def load_history():
    histfile = os.getenv("HISTFILE")
    if not histfile or not os.path.exists(histfile):
        return
    
    try:
        with open(histfile, "r") as f:
            for line in f:
                cmd = line.strip()
                if cmd:
                    HISTORY.append(cmd)          # 1. For 'history' command
                    readline.add_history(cmd)    # 2. For Up-Arrow key
    except FileNotFoundError:
        pass

def save_history():
    histfile = os.getenv("HISTFILE")
    if not histfile:
        return

    try:
        readline.write_history_file(histfile)
    except IOError:
        pass

def main():
    # Loads history on startup
    load_history()
    
    try:
        while True:
            try:
                user_input = input("$ ")
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

            if "|" in parts:
                pipeline_cmds = parse_pipeline(parts)
                run_pipeline(pipeline_cmds)
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
    finally:
        # Saves history on exit
        save_history()

if __name__ == "__main__":
    main()
