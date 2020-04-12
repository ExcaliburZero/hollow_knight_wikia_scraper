import io
import unittest

from .context import hollow_knight_wikia_scraper as hkws

class TestDirectedGraph(unittest.TestCase):
    def test_write_dot_empty(self) -> None:
        graph = hkws.graph.DirectedGraph({})
        output_stream = io.StringIO()

        graph.write_dot(output_stream)

        expected = "digraph {\n}\n"
        actual = output_stream.getvalue()

        self.assertEqual(expected, actual)


    def test_write_dot_some_entries(self) -> None:
        graph = hkws.graph.DirectedGraph({})
        output_stream = io.StringIO()

        graph.add_edge("Knight", "Hollow_Knight")
        graph.add_edge("Knight", "Charms")

        graph.write_dot(output_stream)

        expected = "digraph {\n" +\
            "  \"Knight\" -> \"Charms\";\n" +\
            "  \"Knight\" -> \"Hollow_Knight\";\n" +\
            "}\n"
        actual = output_stream.getvalue()

        self.assertEqual(expected, actual)