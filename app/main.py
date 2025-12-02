import os
import sys


def main():
    while True:
        sys.stdout.write("$ ")

        # Wait for user input
        command = input()
        if command == "exit":
            break
        if command.startswith("echo "):
            _, message = command.split(" ", 1)
            print(message)
            continue
        if command.startswith("type "):
            _, cmd = command.split(" ", 1)
            # Check cmd sequence:
            # 1. Check if cmd is a builtin shell command
            # 2. Go through every directory in PATH
            # 3. Mark command as not found
            if cmd in ["echo", "exit", "type"]:
                print(f"{cmd} is a shell builtin")
            else:
                PATH = os.getenv("PATH")
                for dir in PATH.split(os.pathsep):
                    # 1. Check if a file with the command name exists.
                    full_path = os.path.join(dir, cmd)
                    if os.path.exists(full_path):
                        # 2. Check if the file has execute permissions.
                        if os.access(full_path, os.X_OK):
                            # 3. If the file exists and has execute permissions, print <command> is <full_path> and stop.
                            print(f"{cmd} is {full_path}")
                            break
                        else:
                            # 4. If the file exists but lacks execute permissions, skip it and continue to the next directory.
                            continue
                print(f"{cmd}: not found")
            continue
        print(f"{command}: command not found")


if __name__ == "__main__":
    main()
