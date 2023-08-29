import os

from phenix_apps.apps   import AppBase
from phenix_apps.common import logger, utils

#  apps:
#  - name: helics
#    metadata:
#      broker:
#        root: <ip:port>    # optional location of root broker (assumed to already be in topology)
#        log-level: summary # log level to apply to every broker created

class Helics(AppBase):
  def __init__(self):
    AppBase.__init__(self, 'helics')

    self.helics_dir = f"{self.exp_dir}/helics"
    os.makedirs(self.helics_dir, exist_ok=True)

    self.execute_stage()

    # We don't (currently) let the parent AppBase class handle this step
    # just in case app developers want to do any additional manipulation
    # after the appropriate stage function has completed.
    print(self.experiment.to_json())


  def pre_start(self):
    logger.log('INFO', f'Starting user application: {self.name}')

    # broker hosts --> {endpoint: <ip:port>, fed-count: <num>}
    brokers = {}
    federates = self.extract_annotated_topology_nodes('helics/federate')

    for fed in federates:
      configs = fed['annotations'].get('helics/federate', [])

      for config in configs:
        broker = config.get('broker', {})
        count  = config.get('fed-count', 1)

        hostname = broker.get('hostname', None)
        endpoint = broker.get('endpoint', None)

        entry = brokers.get(hostname, {'endpoint': endpoint, 'fed-count': 0})
        entry['fed-count'] += count

        brokers[hostname] = entry


    if len(brokers) == 1:
      pass
    else:
      pass # TODO: check for or add broker VM to topology

    templates = utils.abs_path(__file__, 'templates/')

    for hostname, config in brokers.items():
      start_file = f'{self.helics_dir}/{hostname}-broker.sh'

      cfg = {
        'feds':      config['fed-count'],
        'log-level': self.metadata.get('broker', {}).get('log-level', 'summary'),
        'log-file': self.metadata.get('broker', {}).get('log-file', '/var/log/helics-broker.log'),
      }

      if len(brokers) > 1:
        cfg['parent'] = self.metadata.get('broker', {}).get('root', '127.0.0.1')
        cfg['endpoint'] = config['endpoint']

      with open(start_file, 'w') as f:
        utils.mako_serve_template('broker.mako', templates, f, cfg=cfg)

      self.add_inject(hostname=hostname, inject={'src': start_file, 'dst': '/etc/phenix/startup/90-helics-broker.sh'})

def main():
  Helics()


if __name__ == '__main__':
  main()
