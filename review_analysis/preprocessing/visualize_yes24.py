
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 화면 표시 없이 파일로 저장하기 위한 설정
import matplotlib.pyplot as plt


def main() -> None:
    # 이 파일 위치: .../review_analysis/preprocessing/visualize_yes24.py
    # 부모 폴더 2번 올라가면 프로젝트 루트 (.../YBIGTA_newbie_team_project)
    project_root = Path(__file__).resolve().parents[2]

    # 입력: 전처리된 Yes24 CSV 파일
    csv_path = project_root / "database" / "preprocessed_reviews_yes24.csv"
    
    # 출력: 플롯 저장 경로
    plots_dir = project_root / "review_analysis" / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    # 파일 존재 확인
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    print(f"Loading data from {csv_path}...")
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # 타입 정리 (rating -> 숫자, date -> 날짜)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    
    # 필수 컬럼 결측치 제거
    df = df.dropna(subset=["rating", "date"]).copy()

    # content_len 없으면 생성 (전처리 파일에 보통 포함되어 있지만 안전장치)
    if "content_len" not in df.columns:
        base_col = "content_clean" if "content_clean" in df.columns else "content"
        df["content_len"] = df[base_col].astype(str).str.len()

    print("Generating plots...")

    # (1) 별점 히스토그램
    plt.figure()
    # 1점~5점 정수 별점이므로 구간을 0.5 단위로 끊어서 시각화
    df["rating"].hist(bins=[0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
    plt.title("Yes24 EDA: Rating Histogram")
    plt.xlabel("rating")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_rating_hist.png", dpi=200)
    plt.close()

    # (2) 별점 박스플롯
    plt.figure()
    plt.boxplot(df["rating"].values)
    plt.title("Yes24 EDA: Rating Boxplot")
    plt.ylabel("rating")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_rating_box.png", dpi=200)
    plt.close()

    # (3) 별점 파이차트
    plt.figure()
    rating_counts = df["rating"].round().astype(int).value_counts().sort_index()
    plt.pie(rating_counts.values, labels=rating_counts.index.astype(str), autopct="%1.1f%%")
    plt.title("Yes24 EDA: Rating Pie")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_rating_pie.png", dpi=200)
    plt.close()

    # (4) 텍스트 길이 히스토그램
    plt.figure()
    df["content_len"].hist(bins=30)
    plt.title("Yes24 EDA: Text Length Histogram")
    plt.xlabel("content_len")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_textlen_hist.png", dpi=200)
    plt.close()

    # (5) 텍스트 길이 박스플롯
    plt.figure()
    plt.boxplot(df["content_len"].values)
    plt.title("Yes24 EDA: Text Length Boxplot")
    plt.ylabel("content_len")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_textlen_box.png", dpi=200)
    plt.close()

    # (6) 월별 리뷰 수 라인그래프
    plt.figure()
    # Pandas 2.x 버전부터 'M' 대신 'ME'(Month End) 사용 권장
    monthly_cnt = df.set_index("date").resample("ME").size()
    monthly_cnt.plot()
    plt.title("Yes24 EDA: Monthly Review Count")
    plt.xlabel("month")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_monthly_count_line.png", dpi=200)
    plt.close()

    # (7) 월별 평균 별점 라인그래프
    plt.figure()
    monthly_mean = df.set_index("date")["rating"].resample("ME").mean()
    monthly_mean.plot()
    plt.title("Yes24 EDA: Monthly Mean Rating")
    plt.xlabel("month")
    plt.ylabel("mean_rating")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_monthly_mean_rating_line.png", dpi=200)
    plt.close()

    # (8) 요일별 리뷰 수 막대그래프
    plt.figure()
    weekday = df["date"].dt.dayofweek  # Mon=0 ... Sun=6
    weekday_counts = weekday.value_counts().sort_index()
    plt.bar(weekday_counts.index.astype(str), weekday_counts.values)
    plt.title("Yes24 EDA: Weekday Review Count")
    plt.xlabel("dayofweek (Mon=0 ... Sun=6)")
    plt.ylabel("count")
    plt.tight_layout()
    plt.savefig(plots_dir / "yes24_eda_weekday_count_bar.png", dpi=200)
    plt.close()
    
    print(f"All plots saved to {plots_dir}")


if __name__ == "__main__":
    main()