# Source: https://gist.github.com/mdsrosa/c71339cb23bc51e711d8
#-------------------------------------------------------------------------------
# Name:        Dijkstra.py
# Purpose:     Dijkstra algoritme voor het bepalen van kortste route in een Graph.
#              Gebruikt in o.a. ShortestRoute.py (Geoinfo Tools - RouteAnalyse)
# Author:      bart kropf
#
# Created:     05-12-2016
# Copyright:   (c) BKGIS 2016
#-------------------------------------------------------------------------------

from collections import defaultdict, deque

class Graph(object):
    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(list)
        self.distances = {}

    def add_node(self, value):
        self.nodes.add(value)

    def add_edge(self, from_node, to_node, distance):
        self.edges[from_node].append(to_node)
        self.edges[to_node].append(from_node)
        self.distances[(from_node, to_node)] = distance


def dijkstra(graph, initial):
    visited = {initial: 0}
    path = {}

    nodes = set(graph.nodes)

    while nodes:
        min_node = None
        for node in nodes:
            if node in visited:
                if min_node is None:
                    min_node = node
                elif visited[node] < visited[min_node]:
                    min_node = node
        if min_node is None:
            break

        nodes.remove(min_node)
        current_weight = visited[min_node]

        for edge in graph.edges[min_node]:
            try:
                weight = current_weight + graph.distances[(min_node, edge)]
            except:
                continue
            if edge not in visited or weight < visited[edge]:
                visited[edge] = weight
                path[edge] = min_node

    return visited, path


def shortest_path(graph, origin, destination):
    visited, paths = dijkstra(graph, origin)
    full_path = deque()
    _destination = paths[destination]

    while _destination != origin:
        full_path.appendleft(_destination)
        _destination = paths[_destination]

    full_path.appendleft(origin)
    full_path.append(destination)

    return visited[destination], list(full_path)

# Voor stand-alone testen...
if __name__ == '__main__':
    graph = Graph()

    for node in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
        graph.add_node(node)
    graph.add_edge('A', 'B', 10)
    graph.add_edge('A', 'C', 20)
    graph.add_edge('B', 'D', 45)
    graph.add_edge('C', 'E', 30)
    graph.add_edge('B', 'E', 50)
    graph.add_edge('D', 'E', 30)
    graph.add_edge('E', 'F', 5)
    graph.add_edge('F', 'G', 2)

##    # voorbeeld RWZI A1 met rioolgemalen op niveau B en C.
##    for node in ['A1', 'B1', 'B2', 'B3', 'C1', 'C2', 'C3', 'C4']:
##        graph.add_node(node)
##    graph.add_edge('A1', 'B1', 10)
##    graph.add_edge('A1', 'B2', 10)
##    graph.add_edge('A1', 'B3', 10)
##    graph.add_edge('B1', 'C1', 20)
##    graph.add_edge('B2', 'C2', 20)
##    graph.add_edge('B3', 'C3', 20)
##    graph.add_edge('B3', 'C4', 25)

    start_node = 'A'
    end_node = 'F'
    print("shortest path {} -> {}: {}".format(start_node, end_node, shortest_path(graph, start_node, end_node))) # vb output: (25, ['A', 'B', 'D'])
    edges = dijkstra(graph, start_node)[1]
    nodes = dijkstra(graph, start_node)[0]
    print ("edges: {}".format(edges))
    print ("nodes: {}".format(nodes))
    print "{} edges".format(len(edges))

    ##print (graph.nodes)