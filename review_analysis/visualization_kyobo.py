import re
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# ---------------------------------------
# 0) Settings
# ---------------------------------------
# Even if this font is missing, English text won't break.
plt.rcParams["font.family"] = "Malgun Gothic"  # Mac: AppleGothic
plt.rcParams["axes.unicode_minus"] = False

sns.set_theme(style="whitegrid")

DATA_PATH = Path("../database/preprocessed_reviews_kyobo.csv")  # adjust if needed
OUT_DIR = Path("review_analysis/plots")
OUT_DIR.mkdir(parents=True, exist_ok=True)

WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _light_grid(ax: plt.Axes) -> None:
    """
    Make grid subtle and remove top/right spines.

    Parameters
    ----------
    ax:
        Matplotlib Axes to style.
    """
    ax.grid(True, alpha=0.2)
    sns.despine(ax=ax)


def load_data(path: Path) -> pd.DataFrame:
    """
    Load preprocessed review data.

    Parameters
    ----------
    path:
        Path to `preprocessed_reviews_kyobo.csv`.

    Returns
    -------
    pd.DataFrame
        Loaded dataframe with normalized dtypes for key columns.
    """
    df = pd.read_csv(path)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    if "review_char_len" in df.columns:
        df["review_char_len"] = pd.to_numeric(df["review_char_len"], errors="coerce")

    return df


def plot_rating_distribution(df: pd.DataFrame) -> None:
    """
    Plot rating distribution as a bar chart.

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    order = sorted(df["rating"].dropna().unique())
    sns.countplot(x="rating", data=df, order=order, ax=ax)

    ax.set_title("Rating Distribution")
    ax.set_xlabel("Rating")
    ax.set_ylabel("Count")

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "rating_distribution.png", dpi=200)
    plt.close(fig)


def plot_review_char_len_distribution(df: pd.DataFrame) -> None:
    """
    Plot histogram + KDE for review character length.

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    x = df["review_char_len"].dropna()
    sns.histplot(x, bins=40, kde=True, ax=ax)

    ax.set_title("Review Length Distribution (Histogram + KDE)")
    ax.set_xlabel("Length (chars)")
    ax.set_ylabel("Count")

    # If you want (optional): ax.set_xscale("log")

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "review_char_len_hist_kde.png", dpi=200)
    plt.close(fig)


def plot_review_char_len_ecdf(df: pd.DataFrame) -> None:
    """
    Plot ECDF for review character length.

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    x = df["review_char_len"].dropna().sort_values().to_numpy()
    y = np.arange(1, len(x) + 1) / len(x)

    ax.plot(x, y, marker=".", linestyle="none")
    ax.set_title("Review Length ECDF")
    ax.set_xlabel("Length (chars)")
    ax.set_ylabel("ECDF")

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "review_char_len_ecdf.png", dpi=200)
    plt.close(fig)


def plot_len_outliers_box(df: pd.DataFrame) -> None:
    """
    Plot boxplot for review character length with a 99th percentile reference line.

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    sns.boxplot(y="review_char_len", data=df, ax=ax)

    ax.set_title("Review Length Outlier Check (Boxplot)")
    ax.set_xlabel("")
    ax.set_ylabel("Length (chars)")

    q99 = df["review_char_len"].quantile(0.99)
    ax.axhline(q99, linestyle="--")
    ax.text(0.02, q99, "  99th percentile", va="bottom")

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "review_char_len_box_outliers.png", dpi=200)
    plt.close(fig)


def plot_rating_vs_length(df: pd.DataFrame) -> None:
    """
    Plot hexbin chart for rating vs review length to reduce overplotting.

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    tmp = df[["rating", "review_char_len"]].dropna()
    hb = ax.hexbin(tmp["review_char_len"], tmp["rating"], gridsize=35, mincnt=1)

    ax.set_title("Rating vs Review Length (Hexbin)")
    ax.set_xlabel("Length (chars)")
    ax.set_ylabel("Rating")

    fig.colorbar(hb, ax=ax, label="Count")

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "rating_vs_length_hexbin.png", dpi=200)
    plt.close(fig)


def plot_weekday_violin(df: pd.DataFrame) -> None:
    """
    Plot rating distribution by weekday using violin plot.

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    sns.violinplot(
        x="weekday",
        y="rating",
        data=df,
        order=WEEKDAY_ORDER,
        cut=0,
        inner="quartile",
        ax=ax,
    )

    ax.set_title("Rating by Weekday (Violin + Quartiles)")
    ax.set_xlabel("Weekday")
    ax.set_ylabel("Rating")

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "weekday_rating_violin.png", dpi=200)
    plt.close(fig)


def plot_monthly_trend(df: pd.DataFrame) -> None:
    """
    Plot monthly review counts with a rolling mean smoothing line.

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    m = (
        df.dropna(subset=["date"])
        .set_index("date")
        .resample("MS")
        .size()
        .rename("count")
    )

    ax.plot(m.index, m.values, marker="o", label="Monthly count")

    m_roll = m.rolling(window=3, min_periods=1).mean()
    ax.plot(m_roll.index, m_roll.values, linewidth=2, label="3-month rolling mean")

    ax.set_title("Monthly Review Count Trend")
    ax.set_xlabel("Month")
    ax.set_ylabel("Count")
    ax.legend()

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "monthly_trend_rolling.png", dpi=200)
    plt.close(fig)


def plot_month_weekday_heatmap(df: pd.DataFrame) -> None:
    """
    Plot heatmap of review counts by (year_month x weekday).

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    pivot = (
        df.dropna(subset=["year_month", "weekday"])
        .pivot_table(
            index="year_month",
            columns="weekday",
            values="content",
            aggfunc="count",
            fill_value=0,
        )
        .reindex(columns=WEEKDAY_ORDER)
    )

    sns.heatmap(pivot, ax=ax, cbar=True)

    ax.set_title("Review Posting Pattern (Month x Weekday)")
    ax.set_xlabel("Weekday")
    ax.set_ylabel("Year-Month")

    fig.tight_layout()
    fig.savefig(OUT_DIR / "heatmap_month_weekday.png", dpi=200)
    plt.close(fig)


def plot_top_words(df: pd.DataFrame, top_n: int = 20) -> None:
    """
    Plot top frequent tokens from cleaned_content (simple frequency).

    Parameters
    ----------
    df:
        Preprocessed reviews dataframe.
    top_n:
        Number of top tokens to display.

    Notes
    -----
    This is a lightweight alternative to a WordCloud.
    Better quality if you add a proper stopword list and tokenizer.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    text = " ".join(df["cleaned_content"].dropna().astype(str).tolist()).lower()
    text = re.sub(r"\s+", " ", text).strip()

    tokens = [t for t in text.split(" ") if len(t) >= 2]

    # Minimal stopwords (edit freely)
    simple_stop = {"것", "수", "내", "너무", "정말", "그리고", "해서", "저는"}
    tokens = [t for t in tokens if t not in simple_stop]

    s = pd.Series(tokens).value_counts().head(top_n)[::-1]
    ax.barh(s.index, s.values)

    ax.set_title(f"Top {top_n} Tokens (Simple Frequency)")
    ax.set_xlabel("Count")
    ax.set_ylabel("Token")

    _light_grid(ax)
    fig.tight_layout()
    fig.savefig(OUT_DIR / "top_words_barh.png", dpi=200)
    plt.close(fig)


def main() -> None:
    """
    Run all EDA plots and save them into OUT_DIR.
    """
    df = load_data(DATA_PATH)

    print(f"[EDA] Loaded rows: {len(df)}")
    print("[EDA] Columns:", list(df.columns))

    plot_rating_distribution(df)
    plot_review_char_len_distribution(df)
    plot_review_char_len_ecdf(df)
    plot_len_outliers_box(df)
    plot_rating_vs_length(df)
    plot_weekday_violin(df)
    plot_monthly_trend(df)
    plot_month_weekday_heatmap(df)
    plot_top_words(df, top_n=20)

    print(f"[EDA] Saved figures to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
