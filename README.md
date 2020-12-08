# STVM (SmallTalkVirtualMachine)

STVM (name will probably change in the future), is an effort to make a kind of cog-like virtual machine in Python.
The idea behind is to understand well how a Smalltalk VM works, the Spur memory management works and make it able to run (probably very very slowly) Pharo/Cuis/Squeak images.
The focus is not on performances, but on flexibility for quick development/modifications and runtime modifications.


## State

Currently, the project is still in a PoC mode, no image is running properly, but a debugger is here to step through an image execution.
Only 64bits images are supported at the moment and <= Pharo8 (no sista bytecode have been implemented).

Currently, it provides:

* an image reader for 64bits images
* an abstraction of low-level spur objects with quick accesses to slots/array/instvars...
* an easy way to register new abstractions for low-level objects (cf. the objects classes in `specials.py`)
* a first implementation of bytecode and an easy way to register new bytecodes
* a first implementation of some primitives and an easy way to register new primitives
* some plugins implementations and an easy way to register new plugins
* a dumb memory allocator
* no GC (currently)
* a textual bytecode debugger


## Install

The project includes a `Pipfile`, you can then just

```shell
$ pipenv install
```

which will create a virtualenv and grab all the required dependencies.


## Run the debugger

You can just call the `debug.py` file with a 64bits image file as parameter.

```shell
$ python debug.py Pharo8.0.image  # or whatever image name you are using
```


## How to

This section will quickly present how you can perform some basic operations on the VM.


### Open an image file

Opening an image file is pretty forward:

```python
from stvm.image64 import Image

image = Image('myimagefile')
```

### Get special objects from an image

You can get a number of objects directly from an image.
You have to build a `VMMemory` first from the image:

```python
from stvm.image64 import Image

memory = Image('myimagefile').as_memory()
```

Then, you can access some objects directly:

```python
special = memory.special_object_array
nil = memory.special_object_array[0]
false = memory.special_object_array[1]
true = memory.special_object_array[2]
...

class_table = memory.class_table
smallfloat64 = class_table[4]

# or
nil = memory.nil
false = memory.false
smalltalk = memory.smalltalk
...
```

You can also access to the object at an address easily

```python
obj = memory.object_at(an_address)

# navigating to it's class
c = obj.class_

# and to the superclass of this class
sc = c[0]  # or c.slots[0]

# asking for the name
print(sc.name)
```

Each navigation in an object resolves to the object the slot points to.


### Create a new VM instance

Creating a VM is done using `new()` on a `VM`:

```python
from svtm import VM

vm = VM.new('myimagefile')
```

You can then step using the classical `fetch/execute`:

```python
bytecode = vm.fetch()
vm.decode_execute(bytecode)
```


### Register a new Bytecode

A bytecode is implemented by proposing a new class.
This class needs to implement two methods and to use a special decorator:

```python
@bytecode(555)
class MyNewBytecode(object):
  def execute(bytecode, context, vm):
    ... # here is the execution of my bytecode and the pc incrementation

  def display(bytecode, context, vm, position=None, active=False):
    ... # here is how it will be displayed in the debugger or for other purpose
```

Each method gets as parameter:

* the number representing the bytecode that is executed (or will be)
* the context in which it is executed
* the current virtual machine running it
* the position in the bytecode stream (for display)
* the fact that the current bytecode is active (will be executed) or not (for debug purpose)

You can also register many numbers for a bytecode:

```python
@bytecode(range(555, 666))
class MyNewBytecode(object):
  ...
```

This will register `MyNewBytecode` for numbers 555 to 665.


### Create a new BytecodeMap and register Bytecode for it

Each bytecode is registed in a BytecodeMap.
To create your own BytecodeMap, you need to inherits from `ByteCodeMap` and to explicitly says that you want to register a bytecode for this map:

```python
from stvm.bytecodes import ByteCodeMap

class MyByteCodeMap(ByteCodeMap):
  ...

@bytecode(134, register=MyByteCodeMap)
class MyBytecode(object):
  ...
```

You then use this bytecode map in your VM:

```python
from stvm import VM
from svtm.image64 import Image

vm = VM(Image('myimagefile'), bytecodes_map=MyByteCodeMap)
```

You can also modify (at runtime or not) bytecodes from any bytecode map and change them for a VM instance.


### Register a new Primitive

Registering a new primitive is done in the `primitives.py` file with the `@primitive` decorator.

```python
@primitive(4444)
def myprimitive(rcvr, param1, context, vm):  #  param1 depends on your original method parameter number, context and vm need to be here
  ...
```
You can see the `primitives.py` file for more examples.

Notes:

* if a primitive returns `None`, the receiver is automatically pushed on the stack.
* if a primitive requires a context activation, it has to be said in the decorator (check primitive 83 `perform`) for example
* if a primitive returns `True` or `False`, they are automatically transformed in `true` or `false` from the VM


### Register a new Plugin

Plugins are regular python module that need to be placed in the `plugins` directory.
As for the primitives, they are receiving the arguments depending on the number of arguments of the original method.
Here is how is implemented the `primitiveGetCurrentWorkingDirectory` function


```python
import os
from ..utils import to_bytestring

def primitiveGetCurrentWorkingDirectory(cls, context, vm):
    return to_bytestring(os.getcwd(), vm)
```

## Dependencies

Currently, no dependency is really needed, but some primitives and plugins requires `python-xlib` (so, currently only linux) and `ipdb` for the "dev" mode.


## Tests

There is currently none, they will come in time with a refactoring of the API of everything (that grows organically).
