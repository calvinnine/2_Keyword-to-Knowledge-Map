"""Smoke tests for graph analysis helpers using in-memory NetworkX graphs."""

import networkx as nx


def test_louvain_runs_on_simple_graph():
    """Ensure python-louvain installs and runs cleanly."""
    import community as community_louvain

    G = nx.karate_club_graph()
    partition = community_louvain.best_partition(G, random_state=42)
    assert len(partition) == G.number_of_nodes()
    assert len(set(partition.values())) >= 2


def test_networkx_centrality_metrics():
    G = nx.karate_club_graph()
    pr = nx.pagerank(G)
    bw = nx.betweenness_centrality(G)
    cl = nx.closeness_centrality(G)
    assert len(pr) == len(bw) == len(cl) == G.number_of_nodes()
