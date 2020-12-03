from cmd import Cmd
from pprint import pprint
from .vm_new import VM


class bcolors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'



class STVMDebugger(Cmd):
    def __init__(self, vm, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.intro = 'Experimental SmalltalkVM debugger\n'
        self.intro += f'Loaded image: {vm.image.filename}\n'
        self.intro += f'Image VM version: {vm.image.image_version}\n'
        self.intro += f'Fetching active context: "{vm.current_context.compiled_method.selector.as_text()}"\n'
        self.prompt = '? > '
        self.vm = vm
        self.cmdqueue = ['stack', 'list']

    # def cmdloop(self, intro=None):
    #     while True:
    #         try:
    #             super().cmdloop(intro="")
    #             break
    #         except KeyboardInterrupt:
    #             # self.do_stack("")
    #             # self.do_list("")
    #             ...

    def do_step(self, arg):
        self.vm.decode_execute(self.vm.fetch())
        self.do_stack("")
        self.do_list("")

    def do_stop(self, arg):
        bc = int(arg)
        current = self.vm.fetch()
        while current != bc:
            self.vm.decode_execute(current)
            current = self.vm.fetch()
        self.do_stack("")
        self.do_list("")

    def do_break(self, arg):
        name = arg.strip()
        while self.vm.current_context.compiled_method.selector.as_text() != name:
            self.vm.decode_execute(self.vm.fetch())
        self.do_stack("")
        self.do_list("")


    def do_continue(self, arg):
        try:
            count = 0
            import datetime
            a = datetime.datetime.now()
            while True:
                self.vm.decode_execute(self.vm.fetch())
                count += 1
                if count > 50000:
                    b = datetime.datetime.now()
                    raise StopIteration(f"Looping too long {b-a}")
        except Exception as e:
            try:
                self.do_list("full")
            except Exception:
                import ipdb; ipdb.set_trace()

            print(f"{colors.fg.red}Stopped on exception >> {e}")
            print(colors.reset)

    def do_next(self, arg):
        context = self.vm.current_context
        while "not same context":
            self.vm.decode_execute(self.vm.fetch())
            if self.vm.current_context is context:
                break
            if self.vm.current_context is context.sender:
                break
        self.do_stack("")
        self.do_list("")

    def do_metadebug(self, arg):
        context = self.vm.current_context
        cm = context.compiled_method
        self.do_stack("")
        self.do_list("")
        import ipdb; ipdb.set_trace()


    def do_list(self, arg):
        context = self.vm.current_context.adapt_context()
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
        context = self.vm.current_context.adapt_context()
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
        context = self.vm.current_context
        self.print_context(context, arg)

    def print_context(self, context, arg):
        print("Current context")
        print("method  ", context.compiled_method.selector.as_text())
        if context.closure is None:
            print("closure   nil")
        else:
            print("closure", context.closure.display())
        print("sender  ", context.sender.display())
        print("receiver", context.receiver.display())
        print("stack:   [", *[s.display() for s in context.stack], ']')
        print("args:    [", *[s.display() for s in context.args], ']')
        print("temps:   [", *[s.display() for s in context.temps], ']')
        print("PC", context.pc)

    def do_active_process(self, arg):
        process = self.vm.active_process
        self.navigate(process, arg)

    def do_receiver(self, arg):
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

    def navigate(self, receiver, arg):
        args = [a for a in arg.strip().split(" ") if a]
        while args:
            if receiver.kind in range(9, 24):
                print(f"{colors.fg.red}Cannot navigate slots of Indexable objects{colors.reset}")
                break
            if receiver.kind in (-1, -3):
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
        self.print_object(receiver)

    def print_object(self, receiver):
        print("receiver", receiver.display())
        print("object type", receiver.__class__.__name__, "kind", receiver.kind)
        print("class", receiver.class_.name)
        if receiver.kind in (-1, -3):
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


    def do_where(self, arg):
        context = self.vm.current_context
        current = context
        nil = self.vm.memory.nil
        i = 1
        while context != nil:
            line = colors.fg.purple
            selector = context.compiled_method.selector.as_text()
            indic = f"{colors.reset}{colors.fg.purple} "
            if context is current:
                indic = f"{colors.bold}*"
            line += f"{indic}   #{selector} rcvr={context.receiver.display()}"
            # line += f"        {context.display()}"
            print(line)
            context = context.sender
            i += 1
        print(f"Depth {i}")
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
