import sys
import os

# 현재 파일 위치(preprocessing)에서 두 단계 위(YBIGTA_newbie_team_project)를 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.append(project_root)


import os
import glob
from argparse import ArgumentParser
from typing import Dict, Type
from review_analysis.preprocessing.base_processor import BaseDataProcessor
from review_analysis.preprocessing.kyobo_processor import KyoboProcessor
from review_analysis.preprocessing.yes24_processor import Yes24Processor
from review_analysis.preprocessing.aladin_processor import AladinProcessor

# 모든 preprocessing 클래스를 예시 형식으로 적어주세요. 
# key는 "reviews_사이트이름"으로, value는 해당 처리를 위한 클래스
PREPROCESS_CLASSES: Dict[str, Type[BaseDataProcessor]] = {
    "reviews_kyobo": KyoboProcessor,
    "reviews_yes24": Yes24Processor,
    "reviews_aladin": AladinProcessor,
}

DATA_DIR = os.path.join("..", "..", "database")
REVIEW_COLLECTIONS = glob.glob(os.path.join(DATA_DIR, "reviews_*.csv"))

def create_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument('-o', '--output_dir', type=str, required=False, default=DATA_DIR, 
                        help="Output file dir. Example: ../../database")
    parser.add_argument('-c', '--preprocessor', type=str, required=False, choices=PREPROCESS_CLASSES.keys(),
                        help=f"Which processor to use. Choices: {', '.join(PREPROCESS_CLASSES.keys())}")
    parser.add_argument('-a', '--all', action='store_true',
                        help="Run all data preprocessors. Default to False.")    
    return parser

if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    if args.all: 
        for csv_file in REVIEW_COLLECTIONS:
            base_name = os.path.splitext(os.path.basename(csv_file))[0]
            
            if base_name in PREPROCESS_CLASSES:
                preprocessor_class = PREPROCESS_CLASSES[base_name]
                preprocessor = preprocessor_class(csv_file, args.output_dir)
                
                print(f"Processing: {base_name}...")
                preprocessor.preprocess()
                preprocessor.feature_engineering()
                preprocessor.save_to_database()
            else:
                print(f"Skipping {base_name}: No matching processor found.")
     
    elif args.preprocessor:
        base_name = args.preprocessor
        
        target_csv = os.path.join(DATA_DIR, f"{base_name}.csv")
        
        if os.path.exists(target_csv):
            preprocessor_class = PREPROCESS_CLASSES[base_name]
            preprocessor = preprocessor_class(target_csv, args.output_dir)
            
            print(f"Processing: {base_name}...")
            preprocessor.preprocess()
            preprocessor.feature_engineering()
            preprocessor.save_to_database()
        else:
            raise FileNotFoundError(f"Input file not found: {target_csv}")
    
    else:
        raise ValueError("No preprocessor selected. Use --all or --preprocessor.")