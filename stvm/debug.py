import datetime
from cmd import Cmd
from pprint import pprint
from .vm import VM, DebugException


class STVMDebugger(Cmd):
    def __init__(self, vm, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.intro = 'Experimental SmalltalkVM debugger\n'
        self.intro += f'Loaded image: {vm.image.file.name}\n'
        self.intro += f'Directory: {vm.image.file.parent}\n'
        self.intro += f'Image VM version: {vm.image.image_version}\n'
        self.intro += f'Fetching active context: "{vm.current_context.compiled_method.selector.as_text()}"\n'
        self.prompt = '? > '
        self.vm = vm
        self.cmdqueue = ['stack', 'list']

    def do_untilswith(self, arg):
        """
        Runs the VM until a process switch is performed (disabled)
        """
        process = self.vm.active_process
        while process is self.vm.active_process:
            self.vm.decode_execute(self.vm.fetch())
        self.do_stack("")
        self.do_list("")
        print(f"<*> Process {self.vm.active_process.display()}")

    def do_untilerror(self, arg):
        """
        Runs the VM until an error occurs, and go back to the previous context, before the send is executed.
        """
        try:
            while True:
                self.vm.decode_execute(self.vm.fetch())
        except DebugException as e:
            print(f"{colors.fg.red}Stopped on exception >> {e} in {self.vm.current_context.compiled_method.selector.as_text()}")
            print(colors.reset)
            current = self.vm.current_context
            self.do_stack("")
            self.do_list("")
        except Exception as e:
            try:
                self.do_list("")
                self.do_stack("")
            except Exception:
                print("Error in displaying the compiled method or the stack")
                import ipdb; ipdb.set_trace()

            print(f"{colors.fg.red}Stopped on exception >> {e} in {self.vm.current_context.compiled_method.selector.as_text()}")
            print("Going to the previous context before the send")
            print(colors.reset)
            current = self.vm.current_context
            sender = current.previous
            sender_pc = self.sender_pc(current)
            sender.pc = sender_pc
            sender.stack.extend(current.stack[:current.compiled_method.num_args])
            self.vm.current_context = sender
            self.do_stack("")
            self.do_list("")


    def sender_pc(self, context):
        sender = context.previous
        current_pc = sender.pc
        cm = sender.compiled_method
        if cm.raw_slots[current_pc - 1] in [*range(176, 208), *range(208, 256)]:
            return current_pc - 1
        if cm.raw_slots[current_pc - 2] in [131, 133, 134]:
            return current_pc - 2
        if cm.raw_slots[current_pc - 3] == 132:
            return current_pc - 3
        import ipdb; ipdb.set_trace()



    def do_step(self, arg):
        """
        Performs a step-into
        """
        self.vm.decode_execute(self.vm.fetch())
        self.do_stack("")
        self.do_list("")

    def do_stop(self, arg):
        """
        Stops on a bytecode number
        arg:     the number bytecode
        example: stop 139
        """
        bc = int(arg)
        current = self.vm.fetch()
        while current != bc:
            self.vm.decode_execute(current)
            current = self.vm.fetch()
        self.do_stack("")
        self.do_list("")

    def do_break(self, arg):
        """
        Break on a method execution
        arg:     the selector
        example: break +
        """
        name = arg.strip()
        while self.vm.current_context.compiled_method.selector.as_text() != name:
            self.vm.decode_execute(self.vm.fetch())
        self.do_stack("")
        self.do_list("")

    def do_time(self, arg):
        """
        Time how many bytecode are executed in 1 second
        arg: if none 1s otherwise, the number of seconds.
             used to perform rough benches
        """
        arg = arg or 1
        s = float(arg)
        end = datetime.datetime.now() + datetime.timedelta(seconds=s)
        count = 0
        while end > datetime.datetime.now():
            count += 1
            self.vm.decode_execute(self.vm.fetch())

        purple = colors.fg.purple
        yellow = colors.fg.yellow
        reset = colors.reset
        grey = colors.fg.darkgrey
        print(f"{purple}{count}{yellow} bytecodes executed in {grey}{s}s{reset}")

    def do_continue(self, arg):
        """
        Continue execution. Currently, will stop when the execution is a little bit too long (too many bytecode are executed).
        The limit is 500000, but a new number can be passed as argument
        """
        limit = 500000 if not arg else int(arg)
        try:
            count = 0
            a = datetime.datetime.now()
            while True:
                self.vm.decode_execute(self.vm.fetch())
                count += 1
                if count > limit:
                    b = datetime.datetime.now()
                    raise StopIteration(f"Looping too long {b-a}")
        except Exception as e:
            try:
                self.do_list("full")
                self.do_stack("")
            except Exception:
                import ipdb; ipdb.set_trace()

            print(f"{colors.fg.red}Stopped on exception >> {e}")
            print(colors.reset)

    def do_next(self, arg):
        """
        Performs a "step over"
        """
        context = self.vm.current_context
        past_ctx = []
        while context:
            past_ctx.append(context)
            context = context.sender
        while "not same context":
            self.vm.decode_execute(self.vm.fetch())
            if self.vm.current_context in past_ctx:
                break
        self.do_stack("")
        self.do_list("")

    def do_metadebug(self, arg):
        """
        Launch the python debugger (IPDB) here
        """
        context = self.vm.current_context
        cm = context.compiled_method
        self.do_stack("")
        self.do_list("")
        import ipdb; ipdb.set_trace()

    def do_list(self, arg):
        """
        Displays the method bytecode set.
        arg: if none, only +-5 bytecode are displayed from the program counter
             if "full", all the method is displayed
        """
        context = self.vm.current_context.adapt_context()
        return self.print_cm(context, arg)

    def print_cm(self, context, arg):
        cm = context.compiled_method
        bc_start = cm.initial_pc
        receiver_class = context.receiver.class_.name
        selector = cm.selector.as_text()
        print(f"{colors.fg.purple}{receiver_class}>>#{selector}{colors.reset}")

        size = cm.size() - cm.trailer.size
        if arg != "full":
            start = bc_start if context.pc - 5 < bc_start else context.pc - 5
            stop = size if context.pc + 5 > size else context.pc + 5
        else:
            start = bc_start
            stop = size
        if start > bc_start:
            print(f"{colors.fg.yellow}    ...")
        i = bc_start
        while i < start:
            bc_class = self.vm.bytecodes_map.get(cm.raw_data[i])
            i += bc_class.display_jump

        while i < stop:
            bc = cm.raw_data[i]
            active = context.pc == i
            bc_class = self.vm.bytecodes_map.get(bc)
            bc_repr = bc_class.display(bc, context, self.vm, active=active, position=i)
            bc_value = bc
            for j in cm.raw_data[i+1:i+bc_class.display_jump]:
                bc_value = (bc_value << 8) + j
            indic = f"{colors.fg.green}*" if active else f"{colors.fg.yellow} "
            line = f"{indic}   {i:3}    <{bc_value:02X}>  {bc_repr}  ({bc})"
            print(line)
            i += bc_class.display_jump
        if stop < size:
            print(f"{colors.fg.yellow}    ...")
        print(colors.reset)


    def do_stack(self, arg):
        """
        Displays the current stack
        """
        context = self.vm.current_context.adapt_context()
        self.print_stack(context, arg)

    def print_stack(self, context, arg):
        stack = context.stack
        if arg.startswith("top"):
            self.navigate(stack[-1], arg[3:])
            return
        print(f"{colors.fg.purple}Context stack")
        if not stack:
            print(f"    {colors.fg.orange}empty   -->")
            return
        print(f"    {colors.fg.orange}top     -->  {stack[-1].display()}")
        sub = stack[-2::-1]
        size = len(sub)
        args = context.compiled_method.num_args
        temps = context.compiled_method.num_temps
        for i, e in enumerate(sub):
            i = size - i -1
            prefix = f"    {colors.fg.darkgrey}             "
            if i < args:
                prefix = f"    {colors.fg.lightblue}arg  {i:2} -->  "
            elif i < temps:
                prefix = f"    {colors.fg.cyan}temp {i:2} -->  "
            print(f"{prefix}{e.display()}")
        print(colors.reset)

    def do_context(self, arg):
        """
        Displays the current context
        """
        args = arg.strip()
        context = self.vm.current_context
        if args:
            depth = int(args)
            for i in range(depth):
                context = context.previous
            self.print_stack(context, "")
            self.print_cm(context, "")
            return
        self.print_context(context, arg)

    def print_context(self, context, arg):
        print(f"Context  {context.display()}")
        if context.stcontext:
            print(f"allocated context {context.stcontext.display()}")
        print(f"home     {context.home.display()}")
        print("method  ", context.compiled_method.selector.as_text())
        if context.closure is None:
            print("closure   nil")
        else:
            print("closure ", context.closure.display())
        print("sender  ", context.sender.display())
        print("receiver", context.receiver.display())
        print("stack    [", *[s.display() for s in context.stack], ']')
        print("args     [", *[s.display() for s in context.args], ']')
        print("temps    [", *[s.display() for s in context.temps], ']')
        print("pc       ", context.pc)

    def do_active_process(self, arg):
        """
        Displays the active process
        """
        process = self.vm.active_process
        self.navigate(process, arg)

    def do_receiver(self, arg):
        """
        Displays the receiver.
        It is possible to navigate slots of the object.
        example: receiver slot 1
                 receiver slot 0 slot 2
        """
        context = self.vm.current_context
        receiver = context.receiver
        self.navigate(receiver, arg)

    def do_sender(self, arg):
        context = self.vm.current_context
        sender = context.sender
        s = sender
        while s != self.vm.memory.nil:
            self.print_context(s, "")
            print()
            s = s.sender

    def do_method(self, arg):
        """
        Displays the current compiled method
        """
        cm = self.vm.current_context.compiled_method
        self.navigate(cm, arg)

    def navigate(self, receiver, arg):
        args = [a for a in arg.strip().split(" ") if a]
        while args:
            if receiver.kind in range(9, 24):
                print(f"{colors.fg.red}Cannot navigate slots of Indexable objects{colors.reset}")
                break
            if receiver.kind < 0:
                print(f"{colors.fg.red}Cannot navigate slots of Immediate {colors.reset}")
                break
            if args[0] == "slot":
                number = args[1]
                receiver = receiver.slots[int(number)]
                args = args[2:]
            elif args[0] == "instvar":
                number = args[1]
                receiver = receiver.instvars[int(number)]
                args = args[2:]
            elif args[0] == "array":
                number = args[1]
                receiver = receiver.array[int(number)]
                args = args[2:]
            elif args[0] == 'class':
                receiver = receiver.class_
                args = args[1:]
            elif args[0] == "literal":
                number = args[1]
                receiver = receiver.literals[int(number)]
                args = args[2:]

        self.print_object(receiver)

    def print_object(self, receiver):
        print("object", receiver.display())
        print("object type", receiver.__class__.__name__, "kind", receiver.kind)
        print("class", receiver.class_.name)
        print("address", receiver.address)
        if receiver.kind < 0:
            return
        if receiver.kind in range(24, 32):
            print("selector", receiver.selector.as_text())
            print("literals")
            for i, e in enumerate(receiver.literals):
                print(f"{i:3}   {e.display()}")
            return
        print("slots")
        if receiver.kind in range(9, 24):
            for i in range(len(receiver)):
                if i > 0 and i % 8 == 0:
                    print()
                print("", hex(receiver[i]), end="")
            print()
            print(f'text "{receiver.as_text()}"')
            print(f'uint {receiver.as_int()}')
            return
        for i in range(len(receiver.slots)):
            print(f"{i:2}   ", receiver[i].display())
        if hasattr(receiver, "instvars"):
            print("instvar in slots")
            for i in range(len(receiver.instvars)):
                print(f"{i:2}   ", receiver.instvars[i].display())
        if hasattr(receiver, "array"):
            print("array in slots")
            for i in range(len(receiver.array)):
                print(f"{i:2}   ", receiver.array[i].display())

    def do_print(self, arg):
        if arg == "receiver":
            self.do_receiver("")
        elif arg == "context":
            self.do_print_context("")

    def do_object(self, arg):
        """
        Displays the content of an object at an address.
        It is possible to navigate slots of the object.
        example: object 0x1234 slot 1
                 object 0x1234 slot 0 slot 2
        """
        args = [a for a in arg.strip().split(" ") if a]
        address = int(args[0], 0)
        obj = self.vm.memory.object_at(address)
        self.navigate(obj, " ".join(args[1:]))

    def do_where(self, arg):
        """
        Displays the stack of contexts.
        arg: if none, the full stack is displayed
             if a number, details about this context is displayed
        """
        context = self.vm.current_context
        current = context
        nil = self.vm.memory.nil
        i = 0
        while context != nil:
            line = colors.fg.purple
            selector = context.compiled_method.selector.as_text()
            indic = f"{colors.reset}{colors.fg.purple} "
            if context is current:
                indic = f"{colors.bold}*"
            line += f"{i:3} {indic}   #{selector} rcvr={context.receiver.display()}"
            # line += f"        {context.display()}"
            print(line)
            context = context.sender
            i += 1
        # print(f"Depth {i}")
        print(colors.reset)

    def do_quit(self, arg):
        "Quit the VM debugger"
        return True

    do_EOF = do_quit
    do_s = do_step
    do_l = do_list
    do_n = do_next

class colors:
    reset='\033[0m'
    bold='\033[01m'
    disable='\033[02m'
    underline='\033[04m'
    reverse='\033[07m'
    strikethrough='\033[09m'
    invisible='\033[08m'
    class fg:
        black='\033[30m'
        red='\033[31m'
        green='\033[32m'
        orange='\033[33m'
        blue='\033[34m'
        purple='\033[35m'
        cyan='\033[36m'
        lightgrey='\033[37m'
        darkgrey='\033[90m'
        lightred='\033[91m'
        lightgreen='\033[92m'
        yellow='\033[93m'
        lightblue='\033[94m'
        pink='\033[95m'
        lightcyan='\033[96m'
    class bg:
        black='\033[40m'
        red='\033[41m'
        green='\033[42m'
        orange='\033[43m'
        blue='\033[44m'
        purple='\033[45m'
        cyan='\033[46m'
        lightgrey='\033[47m'

if __name__ == '__main__':
    STVMDebugger(VM.new('Pharo8.0.image')).cmdloop()
    # STVMDebugger(VM.new('Cuis5.0-4426.image')).cmdloop()
    # STVMDebugger(VM.new('ns-2020-03-02.64.image')).cmdloop()
    # STVMDebugger(VM.new('Pharo9.0-SNAPSHOT-64bit-12edded.image')).cmdloop()
