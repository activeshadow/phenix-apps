class Builtin:
    def __init__(self, per_node, count):
        self.per_node = per_node
        self.count = count

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
