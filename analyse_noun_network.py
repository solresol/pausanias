#!/usr/bin/env python

import argparse
import sqlite3
import sys
import os
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict

def parse_arguments():
    parser = argparse.ArgumentParser(description="Analyze the network of proper nouns in Pausanias")
    parser.add_argument("--database", default="pausanias.sqlite", 
                        help="SQLite database file (default: pausanias.sqlite)")
    parser.add_argument("--min-cooccurrence", type=int, default=1,
                        help="Minimum number of co-occurrences for an edge (default: 1)")
    parser.add_argument("--top-nodes", type=int, default=100,
                        help="Number of top nodes to include in visualization (default: 100)")
    parser.add_argument("--output-dir", default="network_viz",
                        help="Output directory for network visualizations (default: network_viz)")
    
    return parser.parse_args()

def create_centrality_table(conn):
    """Create the table for storing centrality measures if it doesn't exist."""
    conn.execute('''
    CREATE TABLE IF NOT EXISTS noun_centrality (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reference_form TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        english_transcription TEXT NOT NULL,
        degree_centrality REAL,
        betweenness_centrality REAL,
        eigenvector_centrality REAL,
        pagerank REAL,
        clustering_coefficient REAL,
        timestamp TEXT NOT NULL,
        UNIQUE(reference_form, entity_type)
    )
    ''')
    conn.commit()

def clear_centrality_table(conn):
    """Clear existing centrality data before inserting new values."""
    conn.execute("DELETE FROM noun_centrality")
    conn.commit()
    print("Cleared existing centrality data.")

def get_noun_nodes(conn):
    """Get all distinct proper nouns as nodes."""
    query = """
    SELECT reference_form, entity_type, english_transcription
    FROM proper_nouns
    GROUP BY reference_form, entity_type
    """
    
    df = pd.read_sql_query(query, conn)
    return df

def get_cooccurrences(conn):
    """Get all passage IDs where each proper noun appears."""
    query = """
    SELECT passage_id, reference_form, entity_type
    FROM proper_nouns
    """
    
    df = pd.read_sql_query(query, conn)
    return df

def build_graph(nodes_df, cooccurrences_df, min_cooccurrence=1):
    """Build a network graph where nodes are proper nouns and edges represent co-occurrences."""
    # Create a graph
    G = nx.Graph()
    
    # Add nodes with attributes
    for _, row in nodes_df.iterrows():
        G.add_node(
            (row['reference_form'], row['entity_type']),
            reference_form=row['reference_form'],
            entity_type=row['entity_type'],
            english_transcription=row['english_transcription']
        )
    
    # Group by passage_id to find co-occurrences
    passage_nouns = defaultdict(list)
    for _, row in cooccurrences_df.iterrows():
        passage_nouns[row['passage_id']].append(
            (row['reference_form'], row['entity_type'])
        )
    
    # Add edges for co-occurrences
    edge_weights = defaultdict(int)
    for passage_id, nouns in passage_nouns.items():
        for i, noun1 in enumerate(nouns):
            for noun2 in nouns[i+1:]:
                # Ensure the order is consistent
                if noun1 < noun2:
                    edge = (noun1, noun2)
                else:
                    edge = (noun2, noun1)
                edge_weights[edge] += 1
    
    # Add edges with weights to the graph
    for edge, weight in edge_weights.items():
        if weight >= min_cooccurrence:
            G.add_edge(edge[0], edge[1], weight=weight)
    
    print(f"Built graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges.")
    return G

def calculate_centrality_measures(G):
    """Calculate various centrality measures for the graph."""
    print("Calculating degree centrality...")
    degree_centrality = nx.degree_centrality(G)
    
    print("Calculating betweenness centrality...")
    betweenness_centrality = nx.betweenness_centrality(G, weight='weight')
    
    print("Calculating eigenvector centrality...")
    eigenvector_centrality = nx.eigenvector_centrality_numpy(G, weight='weight')
    
    print("Calculating PageRank...")
    pagerank = nx.pagerank(G, weight='weight')
    
    print("Calculating clustering coefficients...")
    clustering_coefficient = nx.clustering(G, weight='weight')
    
    # Combine all centrality measures
    centrality_data = []
    for node in G.nodes():
        centrality_data.append({
            'reference_form': node[0],
            'entity_type': node[1],
            'english_transcription': G.nodes[node]['english_transcription'],
            'degree_centrality': degree_centrality[node],
            'betweenness_centrality': betweenness_centrality[node],
            'eigenvector_centrality': eigenvector_centrality[node],
            'pagerank': pagerank[node],
            'clustering_coefficient': clustering_coefficient[node]
        })
    
    return pd.DataFrame(centrality_data)

def save_centrality_measures(conn, centrality_df):
    """Save centrality measures to the database."""
    timestamp = datetime.now().isoformat()
    
    for _, row in centrality_df.iterrows():
        conn.execute(
            """
            INSERT OR REPLACE INTO noun_centrality 
            (reference_form, entity_type, english_transcription, 
             degree_centrality, betweenness_centrality, eigenvector_centrality, 
             pagerank, clustering_coefficient, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row['reference_form'], row['entity_type'], row['english_transcription'],
                row['degree_centrality'], row['betweenness_centrality'], 
                row['eigenvector_centrality'], row['pagerank'], 
                row['clustering_coefficient'], timestamp
            )
        )
    
    conn.commit()
    print(f"Saved centrality measures for {len(centrality_df)} nodes.")

def visualize_network(G, centrality_df, output_dir, top_n=100):
    """Visualize the network highlighting the most central nodes."""
    # Make sure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Get top nodes by different centrality measures
    top_by_degree = centrality_df.nlargest(top_n, 'degree_centrality')
    top_by_betweenness = centrality_df.nlargest(top_n, 'betweenness_centrality')
    top_by_eigenvector = centrality_df.nlargest(top_n, 'eigenvector_centrality')
    top_by_pagerank = centrality_df.nlargest(top_n, 'pagerank')
    
    # Create subgraphs for visualization
    subgraphs = {
        'degree': nx.subgraph(G, [(row['reference_form'], row['entity_type']) for _, row in top_by_degree.iterrows()]),
        'betweenness': nx.subgraph(G, [(row['reference_form'], row['entity_type']) for _, row in top_by_betweenness.iterrows()]),
        'eigenvector': nx.subgraph(G, [(row['reference_form'], row['entity_type']) for _, row in top_by_eigenvector.iterrows()]),
        'pagerank': nx.subgraph(G, [(row['reference_form'], row['entity_type']) for _, row in top_by_pagerank.iterrows()])
    }
    
    # Define colors for entity types
    entity_colors = {
        'person': 'blue',
        'place': 'green',
        'deity': 'red',
        'other': 'orange'
    }
    
    # Generate visualizations for each centrality measure
    for measure, subgraph in subgraphs.items():
        plt.figure(figsize=(14, 14))
        
        # Use spring layout for visualization
        pos = nx.spring_layout(subgraph, seed=42, k=0.5, iterations=100)
        
        # Get node sizes based on centrality measure
        if measure == 'degree':
            node_sizes = [v * 5000 + 100 for v in nx.degree_centrality(subgraph).values()]
        elif measure == 'betweenness':
            node_sizes = [v * 2000 + 100 for v in nx.betweenness_centrality(subgraph).values()]
        elif measure == 'eigenvector':
            node_sizes = [v * 10000 + 100 for v in nx.eigenvector_centrality_numpy(subgraph).values()]
        else:  # pagerank
            node_sizes = [v * 20000 + 100 for v in nx.pagerank(subgraph).values()]
        
        # Get node colors based on entity type
        node_colors = [entity_colors.get(subgraph.nodes[node]['entity_type'], 'gray') for node in subgraph.nodes()]
        
        # Draw the network
        nx.draw_networkx_edges(subgraph, pos, alpha=0.3, width=0.5)
        
        nx.draw_networkx_nodes(
            subgraph, pos,
            node_size=node_sizes,
            node_color=node_colors,
            alpha=0.7
        )
        
        # Add labels for top 20 nodes only to avoid clutter
        top_20_indices = sorted(range(len(node_sizes)), key=lambda i: node_sizes[i], reverse=True)[:20]
        top_20_nodes = [list(subgraph.nodes())[i] for i in top_20_indices]
        labels = {node: subgraph.nodes[node]['english_transcription'] for node in top_20_nodes}
        
        nx.draw_networkx_labels(
            subgraph, pos,
            labels=labels,
            font_size=10,
            font_weight='bold'
        )
        
        plt.title(f"Pausanias Proper Noun Network (Top {top_n} by {measure.capitalize()} Centrality)")
        plt.axis('off')
        
        # Save the figure
        filename = os.path.join(output_dir, f"network_by_{measure}.png")
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved network visualization to {filename}")
    
    # Also save the full network data for D3 visualization
    export_for_d3(G, os.path.join(output_dir, "network_data.json"))

def export_for_d3(G, filename):
    """Export the network data in a format suitable for D3.js visualization."""
    # Prepare nodes with attributes
    nodes = []
    for node, attrs in G.nodes(data=True):
        nodes.append({
            'id': f"{node[0]}_{node[1]}",  # Create a unique string ID
            'reference_form': node[0],
            'entity_type': node[1],
            'english_name': attrs['english_transcription']
        })
    
    # Prepare edges with weights
    links = []
    for u, v, attrs in G.edges(data=True):
        links.append({
            'source': f"{u[0]}_{u[1]}",
            'target': f"{v[0]}_{v[1]}",
            'weight': attrs.get('weight', 1)
        })
    
    # Combine into a single object
    data = {
        'nodes': nodes,
        'links': links
    }
    
    # Save to file
    import json
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Exported network data for D3 visualization to {filename}")

if __name__ == '__main__':
    args = parse_arguments()
    
    # Connect to the database
    conn = sqlite3.connect(args.database)
    
    try:
        # Create the centrality table if it doesn't exist
        create_centrality_table(conn)
        
        # Clear existing centrality data
        clear_centrality_table(conn)
        
        # Get nodes and co-occurrences
        print("Fetching proper noun data...")
        nodes_df = get_noun_nodes(conn)
        cooccurrences_df = get_cooccurrences(conn)
        
        if len(nodes_df) == 0:
            print("No proper nouns found in the database.")
            sys.exit(0)
        
        print(f"Found {len(nodes_df)} distinct proper nouns.")
        
        # Build the graph
        print("Building the network graph...")
        G = build_graph(nodes_df, cooccurrences_df, args.min_cooccurrence)
        
        # Calculate centrality measures
        print("Calculating centrality measures...")
        centrality_df = calculate_centrality_measures(G)
        
        # Save to database
        print("Saving centrality measures to database...")
        save_centrality_measures(conn, centrality_df)
        
        # Visualize the network
        print("Generating network visualizations...")
        visualize_network(G, centrality_df, args.output_dir, args.top_nodes)
        
        print("Network analysis complete.")
    
    except Exception as e:
        # Let exception bubble up
        raise e
    
    finally:
        conn.close()
