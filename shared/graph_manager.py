"""
FinSight Knowledge Graph Manager
==================================
Manages a persistent NetworkX DiGraph for entity relationships.
Used by Skills 2, 3, and 6 for both reasoning and visualization.

STORAGE:  data/graph/knowledge_graph.json  (NetworkX node_link_data format)
VISUAL:   data/visualizations/graph.html   (Pyvis interactive HTML)

NODE TYPES: company, sector, country, commodity, event
EDGE TYPES: belongs_to, exposed_to, affected_by, correlated_with, headquartered_in
"""

import os
import json
import datetime
import networkx as nx

try:
    from pyvis.network import Network
    PYVIS_AVAILABLE = True
except ImportError:
    PYVIS_AVAILABLE = False
    print("[Graph] pyvis not installed. Visualization disabled.")

from shared.config_loader import get_workspace_path


class GraphManager:
    """
    Manages the FinSight knowledge graph.

    The graph stores entities (companies, sectors, countries, commodities, events)
    and their relationships. It grows incrementally as events are processed.

    INPUT (on load):
        data/graph/knowledge_graph.json — previously saved graph state

    OUTPUT (on save):
        data/graph/knowledge_graph.json — updated graph state
        data/visualizations/graph.html  — interactive Pyvis visualization
    """

    # Color scheme for node types in visualization
    NODE_COLORS = {
        "company": "#4FC3F7",    # Light blue
        "sector": "#81C784",     # Green
        "country": "#FFB74D",    # Orange
        "commodity": "#F06292",  # Pink
        "event": "#BA68C8",      # Purple
    }

    NODE_SHAPES = {
        "company": "dot",
        "sector": "diamond",
        "country": "triangle",
        "commodity": "star",
        "event": "square",
    }

    def __init__(self):
        self.graph_path = get_workspace_path("graph", "knowledge_graph.json")
        self.graph = self._load()

    def _load(self) -> nx.DiGraph:
        """Load graph from JSON file, or create empty graph."""
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return nx.node_link_graph(data, directed=True)
            except Exception as e:
                print(f"[Graph] Failed to load graph: {e}. Starting fresh.")
        return nx.DiGraph()

    def save(self):
        """
        Persist the graph to disk as JSON.

        OUTPUT: data/graph/knowledge_graph.json
        """
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(self.graph_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    # ── Node Operations ──────────────────────────────────────────

    def add_entity(self, name: str, entity_type: str, metadata: dict = None):
        """
        Add or update an entity node.

        INPUT:
            name        — Entity name (e.g., "Reliance Industries")
            entity_type — One of: company, sector, country, commodity, event
            metadata    — Optional dict of additional attributes

        OUTPUT:
            Node added/updated in the in-memory graph
        """
        node_id = self._normalize(name)
        attrs = {
            "label": name,
            "type": entity_type,
            "created_at": datetime.datetime.now().isoformat(),
        }
        if metadata:
            attrs.update(metadata)

        if self.graph.has_node(node_id):
            # Update existing node, don't overwrite created_at
            existing = self.graph.nodes[node_id]
            attrs["created_at"] = existing.get("created_at", attrs["created_at"])
            attrs["updated_at"] = datetime.datetime.now().isoformat()
            self.graph.nodes[node_id].update(attrs)
        else:
            self.graph.add_node(node_id, **attrs)

    def add_relationship(self, source: str, target: str, rel_type: str, metadata: dict = None):
        """
        Add a directed edge between two entities.

        INPUT:
            source   — Source entity name
            target   — Target entity name
            rel_type — One of: belongs_to, exposed_to, affected_by, correlated_with, headquartered_in
            metadata — Optional dict of edge attributes

        OUTPUT:
            Edge added/updated in the in-memory graph
        """
        src_id = self._normalize(source)
        tgt_id = self._normalize(target)

        attrs = {
            "type": rel_type,
            "created_at": datetime.datetime.now().isoformat(),
        }
        if metadata:
            attrs.update(metadata)

        self.graph.add_edge(src_id, tgt_id, **attrs)

    # ── Query Operations ─────────────────────────────────────────

    def query_connections(self, entity: str, depth: int = 1) -> list:
        """
        Get all entities connected to the given entity up to N hops.

        INPUT:
            entity — Entity name to query
            depth  — Number of hops (1 = direct connections only)

        OUTPUT:
            list of dicts: [{"name": ..., "type": ..., "relationship": ..., "direction": ...}]
        """
        node_id = self._normalize(entity)
        if not self.graph.has_node(node_id):
            return []

        connections = []
        visited = set()
        self._bfs_connections(node_id, depth, connections, visited)
        return connections

    def _bfs_connections(self, node_id, depth, connections, visited):
        """BFS to find connections up to given depth."""
        if depth <= 0:
            return
        visited.add(node_id)

        # Outgoing edges
        for _, target, data in self.graph.out_edges(node_id, data=True):
            if target not in visited:
                node_data = self.graph.nodes.get(target, {})
                connections.append({
                    "name": node_data.get("label", target),
                    "type": node_data.get("type", "unknown"),
                    "relationship": data.get("type", "related"),
                    "direction": "outgoing",
                })
                self._bfs_connections(target, depth - 1, connections, visited)

        # Incoming edges
        for source, _, data in self.graph.in_edges(node_id, data=True):
            if source not in visited:
                node_data = self.graph.nodes.get(source, {})
                connections.append({
                    "name": node_data.get("label", source),
                    "type": node_data.get("type", "unknown"),
                    "relationship": data.get("type", "related"),
                    "direction": "incoming",
                })
                self._bfs_connections(source, depth - 1, connections, visited)

    def get_context_for_event(self, entities: dict) -> str:
        """
        Build a text context from the knowledge graph for a set of event entities.
        This is injected into the hypothesis generation prompt.

        INPUT:
            entities — dict with keys: companies, sectors, countries, commodities
                       Each value is a list of entity names

        OUTPUT:
            str — Human-readable text describing known graph connections
                  e.g., "Reliance Industries belongs_to energy sector.
                         energy sector is correlated_with crude oil."
        """
        context_lines = []

        all_entities = []
        for key in ["companies", "sectors", "countries", "commodities"]:
            all_entities.extend(entities.get(key, []))

        for entity_name in all_entities:
            connections = self.query_connections(entity_name, depth=2)
            if connections:
                for conn in connections[:5]:  # Limit to 5 connections per entity
                    context_lines.append(
                        f"- {entity_name} {conn['relationship']} {conn['name']} ({conn['type']})"
                    )

        if not context_lines:
            return "No prior knowledge graph connections found for these entities."

        return "Known connections from knowledge graph:\n" + "\n".join(context_lines)

    def get_entities_by_type(self, entity_type: str) -> list:
        """
        Get all entities of a given type.

        INPUT:  entity_type — "company", "sector", etc.
        OUTPUT: list of dicts [{"id": ..., "label": ..., "type": ...}]
        """
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") == entity_type:
                results.append({"id": node_id, "label": data.get("label", node_id), **data})
        return results

    def get_entities_for_sector(self, sector: str) -> list:
        """
        Get all companies that belong to a given sector.

        INPUT:  sector — Sector name (e.g., "energy")
        OUTPUT: list of company names
        """
        sector_id = self._normalize(sector)
        companies = []
        for source, target, data in self.graph.in_edges(sector_id, data=True):
            if data.get("type") == "belongs_to":
                node_data = self.graph.nodes.get(source, {})
                if node_data.get("type") == "company":
                    companies.append(node_data.get("label", source))
        return companies

    # ── Bulk Update (called by Skill 2) ──────────────────────────

    def update_from_extraction(self, event_id: str, extracted: dict):
        """
        Update the graph with entities and relationships from a Skill 2 extraction.

        INPUT:
            event_id  — Unique event identifier
            extracted — Dict with keys:
                entities:
                    companies: [...]
                    sectors: [...]
                    countries: [...]
                    commodities: [...]
                event_type: str
                one_line_summary: str

        OUTPUT:
            Graph updated in-memory with new nodes and edges.
            Call .save() afterwards to persist.
        """
        entities = extracted.get("entities", {})

        # Add event node
        self.add_entity(event_id, "event", {
            "event_type": extracted.get("event_type", "unknown"),
            "summary": extracted.get("one_line_summary", ""),
        })

        # Add companies and link to sectors
        for company in entities.get("companies", []):
            self.add_entity(company, "company")
            self.add_relationship(company, event_id, "affected_by")

        # Add sectors and link to event
        for sector in entities.get("sectors", []):
            self.add_entity(sector, "sector")
            self.add_relationship(sector, event_id, "affected_by")

            # Link companies to sectors
            for company in entities.get("companies", []):
                self.add_relationship(company, sector, "belongs_to")

        # Add countries
        for country in entities.get("countries", []):
            self.add_entity(country, "country")
            for company in entities.get("companies", []):
                self.add_relationship(company, country, "headquartered_in")

        # Add commodities
        for commodity in entities.get("commodities", []):
            self.add_entity(commodity, "commodity")
            for sector in entities.get("sectors", []):
                self.add_relationship(sector, commodity, "exposed_to")

    # ── Visualization ────────────────────────────────────────────

    def render_html(self) -> str:
        """
        Render the graph as an interactive HTML file using Pyvis.

        OUTPUT:
            str — Path to generated HTML file at data/visualizations/graph.html
        """
        if not PYVIS_AVAILABLE:
            return ""

        net = Network(
            height="700px", width="100%", bgcolor="#1a1a2e",
            font_color="white", directed=True
        )
        net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=200)

        for node_id, data in self.graph.nodes(data=True):
            node_type = data.get("type", "unknown")
            net.add_node(
                node_id,
                label=data.get("label", node_id),
                color=self.NODE_COLORS.get(node_type, "#FFFFFF"),
                shape=self.NODE_SHAPES.get(node_type, "dot"),
                title=f"Type: {node_type}\n" + "\n".join(
                    f"{k}: {v}" for k, v in data.items()
                    if k not in ("label", "type")
                ),
                size=20 if node_type == "event" else 15,
            )

        for source, target, data in self.graph.edges(data=True):
            net.add_edge(
                source, target,
                label=data.get("type", ""),
                color="#666666",
                arrows="to",
            )

        output_path = get_workspace_path("visualizations", "graph.html")
        net.save_graph(output_path)
        return output_path

    def get_stats(self) -> dict:
        """
        Get graph statistics.

        OUTPUT:
            dict with keys: total_nodes, total_edges, nodes_by_type
        """
        type_counts = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "nodes_by_type": type_counts,
        }

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _normalize(name: str) -> str:
        """Normalize entity name to a graph node ID."""
        return name.strip().lower().replace(" ", "_")
