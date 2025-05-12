from datetime import datetime

from phenix_apps.apps.scorch import ComponentBase
from phenix_apps.common import utils

class Record(ComponentBase):
    
    def __init__(self):
        ComponentBase.__init__(self, 'record')
        self.execute_stage()
    
    def configure(self):
        self.__run('configure')


    def start(self):
        self.__run('start')


    def stop(self):
        self.__run('stop')


    def cleanup(self):
        self.__run('cleanup')

    
    def __run(self, stage):
        nodes = self.extract_node_names()
        vms   = self.metadata.get('vms', [])

        mm = self.mm_init()

        for vm in vms:
            if vm.hostname not in nodes:
                self.eprint(f'{vm.hostname} is not in the topology')
                continue
            
            commands = vm.get(stage, [])

            if len(commands) == 0:
                self.print(f'{vm.hostname} has no commands for stage {stage}')
                continue
            
            for cmd in commands:
                if cmd.action == 'start':
                    filename = cmd.get('filename', None)
                    if not filename:
                        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                        filename = f"{vm.hostname}_{timestamp}.fb"
                    filepath = f"{self.base_dir}/{filename}"

                    mm.vnc_record("fb", vm.hostname, filepath)
                    
                    self.print(f'recording started for vm {vm.hostname}, saving to {filepath}')
                
                elif cmd.action == 'stop':
                    mm.vnc_stop(vm.hostname, "fb")
                    self.print(f'recording stopped for vm {vm.hostname}')
                
                else:
                    self.print(f'record component \'action\' {cmd.action} for {vm.hostname} not defined, use \'start\' or \'stop\'')

def main():
    Record()


if __name__ == '__main__':
    main()
