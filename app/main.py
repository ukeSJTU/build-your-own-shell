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
            if cmd in ["echo", "exit", "type"]:
                print(f"{cmd} is a shell builtin")
            else:
                print(f"{cmd}: not found")
            continue
        print(f"{command}: command not found")


if __name__ == "__main__":
    main()
