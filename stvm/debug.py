from cmd import Cmd
from pprint import pprint
from vm_new import VM


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
        self.cmdqueue = ['list']

    def do_step(self, arg):
        self.vm.decode_execute(self.vm.fetch())
        self.do_list("")

    def do_stop(self, arg):
        bc = int(arg)
        current = self.vm.fetch()
        while current != bc:
            self.vm.decode_execute(current)
            current = self.vm.fetch()
        self.do_list("")

    def do_continue(self, arg):
        try:
            while True:
                self.vm.decode_execute(self.vm.fetch())
        except Exception as e:
            try:
                self.do_list("full")
            except Exception:
                import ipdb; ipdb.set_trace()

            print(f"{colors.fg.red}Stopped on exception >> {e}")
            print(colors.reset)

    def do_next(self, arg):
        context = self.vm.current_context
        try:
            while "not same context":
                self.vm.decode_execute(self.vm.fetch())
                if self.vm.current_context is context:
                    break
        except Exception:
            self.do_print_context("")
            self.do_metadebug("")
        self.do_list("")

    def do_metadebug(self, arg):
        context = self.vm.current_context
        cm = context.compiled_method
        self.do_list("")
        import ipdb; ipdb.set_trace()


    def do_list(self, arg):
        context = self.vm.current_context
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


    def do_print_context(self, arg):
        context = self.vm.current_context
        print("Current context")
        print("method  ", context.compiled_method.selector.as_text())
        print("stack:   [", *[s.display() for s in context.stack], ']')
        print("args:    [", *[s.display() for s in context.args], ']')
        print("temps:   [", *[s.display() for s in context.temps], ']')
        print("PC", context.pc)
        print("method  size", context.compiled_method.size())
        print("method  size", len(context.compiled_method))
        print("method  bclen", len(context.compiled_method.bytecodes))


    def do_where(self, arg):
        context = self.vm.current_context
        current = context
        while context != None:
            line = colors.fg.purple
            selector = context.compiled_method.selector.as_text()
            indic = f"{colors.reset}{colors.fg.purple} "
            if context is current:
                indic = f"{colors.bold}*"
            line += f"{indic}   #{selector} rcvr=<0x{id(context.receiver):X}>"
            print(line)
            context = context.previous
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
