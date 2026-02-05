from __future__ import annotations

import argparse

from st_app.rag.retriever import _build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS index for reviews.")
    parser.parse_args()
    _build_index()
    print("FAISS index built.")


if __name__ == "__main__":
    main()
