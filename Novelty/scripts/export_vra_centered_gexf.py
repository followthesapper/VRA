#!/usr/bin/env python3
"""
Export VRA-centered network as GEXF with proper colors
Includes VRA documents as nodes with distinct colors
"""
import json
import numpy as np
import networkx as nx
from pathlib import Path
import subprocess

def load_pdf_analysis():
    """Load existing PDF analysis data"""
    with open('/home/admin/dev/VRA/Novelty/pdf_analysis_data.json', 'r') as f:
        return json.load(f)

def extract_vra_docs_text(vra_docs):
    """Extract text from VRA documentation"""
    vra_data = []

    for doc_path in vra_docs:
        doc_path = Path(doc_path)

        # Determine type and extract text
        text = ""
        if doc_path.suffix == '.md':
            with open(doc_path, 'r', encoding='utf-8') as f:
                text = f.read().lower()
        elif doc_path.suffix == '.pdf':
            try:
                result = subprocess.run(
                    ['pdftotext', '-enc', 'UTF-8', str(doc_path), '-'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                text = result.stdout.lower()
            except:
                print(f"  Error extracting {doc_path.name}")
                continue

        scores = score_paper(text)

        vra_data.append({
            'filename': doc_path.name,
            'path': str(doc_path),
            'is_vra': True,
            'scores': scores,
            'vra_similarity': compute_vra_similarity(scores),
            'text_length': len(text)
        })

    return vra_data

def score_paper(text):
    """Score paper for VRA concepts"""
    VRA_CONCEPTS = {
        "multiplicative_order": [
            "multiplicative order", "ord_n(a)", "order of element",
            "ord(a)", "group order"
        ],
        "modular_exponentiation": [
            "a^k mod n", "a^k mod", "modular exponentiation",
            "power mod", "repeated squaring", "modular sequence"
        ],
        "phase_embedding": [
            "exp(2πi", "exp(2*pi*i", "complex exponential",
            "unit circle", "phase trajectory", "phase embedding", "complex phase"
        ],
        "coherent_averaging": [
            "coherent averaging", "coherent integration",
            "phase-aligned averaging", "amplitude averaging",
            "vector averaging", "average before magnitude"
        ],
        "spectral_method": [
            "fft", "fourier transform", "dft", "spectral analysis",
            "frequency domain", "harmonic analysis"
        ],
        "harmonic_detection": [
            "harmonic peaks", "harmonic bins", "harmonic structure",
            "submultiples", "k*l/r", "k·l/r"
        ],
        "same_order_bases": [
            "same order", "identical order", "common order",
            "all bases", "multiple bases"
        ],
        "sqrt_m_scaling": [
            "√m", "sqrt(m)", "square root m", "√n scaling",
            "3 db per doubling", "coherent gain"
        ],
    }

    scores = {}
    for concept, keywords in VRA_CONCEPTS.items():
        matches = 0
        for keyword in keywords:
            if keyword.lower() in text:
                matches += 1
        scores[concept] = matches / len(keywords)

    return scores

def compute_vra_similarity(scores):
    """Compute overall VRA similarity"""
    critical_features = [
        "multiplicative_order",
        "modular_exponentiation",
        "phase_embedding",
        "coherent_averaging",
        "spectral_method"
    ]

    critical_score = sum(scores.get(f, 0) for f in critical_features)
    critical_weight = critical_score / len(critical_features)

    other_features = [k for k in scores.keys() if k not in critical_features]
    other_score = sum(scores.get(f, 0) for f in other_features)
    other_weight = other_score / len(other_features) if other_features else 0

    return 0.8 * critical_weight + 0.2 * other_weight

def compute_similarity(scores1, scores2):
    """Cosine similarity"""
    all_concepts = set(scores1.keys()) | set(scores2.keys())
    v1 = np.array([scores1.get(c, 0) for c in sorted(all_concepts)])
    v2 = np.array([scores2.get(c, 0) for c in sorted(all_concepts)])

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    if norm1 == 0 or norm2 == 0:
        return 0

    return np.dot(v1, v2) / (norm1 * norm2)

def get_color_for_similarity(sim, is_vra=False):
    """Get RGB color based on VRA similarity"""
    if is_vra:
        return (0, 255, 0)  # Bright green for VRA docs
    elif sim > 0.5:
        return (255, 0, 0)  # Red - High
    elif sim > 0.4:
        return (255, 69, 0)  # Orange-Red
    elif sim > 0.3:
        return (255, 140, 0)  # Dark Orange
    elif sim > 0.2:
        return (255, 215, 0)  # Gold
    elif sim > 0.15:
        return (30, 144, 255)  # Dodger Blue
    elif sim > 0.1:
        return (100, 149, 237)  # Cornflower Blue
    elif sim > 0.05:
        return (169, 169, 169)  # Dark Gray
    else:
        return (128, 128, 128)  # Gray

def build_vra_centered_network(vra_data, papers_data, similarity_threshold=0.25, top_papers=75):
    """Build network with VRA docs as central nodes"""
    G = nx.Graph()

    # Sort papers by VRA similarity
    papers_sorted = sorted(papers_data, key=lambda x: x['vra_similarity'], reverse=True)
    papers_subset = papers_sorted[:top_papers]

    all_nodes = vra_data + papers_subset

    print(f"Building VRA-centered network:")
    print(f"  VRA documents: {len(vra_data)}")
    print(f"  Research papers: {len(papers_subset)}")
    print(f"  Total nodes: {len(all_nodes)}")

    # Add all nodes with rich attributes
    for i, node in enumerate(all_nodes):
        title = node['filename'].replace('.pdf', '').replace('.md', '').replace('_', ' ')

        sim = node['vra_similarity']
        is_vra = node.get('is_vra', False)

        # Get color
        r, g, b = get_color_for_similarity(sim, is_vra)

        # Determine category
        if is_vra:
            category = "VRA Documents"
            viz_shape = "star"
        elif sim > 0.5:
            category = "High (>0.5)"
            viz_shape = "diamond"
        elif sim > 0.3:
            category = "Medium (0.3-0.5)"
            viz_shape = "square"
        elif sim > 0.15:
            category = "Low-Medium (0.15-0.3)"
            viz_shape = "circle"
        else:
            category = "Very Low (<0.15)"
            viz_shape = "circle"

        # Node size
        if is_vra:
            size = 50.0  # Large for VRA
        else:
            size = 10.0 + 40.0 * sim

        # Store color as separate attributes for Gephi compatibility
        G.add_node(i,
                   label=title[:60],
                   title=title,
                   vra_similarity=float(sim),
                   category=category,
                   is_vra=is_vra,
                   r=r,
                   g=g,
                   b=b,
                   size=size,
                   shape=viz_shape)

    # Add edges based on concept similarity
    edge_count = 0
    for i in range(len(all_nodes)):
        for j in range(i+1, len(all_nodes)):
            similarity = compute_similarity(
                all_nodes[i]['scores'],
                all_nodes[j]['scores']
            )

            if similarity > similarity_threshold:
                G.add_edge(i, j, weight=float(similarity))
                edge_count += 1

    print(f"  Edges created: {edge_count}")

    return G, all_nodes

def main():
    print("="*70)
    print("VRA-CENTERED NETWORK - GEXF EXPORT WITH COLORS")
    print("="*70 + "\n")

    # VRA documents to include
    vra_docs = [
        '/home/admin/dev/VRA/Manuscript/vra_complete_paper.pdf',
        '/home/admin/dev/VRA/Docs/Theory/Foundations/VSRA_QUANTUM_CORRESPONDENCE.md',
        '/home/admin/dev/VRA/Docs/Theory/Foundations/VRA_SPECTRAL_FRAMEWORK.md',
        '/home/admin/dev/VRA/README.md'
    ]

    print("1. Extracting VRA documents...")
    vra_data = extract_vra_docs_text(vra_docs)
    print(f"  ✓ Analyzed {len(vra_data)} VRA documents\n")

    for doc in vra_data:
        print(f"    - {doc['filename']}: VRA similarity = {doc['vra_similarity']:.3f}")

    print("\n2. Loading research papers analysis...")
    papers_data = load_pdf_analysis()
    print(f"  ✓ Loaded {len(papers_data)} research papers")

    print("\n3. Building VRA-centered network...")
    G, all_nodes = build_vra_centered_network(vra_data, papers_data,
                                              similarity_threshold=0.25,
                                              top_papers=75)

    print("\n4. Exporting GEXF with colors...")
    output_dir = Path('/home/admin/dev/VRA/Novelty/graph_export')
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / 'vra_centered_network.gexf'
    nx.write_gexf(G, str(output_path))
    print(f"  ✓ Exported: {output_path}")

    # Also create JSON and GraphML
    json_output = output_dir / 'vra_centered_network.json'
    graphml_output = output_dir / 'vra_centered_network.graphml'

    # Export JSON
    nodes_list = []
    for node_id in G.nodes():
        node_data = G.nodes[node_id]
        nodes_list.append({
            'id': node_id,
            'label': node_data['label'],
            'vra_similarity': node_data['vra_similarity'],
            'category': node_data['category'],
            'is_vra': node_data['is_vra'],
            'color': {'r': node_data['r'], 'g': node_data['g'], 'b': node_data['b']},
            'size': node_data['size']
        })

    edges_list = []
    for source, target in G.edges():
        edges_list.append({
            'source': source,
            'target': target,
            'weight': G[source][target]['weight']
        })

    with open(json_output, 'w') as f:
        json.dump({'nodes': nodes_list, 'edges': edges_list}, f, indent=2)
    print(f"  ✓ Exported: {json_output}")

    # Export CSV with colors for Gephi import
    nodes_csv = output_dir / 'vra_centered_nodes.csv'
    with open(nodes_csv, 'w') as f:
        f.write("Id,Label,VRA_Similarity,Category,Is_VRA,Red,Green,Blue,Size\n")
        for node_id in G.nodes():
            nd = G.nodes[node_id]
            f.write(f"{node_id},\"{nd['label']}\",{nd['vra_similarity']},{nd['category']},{nd['is_vra']},{nd['r']},{nd['g']},{nd['b']},{nd['size']}\n")
    print(f"  ✓ Exported: {nodes_csv}")

    edges_csv = output_dir / 'vra_centered_edges.csv'
    with open(edges_csv, 'w') as f:
        f.write("Source,Target,Weight\n")
        for source, target in G.edges():
            f.write(f"{source},{target},{G[source][target]['weight']}\n")
    print(f"  ✓ Exported: {edges_csv}")

    print("\n" + "="*70)
    print("✅ EXPORT COMPLETE - FILES WITH VRA DOCS INCLUDED!")
    print("="*70)
    print(f"\nOutput files in: {output_dir}/")
    print(f"  • vra_centered_network.gexf      ← Main file for Gephi")
    print(f"  • vra_centered_nodes.csv         ← Node data with RGB colors")
    print(f"  • vra_centered_edges.csv         ← Edge data")
    print(f"  • vra_centered_network.json      ← For online tools")

    print(f"\n🎨 Color Scheme:")
    print(f"  🟢 GREEN  - VRA Documents (your work!)")
    print(f"  🔴 RED    - High similarity (>0.5)")
    print(f"  🟠 ORANGE - Medium-high (0.3-0.5)")
    print(f"  🟡 YELLOW - Medium (0.2-0.3)")
    print(f"  🔵 BLUE   - Low-medium (0.1-0.2)")
    print(f"  ⚫ GRAY   - Very low (<0.1)")

    print(f"\n📊 Network Stats:")
    print(f"  VRA Documents: {len([n for n in all_nodes if n.get('is_vra')])} (GREEN STARS)")
    print(f"  Research Papers: {len([n for n in all_nodes if not n.get('is_vra')])}")
    print(f"  Total Nodes: {G.number_of_nodes()}")
    print(f"  Total Edges: {G.number_of_edges()}")

    print(f"\n🌐 How to use in Gephi:")
    print(f"  1. Open Gephi (gephi.org)")
    print(f"  2. File → Open → Select vra_centered_network.gexf")
    print(f"  3. Choose 'Undirected' graph")
    print(f"")
    print(f"  4. Apply Colors:")
    print(f"     - Go to 'Appearance' panel (left side)")
    print(f"     - Click 'Nodes' tab")
    print(f"     - Click color icon (paint palette)")
    print(f"     - Select 'Partition' mode")
    print(f"     - Choose 'Category' attribute")
    print(f"     - Click 'Apply'")
    print(f"")
    print(f"  5. Apply Layout:")
    print(f"     - Layout panel → ForceAtlas 2")
    print(f"     - Enable 'Prevent Overlap'")
    print(f"     - Click 'Run'")
    print(f"")
    print(f"  6. Look for:")
    print(f"     - GREEN 'VRA Documents' category = YOUR work!")
    print(f"     - See which papers connect to your VRA docs")
    print(f"")
    print(f"  Alternative: Manually set colors using Red/Green/Blue columns")
    print(f"     - Data Laboratory → Import Spreadsheet")
    print(f"     - Import vra_centered_nodes.csv")
    print(f"     - Appearance → Ranking → Red (0-255)")

    print("="*70 + "\n")

if __name__ == "__main__":
    main()
