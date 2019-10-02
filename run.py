from stvm import VM

vm = VM()
# vm.open_image("bootstrap.image")
# vm.open_image("bootstrap2.image")
# vm.open_image("tmp/Pharo.image")
# vm.open_image("Pharo-32.image")
vm.open_image("Pharo.image")

vm.execute()
