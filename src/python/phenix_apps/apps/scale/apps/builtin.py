from phenix_apps.apps.scale.apps import register_app_class

class Builtin:
    def __init__(self, per_node, config):
        self.per_node = per_node
        self.count    = config.get('count', 42)

    def nodes(self):
        nodes, extra = divmod(self.count, self.per_node) # (x//y, x%y)
        nodes = nodes + 1 if extra else nodes

        return nodes

    def containers(self, node):
        containers = []
        stop       = self.per_node

        if node >= self.nodes() -1:
            stop = self.count % self.per_node

        for i in range(0, stop):
            containers.append(f'builtin-{node * self.per_node + i}')

        return containers


register_app_class('builtin', Builtin)