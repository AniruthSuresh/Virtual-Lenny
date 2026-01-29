import os
import json
import matplotlib.pyplot as plt
from tqdm import tqdm

# --------------------
# Paths
# --------------------
YOUTUBE_DIR = "../data/processed/youtube/"
LINKEDIN_DIR = "../data/processed/linkedin/"
RESULTS_DIR = "../results"
os.makedirs(RESULTS_DIR, exist_ok=True)

# --------------------
# Function to get word counts
# --------------------
def get_word_counts(directory):
    counts = []
    files = [f for f in os.listdir(directory) if f.endswith(".json")]
    for filename in tqdm(files, desc=f"Processing {directory}"):
        path = os.path.join(directory, filename)
        with open(path, "r") as f:
            data = json.load(f)
        text = data.get("text", "")
        word_count = len(text.split())
        counts.append(word_count)
    return counts

# --------------------
# Function to print and save stats
# --------------------
def compute_stats(counts):
    counts_sorted = sorted(counts)
    stats = {
        "documents": len(counts),
        "min_words": min(counts),
        "max_words": max(counts),
        "mean_words": sum(counts)/len(counts),
        "median_words": counts_sorted[len(counts_sorted)//2]
    }
    return stats

# --------------------
# Function to plot histogram
# --------------------
def plot_histogram(counts, title, filename):
    plt.figure(figsize=(10,5))
    n, bins, patches = plt.hist(counts, bins=30, alpha=0.7, color="skyblue")
    plt.xlabel("Words per document")
    plt.ylabel("Number of documents")
    plt.title(title)
    plt.grid(axis='y', alpha=0.75)

    # Add counts on top of each bar
    for patch, count in zip(patches, n):
        if count > 0:
            plt.text(
                patch.get_x() + patch.get_width()/2,  # x-coordinate: center of bar
                count,                                # y-coordinate: height of bar
                str(int(count)),                       # label
                ha='center', va='bottom', fontsize=8
            )

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"[OK] Saved plot to {filename}")


# --------------------
# Main
# --------------------
if __name__ == "__main__":
    # Get word counts
    yt_counts = get_word_counts(YOUTUBE_DIR)
    ln_counts = get_word_counts(LINKEDIN_DIR)

    # Compute stats
    yt_stats = compute_stats(yt_counts)
    ln_stats = compute_stats(ln_counts)

    # Save stats as JSON
    stats_file = os.path.join(RESULTS_DIR, "word_count_stats.json")
    with open(stats_file, "w") as f:
        json.dump({"youtube": yt_stats, "linkedin": ln_stats}, f, indent=2)
    print(f"[OK] Saved stats to {stats_file}")

    # Plot and save histograms
    plot_histogram(yt_counts, "YouTube Word Count Distribution", os.path.join(RESULTS_DIR, "youtube_word_count_hist.png"))
    plot_histogram(ln_counts, "LinkedIn Word Count Distribution", os.path.join(RESULTS_DIR, "linkedin_word_count_hist.png"))

    print("[DONE] All stats and plots saved.")
