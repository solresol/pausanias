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
        component_id INTEGER NOT NULL,
        degree_centrality REAL,
        betweenness_centrality REAL,
        eigenvector_centrality REAL,
        pagerank REAL,
        clustering_coefficient REAL,
        timestamp TEXT NOT NULL,
        UNIQUE(reference_form, entity_type, component_id)
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

def get_connected_components(G):
    """Break the graph into connected components and assign component IDs."""
    components = list(nx.connected_components(G))
    print(f"Found {len(components)} connected components.")
    
    # Create a mapping from node to component ID
    node_to_component = {}
    for i, component in enumerate(components):
        for node in component:
            node_to_component[node] = i
    
    # Create subgraphs for each component
    component_graphs = []
    for i, component in enumerate(components):
        subgraph = G.subgraph(component).copy()
        print(f"Component {i}: {subgraph.number_of_nodes()} nodes, {subgraph.number_of_edges()} edges")
        component_graphs.append((i, subgraph))
    
    return component_graphs, node_to_component

def calculate_centrality_measures(G, component_id):
    """Calculate various centrality measures for a connected component."""
    print(f"Calculating centrality measures for component {component_id}...")
    
    # Skip tiny components (1-2 nodes) for some measures
    if G.number_of_nodes() <= 2:
        degree_centrality = nx.degree_centrality(G)
        betweenness_centrality = {node: 0.0 for node in G.nodes()}
        if G.number_of_nodes() == 1:
            # For single node, set eigenvector centrality and pagerank to 1.0
            eigenvector_centrality = {node: 1.0 for node in G.nodes()}
            pagerank = {node: 1.0 for node in G.nodes()}
        else:
            # For two nodes, calculate basic measures
            eigenvector_centrality = {node: 0.5 for node in G.nodes()}
            pagerank = {node: 0.5 for node in G.nodes()}
            
        clustering_coefficient = {node: 0.0 for node in G.nodes()}
    else:
        print("  Calculating degree centrality...")
        degree_centrality = nx.degree_centrality(G)
        
        print("  Calculating betweenness centrality...")
        betweenness_centrality = nx.betweenness_centrality(G, weight='weight')
        
        print("  Calculating eigenvector centrality...")
        try:
            eigenvector_centrality = nx.eigenvector_centrality_numpy(G, weight='weight')
        except nx.NetworkXError:
            print("  Warning: Eigenvector centrality calculation failed. Using power iteration method.")
            try:
                eigenvector_centrality = nx.eigenvector_centrality(G, weight='weight', max_iter=1000)
            except nx.PowerIterationFailedConvergence:
                print("  Warning: Power iteration failed to converge. Using degree centrality as fallback.")
                eigenvector_centrality = degree_centrality
        
        print("  Calculating PageRank...")
        pagerank = nx.pagerank(G, weight='weight')
        
        print("  Calculating clustering coefficients...")
        clustering_coefficient = nx.clustering(G, weight='weight')
    
    # Combine all centrality measures
    centrality_data = []
    for node in G.nodes():
        centrality_data.append({
            'reference_form': node[0],
            'entity_type': node[1],
            'english_transcription': G.nodes[node]['english_transcription'],
            'component_id': component_id,
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
            (reference_form, entity_type, english_transcription, component_id,
             degree_centrality, betweenness_centrality, eigenvector_centrality, 
             pagerank, clustering_coefficient, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row['reference_form'], row['entity_type'], row['english_transcription'],
                row['component_id'], row['degree_centrality'], row['betweenness_centrality'], 
                row['eigenvector_centrality'], row['pagerank'], 
                row['clustering_coefficient'], timestamp
            )
        )
    
    conn.commit()
    print(f"Saved centrality measures for {len(centrality_df)} nodes.")

def visualize_component(G, component_id, centrality_df, output_dir, top_n=100):
    """Visualize a network component highlighting the most central nodes."""
    # Create component subdirectory
    component_dir = os.path.join(output_dir, f"component_{component_id}")
    os.makedirs(component_dir, exist_ok=True)
    
    # Filter centrality dataframe for this component
    component_df = centrality_df[centrality_df['component_id'] == component_id]
    
    # Skip visualization for very small components
    if len(component_df) <= 2:
        print(f"Skipping visualization for component {component_id} (too small).")
        return
    
    # Limit to top_n nodes if the component is larger
    if len(component_df) > top_n:
        # Get top nodes by different centrality measures
        top_by_degree = component_df.nlargest(top_n, 'degree_centrality')
        top_by_betweenness = component_df.nlargest(top_n, 'betweenness_centrality')
        top_by_eigenvector = component_df.nlargest(top_n, 'eigenvector_centrality')
        top_by_pagerank = component_df.nlargest(top_n, 'pagerank')
        
        # Create subgraphs for visualization
        measures = {
            'degree': top_by_degree,
            'betweenness': top_by_betweenness,
            'eigenvector': top_by_eigenvector,
            'pagerank': top_by_pagerank
        }
    else:
        # For smaller components, just use the whole component for all measures
        measures = {
            'degree': component_df,
            'betweenness': component_df,
            'eigenvector': component_df,
            'pagerank': component_df
        }
    
    # Define colors for entity types
    entity_colors = {
        'person': 'blue',
        'place': 'green',
        'deity': 'red',
        'other': 'orange'
    }
    
    # Generate visualizations for each centrality measure
    for measure_name, measure_df in measures.items():
        plt.figure(figsize=(14, 14))
        
        # Create subgraph with selected nodes
        node_set = [(row['reference_form'], row['entity_type']) for _, row in measure_df.iterrows()]
        subgraph = nx.subgraph(G, node_set)
        
        # Use spring layout for visualization
        pos = nx.spring_layout(subgraph, seed=42, k=0.5, iterations=100)
        
        # Get node sizes based on centrality measure
        if measure_name == 'degree':
            node_sizes = [component_df.loc[component_df['reference_form'] == subgraph.nodes[node]['reference_form']].iloc[0]['degree_centrality'] * 5000 + 100 for node in subgraph.nodes()]
        elif measure_name == 'betweenness':
            node_sizes = [component_df.loc[component_df['reference_form'] == subgraph.nodes[node]['reference_form']].iloc[0]['betweenness_centrality'] * 2000 + 100 for node in subgraph.nodes()]
        elif measure_name == 'eigenvector':
            node_sizes = [component_df.loc[component_df['reference_form'] == subgraph.nodes[node]['reference_form']].iloc[0]['eigenvector_centrality'] * 10000 + 100 for node in subgraph.nodes()]
        else:  # pagerank
            node_sizes = [component_df.loc[component_df['reference_form'] == subgraph.nodes[node]['reference_form']].iloc[0]['pagerank'] * 20000 + 100 for node in subgraph.nodes()]
        
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
        top_limit = min(20, len(node_sizes))
        top_indices = sorted(range(len(node_sizes)), key=lambda i: node_sizes[i], reverse=True)[:top_limit]
        top_nodes = [list(subgraph.nodes())[i] for i in top_indices]
        labels = {node: subgraph.nodes[node]['english_transcription'] for node in top_nodes}
        
        nx.draw_networkx_labels(
            subgraph, pos,
            labels=labels,
            font_size=10,
            font_weight='bold'
        )
        
        plt.title(f"Component {component_id}: Proper Noun Network (Top {len(measure_df)} by {measure_name.capitalize()} Centrality)")
        plt.axis('off')
        
        # Save the figure
        filename = os.path.join(component_dir, f"network_by_{measure_name}.png")
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved component {component_id} visualization to {filename}")
    
    # Save the component network data for D3 visualization
    export_component_for_d3(G, component_id, node_set, os.path.join(component_dir, "network_data.json"))

def visualize_network(full_graph, all_centrality_df, component_graphs, output_dir, top_n=100):
    """Visualize each network component and generate an overview visualization."""
    # Make sure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a component map visualization
    plt.figure(figsize=(16, 16))
    
    # Color map for components (cycle through colors)
    cmap = plt.cm.get_cmap('tab20', len(component_graphs))
    
    # Use spring layout for the full graph
    pos = nx.spring_layout(full_graph, seed=42, k=0.3, iterations=100)
    
    # Draw each component with a different color
    for comp_id, subgraph in component_graphs:
        nx.draw_networkx_nodes(
            subgraph, pos,
            node_size=20,
            node_color=[cmap(comp_id % 20)] * subgraph.number_of_nodes(),
            alpha=0.7,
            label=f"Component {comp_id} ({subgraph.number_of_nodes()} nodes)"
        )
        nx.draw_networkx_edges(
            subgraph, pos,
            alpha=0.2,
            width=0.3
        )
    
    plt.title(f"Pausanias Proper Noun Network - {len(component_graphs)} Components")
    plt.axis('off')
    plt.legend(loc='lower center', ncol=5, bbox_to_anchor=(0.5, -0.05))
    
    # Save the figure
    filename = os.path.join(output_dir, "component_map.png")
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved component map visualization to {filename}")
    
    # Visualize each component separately
    for comp_id, subgraph in component_graphs:
        if subgraph.number_of_nodes() > 2:  # Skip very small components
            comp_df = all_centrality_df[all_centrality_df['component_id'] == comp_id]
            visualize_component(subgraph, comp_id, comp_df, output_dir, top_n)
    
    # Export the full network data for D3
    export_for_d3(full_graph, component_graphs, os.path.join(output_dir, "network_data.json"))

def export_component_for_d3(G, component_id, nodes, filename):
    """Export a single component's network data for D3.js visualization."""
    # Prepare nodes with attributes
    node_data = []
    for node in nodes:
        node_data.append({
            'id': f"{node[0]}_{node[1]}",  # Create a unique string ID
            'reference_form': node[0],
            'entity_type': node[1],
            'english_name': G.nodes[node]['english_transcription'],
            'component': component_id
        })
    
    # Prepare edges with weights
    links = []
    subgraph = G.subgraph(nodes)
    for u, v, attrs in subgraph.edges(data=True):
        links.append({
            'source': f"{u[0]}_{u[1]}",
            'target': f"{v[0]}_{v[1]}",
            'weight': attrs.get('weight', 1)
        })
    
    # Combine into a single object
    data = {
        'nodes': node_data,
        'links': links,
        'component_id': component_id
    }
    
    # Save to file
    import json
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Exported component {component_id} network data for D3 to {filename}")

def export_for_d3(G, component_graphs, filename):
    """Export the complete network data with component info for D3.js visualization."""
    # Prepare nodes with attributes
    nodes = []
    for node, attrs in G.nodes(data=True):
        component_id = None
        for comp_id, subgraph in component_graphs:
            if node in subgraph:
                component_id = comp_id
                break
                
        nodes.append({
            'id': f"{node[0]}_{node[1]}",  # Create a unique string ID
            'reference_form': node[0],
            'entity_type': node[1],
            'english_name': attrs['english_transcription'],
            'component': component_id
        })
    
    # Prepare edges with weights
    links = []
    for u, v, attrs in G.edges(data=True):
        links.append({
            'source': f"{u[0]}_{u[1]}",
            'target': f"{v[0]}_{v[1]}",
            'weight': attrs.get('weight', 1)
        })
    
    # Prepare component data
    components = []
    for comp_id, subgraph in component_graphs:
        components.append({
            'id': comp_id,
            'size': subgraph.number_of_nodes(),
            'edges': subgraph.number_of_edges()
        })
    
    # Combine into a single object
    data = {
        'nodes': nodes,
        'links': links,
        'components': components
    }
    
    # Save to file
    import json
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Exported full network data for D3 visualization to {filename}")

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
        full_graph = build_graph(nodes_df, cooccurrences_df, args.min_cooccurrence)
        
        # Break the graph into connected components
        print("Breaking the graph into connected components...")
        component_graphs, node_to_component = get_connected_components(full_graph)
        
        # Calculate centrality measures for each component
        all_centrality_data = []
        for comp_id, component_graph in component_graphs:
            component_centrality = calculate_centrality_measures(component_graph, comp_id)
            all_centrality_data.append(component_centrality)
        
        # Combine all centrality data
        if all_centrality_data:
            all_centrality_df = pd.concat(all_centrality_data, ignore_index=True)
            
            # Save to database
            print("Saving centrality measures to database...")
            save_centrality_measures(conn, all_centrality_df)
            
            # Visualize the network
            print("Generating network visualizations...")
            visualize_network(full_graph, all_centrality_df, component_graphs, args.output_dir, args.top_nodes)
        else:
            print("No centrality data to save or visualize.")
        
        print("Network analysis complete.")
    
    except Exception as e:
        # Let exception bubble up
        raise e
    
    finally:
        conn.close()
