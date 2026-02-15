"""
Worker CLI for running background job processors.

Usage:
    python -m oao.worker --redis-url redis://localhost:6379/0
"""

import argparse
import asyncio
import sys

from oao.runtime.worker_node import WorkerNode


def main():
    parser = argparse.ArgumentParser(
        description="OAO Distributed Worker Node"
    )
    
    parser.add_argument(
        "--redis-url",
        type=str,
        default="redis://localhost:6379/0",
        help="Redis connection URL (default: redis://localhost:6379/0)"
    )
    
    parser.add_argument(
        "--worker-id",
        type=str,
        default=None,
        help="Unique worker ID (auto-generated if not provided)"
    )
    
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Queue polling interval in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Run worker in async mode"
    )
    
    args = parser.parse_args()
    
    try:
        worker = WorkerNode(
            redis_url=args.redis_url,
            worker_id=args.worker_id,
            poll_interval=args.poll_interval
        )
        
        if args.use_async:
            asyncio.run(worker.start_async())
        else:
            worker.start()
            
    except KeyboardInterrupt:
        print("\nWorker interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Worker failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
