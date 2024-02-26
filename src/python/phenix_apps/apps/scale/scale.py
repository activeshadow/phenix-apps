import os, sys

import ipaddress as ip

from itertools import islice

from phenix_apps.apps   import AppBase
from phenix_apps.common import logger, utils, settings

from phenix_apps.apps.scale.builtin import Builtin

import minimega

# spec:
#   scenario:
#     apps:
#     - name: scale
#       metadata:
#         node_template:
#           cpu: 8            # CPU count for each VM
#           memory: 32768     # memory for each VM
#           image: scaler.qc2 # disk image for each VM
#           start_scripts:    # custom start scripts for each VM
#           - path/to/inject/startup_script1
#           - path/to/inject/startup_script2
#         containers: 100 # number of containers per VM
#         container_template:
#           cpu: 1      # CPU count for each container
#           memory: 512 # memory for each container
#           networks:   # networks to configure in each container
#           - name: MGMT
#             network: 172.16.99.0/16
#           - name: EXP
#             network: 10.1.99.0/16
#           gateway: MGMT # default route to use in containers (IP or tapped VLAN name)
#           rootfs: tar:rootfs.tgz
#         app:
#           name: builtin
#           count: 42

class Scale(AppBase):
    def __init__(self):
        AppBase.__init__(self, 'scale')

        self.app_dir = f"{self.exp_dir}/scale"
        os.makedirs(self.app_dir, exist_ok=True)

        self.files_dir = f"{settings.PHENIX_DIR}/images/{self.exp_name}/scale"
        os.makedirs(self.files_dir, exist_ok=True)

        self.profiles = self.metadata.get('profiles', [])

        if len(self.profiles) == 0:
            profile = self.metadata
            profile['name'] = 'default'

            self.profiles.append(profile)

        self.execute_stage()

        # We don't (currently) let the parent AppBase class handle this step
        # just in case app developers want to do any additional manipulation
        # after the appropriate stage function has completed.
        print(self.experiment.to_json())

    def __extract_tap_app(self):
        apps = self.experiment.spec.scenario.apps

        for app in apps:
            if app.name == 'tap':
                return app

        return None

    def __get_node_ip(self, hostname):
        node = self.extract_node(hostname)
        assert node

        addr = None

        if len(node.network.interfaces) > 0:
            if 'address' in node.network.interfaces[0]:
                addr = node.network.interfaces[0]['address']

        assert addr
        return addr

    def __process_networks(self, networks):
        net_str = ''
        nets    = []

        for net in networks:
            try:
                vlan_id  = getattr(self.experiment.status.vlans, net['name'])
                net_str += f"phenix,{vlan_id} "
            except AttributeError:
                logger.log('ERROR', f"VLAN not found: {net['name']}")

            net_iface = ip.IPv4Interface(net['network'])

            nets.append({
                'addr'   : net_iface.ip + 1,
                'prefix' : net_iface.network.prefixlen,
            })

        return (net_str, nets)

    def configure(self):
        logger.log('INFO', f'Configuring user app: {self.name}')

        for idx, profile in enumerate(self.profiles):
            profile_name = profile.get('name', str(idx))
            node_md      = profile.get('node_template', {})

            node_tmpl = {
                'type': 'VirtualMachine',
                'general': {
                    'hostname' : 'FIXME',
                    'vm_type'  : 'kvm'
                },
                'hardware': {
                    'os_type' : 'linux',
                    'vcpus'   : node_md.get('cpu', 8),
                    'memory'  : node_md.get('memory', 32768),
                    'drives'  : [
                        {'image': node_md.get('image', 'scaler.qc2')},
                    ]
                },
                'network': {
                    'interfaces': [
                        {
                            'name'  : 'eth0',
                            'type'  : 'ethernet',
                            'proto' : 'manual',
                            'vlan'  : '0' # causes all VLANs to be trunked into VM
                        }
                    ]
                }
            }

            app      = profile.get('app', {})
            app_name = app.get('name', 'builtin')
            per_node = profile.get('containers', 100)

            nodes = 0

            if app_name == 'builtin':
                count = app.get('count', 42)
                klass = Builtin(per_node, count)
                nodes = klass.nodes()
            else:
                logger.log('ERROR', f'invalid scale app name provided: {app_name}')
                sys.exit(1)

            for i in range(0, nodes):
                hostname = f"scale-profile-{profile_name}-{i}"
                node_tmpl['general']['hostname'] = hostname
                self.add_node(node_tmpl)

                startup_config = f'{self.app_dir}/{hostname}-startup.sh'
                mm_dir  = f'/tmp/miniccc/files/{self.exp_name}/scale'
                mm_file = f'{mm_dir}/{hostname}.mm'

                with open(startup_config, 'w') as f:
                    f.write(f"tar -C / \\\n")
                    f.write(f"  -xzf /ami-configs.tgz\n")
                    f.write("while [ ! -S /tmp/minimega/minimega ]; do sleep 1; done\n")
                    f.write(f"while [ ! -f {mm_file} ]; do sleep 1; done\n")
                    f.write("ovs-vsctl add-br phenix\n")
                    f.write("ovs-vsctl add-port phenix eth0\n")
                    f.write(f"mm read {mm_file}\n")
                    f.write("echo 'DONE!'\n")

                self.add_inject(
                    hostname = hostname,
                    inject = {
                        'src': startup_config,
                        'dst': '/etc/phenix/startup/999-scale.sh'
                    }
                )

                # custom user startup scripts to be inserted in each new scale node 
                start_scripts = profile.get('start_scripts', [])
                script_num    = 500

                for script in start_scripts:
                    script_num += 1

                    self.add_inject(
                        hostname = hostname,
                        inject = {
                            'src': script,
                            'dst': f'/etc/phenix/startup/{script_num}-script.sh'
                        }
                    )

        logger.log('INFO', f'Configured user app: {self.name}')

    def post_start(self):
        logger.log('INFO', f'Running post-start for user app: {self.name}')

        for idx, profile in enumerate(self.profiles):
            profile_name = profile.get('name', str(idx))

            cpu      = profile.get('container_template', {}).get('cpu', 1)
            memory   = profile.get('container_template', {}).get('memory', 512)
            net_info = profile.get('container_template', {}).get('networks', [])
            gateway  = profile.get('container_template', {}).get('gateway', None)
            rootfs   = profile.get('container_template', {}).get('rootfs', 'tar:rootfs.tgz')

            if net_info:
                # get list of networks to add as interfaces to containers;
                # returns a tuple: ('<minimega net string>', {<list of net dicts>})
                #   Ex. (
                #         'phenix,101 phenix,102',
                #         [{'addr': <ip.IPv4Address>, 'prefix': <int>), ...]
                #       )
                net_info = self.__process_networks(net_info)

                if gateway:
                    try: # assume gateway defined as IP address
                        gateway = str(ip.ip_address(gateway))
                    except: # assume gateway defined as tapped VLAN name
                        tap_app = self.__extract_tap_app()

                        if tap_app:
                            # get gateway from tap app
                            for tap in tap_app.metadata.get('taps', []):
                                if tap.get('vlan') != gateway: continue
                                gateway = str(ip.IPv4Interface(tap.ip).ip)

                            # ensure gateway is now an IP address (may not be if
                            # VLAN name provided isn't configured in the tap app)
                            try:
                                ip.ip_address(gateway)
                            except:
                                gateway = None # disable so template ignores it
                                logger.log(
                                    'ERROR',
                                    'VLAN specified for gateway is not tapped',
                                )
                        else:
                            logger.log(
                                'WARN',
                                'tap app not found: VLAN setting for gateway ignored'
                            )
                else:
                    logger.log('INFO', 'no default gateway defined for node(s)')
            else:
                logger.log('WARN', 'no networks defined for scale app')

            if not self.dryrun:
                mm = minimega.connect(namespace=self.exp_name)

            app      = profile.get('app', {})
            app_name = app.get('name', 'builtin')
            per_node = profile.get('containers', 100)

            klass = None
            nodes = 0

            if app_name == 'builtin':
                count = app.get('count', 42)
                klass = Builtin(per_node, count)
                nodes = klass.nodes()
            else:
                logger.log('ERROR', f'invalid scale app name provided: {app_name}')
                sys.exit(1)

            for i in range(0, nodes):
                hostname = f"scale-profile-{profile_name}-{i}"
                containers = klass.containers(i)
    
                mm_config = f'{self.files_dir}/{hostname}.mm'
                templates = utils.abs_path(__file__, 'templates/')

                cfg = {
                    'CONTAINERS' : containers,
                    'VCPU'       : cpu,
                    'MEMORY'     : memory,
                    'FILESYSTEM' : rootfs,
                    'HOSTNAME'   : hostname,
                    'NET_STR'    : net_info[0] if net_info else '',
                    'NETS'       : net_info[1] if net_info else [],
                    'GATEWAY'    : gateway,
                }
    
                with open(mm_config, 'w') as file_:
                    utils.mako_serve_template('minimega.mako', templates, file_, config=cfg)
    
                if not self.dryrun:
                    # can't inject in this stage - need to send with miniccc
                    mm.cc_filter(filter=f"name={hostname}")
                    mm.cc_send(mm_config)

                # increase all nets' starting IP for next loop
                for net in net_info[1]:
                    net['addr'] += len(containers)

        logger.log('INFO', f'Finished running post-start for user app: {self.name}')


def batched(iterable, chunk_size):
    iterator = iter(iterable)
    while chunk := tuple(islice(iterator, chunk_size)):
        yield chunk


def main():
    Scale()


if __name__ == '__main__':
    main()
