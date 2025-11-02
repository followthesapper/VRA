#!/usr/bin/env python3
"""
Export VRA-centered network with only TOP 10 papers
Perfect for online viewers with limited node support
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
        return (255, 0, 0)  # Red
    elif sim > 0.4:
        return (255, 69, 0)  # Orange-Red
    elif sim > 0.3:
        return (255, 140, 0)  # Dark Orange
    elif sim > 0.2:
        return (255, 215, 0)  # Gold
    elif sim > 0.15:
        return (30, 144, 255)  # Dodger Blue
    else:
        return (100, 149, 237)  # Cornflower Blue

def build_top10_network(vra_data, papers_data, top_n=10):
    """Build network with only top N papers"""
    G = nx.Graph()

    # Sort papers and take top N
    papers_sorted = sorted(papers_data, key=lambda x: x['vra_similarity'], reverse=True)
    papers_subset = papers_sorted[:top_n]

    all_nodes = vra_data + papers_subset

    print(f"\nBuilding TOP {top_n} network:")
    print(f"  VRA documents: {len(vra_data)}")
    print(f"  Research papers: {len(papers_subset)}")
    print(f"  Total nodes: {len(all_nodes)}")

    # Add all nodes
    for i, node in enumerate(all_nodes):
        title = node['filename'].replace('.pdf', '').replace('.md', '').replace('_', ' ')

        sim = node['vra_similarity']
        is_vra = node.get('is_vra', False)

        # Get color
        r, g, b = get_color_for_similarity(sim, is_vra)

        # Category
        if is_vra:
            category = "VRA Documents"
        elif sim > 0.5:
            category = "High (>0.5)"
        elif sim > 0.3:
            category = "Medium (0.3-0.5)"
        elif sim > 0.15:
            category = "Low-Medium (0.15-0.3)"
        else:
            category = "Very Low (<0.15)"

        # Size
        size = 50.0 if is_vra else 10.0 + 40.0 * sim

        G.add_node(i,
                   label=title[:80],
                   title=title,
                   vra_similarity=float(sim),
                   category=category,
                   is_vra=is_vra,
                   r=r, g=g, b=b,
                   size=size)

    # Add edges
    edge_count = 0
    for i in range(len(all_nodes)):
        for j in range(i+1, len(all_nodes)):
            similarity = compute_similarity(
                all_nodes[i]['scores'],
                all_nodes[j]['scores']
            )

            if similarity > 0.2:  # Lower threshold for smaller network
                G.add_edge(i, j, weight=float(similarity))
                edge_count += 1

    print(f"  Edges created: {edge_count}\n")

    return G, all_nodes

def main():
    print("="*70)
    print("VRA TOP 10 NETWORK - COMPACT VERSION FOR ONLINE VIEWERS")
    print("="*70)

    # VRA documents
    vra_docs = [
        '/home/admin/dev/VRA/Manuscript/vra_complete_paper.pdf',
        '/home/admin/dev/VRA/Docs/Theory/Foundations/VSRA_QUANTUM_CORRESPONDENCE.md',
        '/home/admin/dev/VRA/Docs/Theory/Foundations/VRA_SPECTRAL_FRAMEWORK.md',
        '/home/admin/dev/VRA/README.md'
    ]

    print("\n1. Extracting VRA documents...")
    vra_data = extract_vra_docs_text(vra_docs)

    print("\n2. Loading research papers...")
    papers_data = load_pdf_analysis()

    # Create multiple filtered versions
    for top_n in [10, 20, 30]:
        print(f"\n{'='*70}")
        print(f"Creating TOP {top_n} network...")
        print(f"{'='*70}")

        G, all_nodes = build_top10_network(vra_data, papers_data, top_n=top_n)

        output_dir = Path('/home/admin/dev/VRA/Novelty/graph_export')
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export GEXF
        gexf_output = output_dir / f'vra_top{top_n}_network.gexf'
        nx.write_gexf(G, str(gexf_output))
        print(f"  ✓ Exported: {gexf_output}")

        # Export JSON
        nodes_list = []
        for node_id in G.nodes():
            nd = G.nodes[node_id]
            nodes_list.append({
                'id': node_id,
                'label': nd['label'],
                'vra_similarity': nd['vra_similarity'],
                'category': nd['category'],
                'is_vra': nd['is_vra'],
                'color': {'r': nd['r'], 'g': nd['g'], 'b': nd['b']},
                'size': nd['size']
            })

        edges_list = []
        for source, target in G.edges():
            edges_list.append({
                'source': source,
                'target': target,
                'weight': G[source][target]['weight']
            })

        json_output = output_dir / f'vra_top{top_n}_network.json'
        with open(json_output, 'w') as f:
            json.dump({'nodes': nodes_list, 'edges': edges_list}, f, indent=2)
        print(f"  ✓ Exported: {json_output}")

        # Print node list
        print(f"\n  Nodes in TOP {top_n} network:")
        print(f"  {'='*66}")
        for i, node in enumerate(all_nodes):
            marker = "🟢" if node.get('is_vra') else "📄"
            sim = node['vra_similarity']
            title = node['filename'][:50]
            print(f"  {marker} #{i}: {title:<50} (sim: {sim:.3f})")

    print("\n" + "="*70)
    print("✅ FILTERED NETWORKS CREATED!")
    print("="*70)
    print(f"\nFiles created in: {output_dir}/")
    print(f"  • vra_top10_network.gexf  ← 4 VRA + 10 papers (14 nodes)")
    print(f"  • vra_top20_network.gexf  ← 4 VRA + 20 papers (24 nodes)")
    print(f"  • vra_top30_network.gexf  ← 4 VRA + 30 papers (34 nodes)")
    print(f"")
    print(f"  + JSON versions of each")
    print(f"")
    print(f"🌐 Online GEXF Viewers:")
    print(f"  1. https://retina.gephi.org/ (Gephi Lite)")
    print(f"  2. https://graphonline.ru/en/")
    print(f"  3. Upload the TOP 10 or TOP 20 version for best results!")
    print(f"")
    print(f"  🟢 GREEN nodes = Your VRA documents")
    print(f"  📄 Colored nodes = Most similar research papers")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
