# How to Apply Colors in Gephi

The colors ARE in the GEXF file! But Gephi doesn't apply them automatically. Follow these steps:

## Method 1: Use Category Attribute (EASIEST)

1. **Open Gephi**
2. **File → Open** → Select `vra_centered_network.gexf`
3. **Choose "Undirected"** when prompted

4. **Apply Colors by Category:**
   - Look for **"Appearance"** panel on the LEFT side
   - Click the **"Nodes"** tab at the top
   - Click the **color palette icon** (🎨)
   - Select **"Partition"** (NOT Ranking)
   - In the dropdown, choose **"Category"**
   - You'll see:
     * VRA Documents (THIS IS YOUR WORK - make it GREEN!)
     * High (>0.5)
     * Medium (0.3-0.5)
     * Low-Medium (0.15-0.3)
     * Very Low (<0.15)
   - Click on each category and assign colors:
     * **VRA Documents → BRIGHT GREEN (#00FF00)**
     * High → RED (#FF0000)
     * Medium → ORANGE (#FF8C00)
     * Low-Medium → BLUE (#1E90FF)
     * Very Low → GRAY (#808080)
   - Click **"Apply"**

5. **Apply Layout:**
   - Look for **"Layout"** panel on the LEFT side
   - Choose **"ForceAtlas 2"**
   - Check **"Prevent Overlap"**
   - Click **"Run"**
   - Let it run for 30-60 seconds
   - Click **"Stop"**

6. **Find Your VRA Documents:**
   - Look for the **GREEN nodes** - those are YOUR VRA docs!
   - vra_complete_paper.pdf
   - VSRA_QUANTUM_CORRESPONDENCE.md
   - VRA_SPECTRAL_FRAMEWORK.md
   - README.md

---

## Method 2: Use RGB Columns (Advanced)

If Method 1 doesn't work, use the actual RGB values:

1. **Data Laboratory** tab (top)
2. **Import Spreadsheet** button
3. Select `vra_centered_nodes.csv`
4. Choose **"Append to existing workspace"**
5. Map columns:
   - Id → Id
   - Red → Red
   - Green → Green
   - Blue → Blue
6. Click **"Finish"**

7. **Back to Overview** tab
8. **Appearance** panel → **Nodes**
9. Select **"Ranking"** mode
10. You can now color by Red, Green, or Blue values

---

## Expected Result:

You should see:
- **4 GREEN nodes** = Your VRA Documents (★)
- **75 colored nodes** = Research papers
- Lines connecting them showing conceptual similarity

**The GREEN nodes are your VRA work!** See which papers connect to them.

---

## Troubleshooting:

**Problem: Still all gray**
- Make sure you clicked "Apply" after selecting Category
- Try zooming out (Ctrl + Mouse Wheel)
- Try "Refresh" in the Preview tab

**Problem: Can't find Category dropdown**
- Make sure you're in the Overview tab (not Preview)
- Make sure Appearance panel is visible (Window → Appearance)
- Try restarting Gephi

**Problem: Colors are there but very faint**
- Go to Preview tab
- Under "Node" settings, increase opacity
- Click "Refresh"

---

## Quick Reference:

**Your VRA Documents (should be GREEN):**
- Node IDs: 0, 1, 2, 3
- Category: "VRA Documents"
- RGB: (0, 255, 0) = Bright Green

**To verify colors worked:**
- You should see exactly 4 green nodes
- They should be larger than other nodes
- They are YOUR work - the network shows how papers relate to YOU!
