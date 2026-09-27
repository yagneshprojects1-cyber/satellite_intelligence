import sys
import traceback

def main():
    print("Starting run_phase6.py...", flush=True)
    import argparse
    from app.embeddings.pipeline import Phase6Pipeline

    parser = argparse.ArgumentParser(description="Phase 6 - AI Embeddings")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tiles to process (for validation)")
    args = parser.parse_args()
    
    pipeline = Phase6Pipeline(limit=args.limit)
    print("Pipeline initialized", flush=True)
    pipeline.setup()
    print("Pipeline setup complete", flush=True)
    pipeline.process_tiles()
    print("Pipeline process complete", flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("EXCEPTION CAUGHT:", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
