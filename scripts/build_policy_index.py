import sys
import time
from app.services.policy_search import PolicySearch

def main():
    try:
        print("🚀 Starting policy index build...")
        start_time = time.time()
        
        ps = PolicySearch()   # settings에서 CSV/Qdrant/모델 자동 참조
        ps.rebuild()          # 드롭 후 전체 재색인
        
        elapsed_time = time.time() - start_time
        print(f"✅ Policy index rebuilt successfully in {elapsed_time:.2f} seconds.")
        
    except FileNotFoundError as e:
        print(f"❌ Error: CSV file not found - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: Failed to build policy index - {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()