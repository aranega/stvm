import sys
from stvm import VM
from stvm import STVMDebugger


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Missing argument: image file")
        exit(1)

    STVMDebugger(VM.new(sys.argv[1])).cmdloop()
