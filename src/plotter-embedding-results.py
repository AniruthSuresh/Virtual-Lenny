import json
import matplotlib.pyplot as plt

# -----------------------
# Load JSON
# -----------------------
json_path = "../results/mixed-testing-embeddings.json"

with open(json_path, "r") as f:
    results = json.load(f)

models = list(results.keys())
mrr = [results[m]["MRR"] for m in models]
hit5 = [results[m]["HitRate@5"] for m in models]
time_sec = [results[m]["AvgQueryTimeSec"] for m in models]

def add_labels(ax, bars, pad_ratio=0.05):
    """Add value labels on top of each vertical bar, with padding"""
    ylim = ax.get_ylim()
    y_padding = (ylim[1] - ylim[0]) * pad_ratio
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2,
            height + y_padding, 
            f"{height:.3f}",
            ha='center',
            va='bottom',
            fontsize=9
        )

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# MRR
bars1 = axes[0].bar(models, mrr, color='skyblue')
axes[0].set_title("MRR")
axes[0].set_ylabel("MRR")
axes[0].set_ylim(0, max(mrr)*1.2) 
add_labels(axes[0], bars1)
axes[0].tick_params(axis='x', rotation=45)

# HitRate@5
bars2 = axes[1].bar(models, hit5, color='lightgreen')
axes[1].set_title("HitRate@5")
axes[1].set_ylabel("HitRate@5")
axes[1].set_ylim(0, max(hit5)*1.2)
add_labels(axes[1], bars2)
axes[1].tick_params(axis='x', rotation=45)

# Avg Query Time
bars3 = axes[2].bar(models, time_sec, color='salmon')
axes[2].set_title("Avg Query Time (sec)")
axes[2].set_ylabel("Seconds")
axes[2].set_ylim(0, max(time_sec)*1.2)
add_labels(axes[2], bars3)
axes[2].tick_params(axis='x', rotation=45)

plt.tight_layout()

output_file = "../results/mixed_embeddings_combined_vertical.png"
plt.savefig(output_file, dpi=300)
print(f"Combined vertical plot saved to {output_file}")

plt.show()
