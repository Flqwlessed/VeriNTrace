import heapq
import itertools
import time
from collections import OrderedDict, deque
from threading import Lock


class PriorityQueue:
    def __init__(self):
        self.heap = []
        self.counter = itertools.count()

    def push(self, item, priority):
        heapq.heappush(self.heap, (-priority, next(self.counter), item))

    def pop(self):
        return heapq.heappop(self.heap)[2] if self.heap else None

    def __len__(self):
        return len(self.heap)


class DirectedGraph:
    def __init__(self):
        self.adjacency = {}

    def add_node(self, node):
        self.adjacency.setdefault(node, set())

    def add_edge(self, source, target):
        self.add_node(source)
        self.add_node(target)
        self.adjacency[source].add(target)

    def bfs(self, start):
        parent, depth, queue = {start: None}, {start: 0}, deque([start])
        while queue:
            node = queue.popleft()
            for child in sorted(self.adjacency.get(node, ())):
                if child not in parent:
                    parent[child], depth[child] = node, depth[node] + 1
                    queue.append(child)
        return parent, depth

    def path(self, start, end):
        parent, _ = self.bfs(start)
        if end not in parent:
            return []
        path = []
        while end is not None:
            path.append(end)
            end = parent[end]
        return path[::-1]


class UnionFind:
    def __init__(self, ids):
        self.parent = {x: x for x in ids}

    def find(self, x):
        while x != self.parent[x]:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.parent[b] = a


class TTLCache:
    def __init__(self, capacity=100, ttl=900):
        self.capacity, self.ttl = capacity, ttl
        self.items, self.lock = OrderedDict(), Lock()

    def get(self, key):
        with self.lock:
            if key not in self.items:
                return None
            expires, value = self.items.pop(key)
            if expires <= time.monotonic():
                return None
            self.items[key] = (expires, value)
            return value

    def put(self, key, value):
        with self.lock:
            self.items[key] = (time.monotonic() + self.ttl, value)
            self.items.move_to_end(key)
            while len(self.items) > self.capacity:
                self.items.popitem(last=False)
