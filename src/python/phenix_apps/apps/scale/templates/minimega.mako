clear vm config
vm config vcpus ${config['VCPU']}
vm config memory ${config['MEMORY']}
vm config net ${config['NET_STR']}
vm config filesystem ${config['FILESYSTEM']}
vm config init /init

% for name in config['CONTAINERS']:
vm launch container ${name}
% endfor

vm start all

% for i, name in enumerate(config['CONTAINERS']):
cc filter name=${name}
  % for idx, net in enumerate(config['NETS']):
cc exec ip addr add ${str(net['addr']+i)}/${net['prefix']} dev veth${idx}
  % endfor
  % if config['NETS'] and config['GATEWAY']:
cc exec ip route add default via ${config['GATEWAY']}
  % endif
% endfor
