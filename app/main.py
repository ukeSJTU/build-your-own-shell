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
        print(f"{command}: command not found")


if __name__ == "__main__":
    main()
