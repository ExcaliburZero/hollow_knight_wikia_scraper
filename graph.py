from dataclasses import dataclass
from typing import Dict, IO, Set


@dataclass
class DirectedGraph:
    edges: Dict[str, Set[str]]

    def add_edge(self, source: str, destination: str) -> None:
        if source not in self.edges:
            self.edges[source] = set()

        self.edges[source].add(destination)

    def write_dot(self, output_stream: IO[str]) -> None:
        output_stream.write("digraph {\n")

        for source, dests in self.edges.items():
            for destination in sorted(dests):
                output_stream.write('  "{}" -> "{}";\n'.format(source, destination))

        output_stream.write("}\n")
