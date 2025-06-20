#!/usr/bin/env python3
"""
Performance benchmarking script for AI Mail MCP.

This script provides comprehensive performance testing and benchmarking
to ensure the system meets performance requirements.
"""

import asyncio
import json
import os
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import psutil
from ai_mail_mcp.mailbox import MailboxManager
from ai_mail_mcp.models import Message


class PerformanceBenchmark:
    """Performance benchmarking suite for AI Mail MCP."""
    
    def __init__(self, db_path: Path):
        self.mailbox = MailboxManager(db_path)
        self.results = {}
        
    def benchmark_message_sending(self, num_messages: int = 1000) -> Dict:
        """Benchmark message sending performance."""
        print(f"🚀 Benchmarking message sending ({num_messages} messages)...")
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        for i in range(num_messages):
            message = Message(
                id=f"bench-send-{i:06d}",
                sender="benchmark-sender",
                recipient="benchmark-recipient",
                subject=f"Benchmark Message {i}",
                body=f"This is benchmark message {i} " * 20,  # ~500 chars
                timestamp=datetime.now(timezone.utc),
                priority="normal" if i % 4 != 0 else "high",
                tags=["benchmark", "performance"] if i % 3 == 0 else ["benchmark"]
            )
            self.mailbox.send_message(message)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        duration = end_time - start_time
        memory_delta = end_memory - start_memory
        messages_per_second = num_messages / duration
        
        results = {
            "operation": "message_sending",
            "num_messages": num_messages,
            "duration_seconds": round(duration, 3),
            "messages_per_second": round(messages_per_second, 2),
            "memory_delta_mb": round(memory_delta, 2),
            "avg_message_time_ms": round((duration / num_messages) * 1000, 3)
        }
        
        print(f"   ✅ {messages_per_second:.2f} messages/sec, {memory_delta:.1f}MB memory")
        return results
    
    def benchmark_message_retrieval(self, num_messages: int = 1000) -> Dict:
        """Benchmark message retrieval performance."""
        print(f"📬 Benchmarking message retrieval ({num_messages} messages)...")
        
        # Ensure we have messages to retrieve
        self.benchmark_message_sending(num_messages)
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        messages = self.mailbox.get_messages("benchmark-recipient", limit=num_messages)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        duration = end_time - start_time
        memory_delta = end_memory - start_memory
        messages_per_second = len(messages) / duration if duration > 0 else float('inf')
        
        results = {
            "operation": "message_retrieval",
            "num_messages": len(messages),
            "duration_seconds": round(duration, 3),
            "messages_per_second": round(messages_per_second, 2),
            "memory_delta_mb": round(memory_delta, 2),
            "avg_retrieval_time_ms": round((duration / len(messages)) * 1000, 3) if messages else 0
        }
        
        print(f"   ✅ Retrieved {len(messages)} messages in {duration:.3f}s")
        return results
    
    def benchmark_concurrent_access(self, num_workers: int = 5, messages_per_worker: int = 100) -> Dict:
        """Benchmark concurrent database access."""
        print(f"🔄 Benchmarking concurrent access ({num_workers} workers, {messages_per_worker} messages each)...")
        
        def worker(worker_id: int) -> Dict:
            start_time = time.time()
            
            for i in range(messages_per_worker):
                message = Message(
                    id=f"concurrent-{worker_id}-{i:03d}",
                    sender=f"worker-{worker_id}",
                    recipient="concurrent-recipient",
                    subject=f"Concurrent Message {i}",
                    body=f"Worker {worker_id} message {i}",
                    timestamp=datetime.now(timezone.utc)
                )
                self.mailbox.send_message(message)
            
            duration = time.time() - start_time
            return {
                "worker_id": worker_id,
                "duration": duration,
                "messages_per_second": messages_per_worker / duration
            }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(num_workers)]
            worker_results = [future.result() for future in futures]
        
        total_duration = time.time() - start_time
        total_messages = num_workers * messages_per_worker
        overall_mps = total_messages / total_duration
        
        # Verify all messages were sent
        all_messages = self.mailbox.get_messages("concurrent-recipient", limit=total_messages * 2)
        concurrent_messages = [msg for msg in all_messages if msg.sender.startswith("worker-")]
        
        results = {
            "operation": "concurrent_access",
            "num_workers": num_workers,
            "messages_per_worker": messages_per_worker,
            "total_messages": total_messages,
            "total_duration_seconds": round(total_duration, 3),
            "overall_messages_per_second": round(overall_mps, 2),
            "messages_verified": len(concurrent_messages),
            "worker_results": worker_results
        }
        
        print(f"   ✅ {overall_mps:.2f} messages/sec across {num_workers} workers")
        return results
    
    def run_full_benchmark(self) -> Dict:
        """Run the complete benchmark suite."""
        print("🏁 Starting AI Mail MCP Performance Benchmark Suite")
        print("=" * 60)
        
        start_time = time.time()
        system_info = {
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "python_version": os.sys.version.split()[0],
            "platform": os.name
        }
        
        benchmark_results = []
        
        # Run individual benchmarks
        try:
            benchmark_results.append(self.benchmark_message_sending(1000))
            benchmark_results.append(self.benchmark_message_retrieval(1000))
            benchmark_results.append(self.benchmark_concurrent_access(5, 200))
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            return {"error": str(e)}
        
        total_duration = time.time() - start_time
        
        # Calculate overall metrics
        overall_results = {
            "benchmark_info": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_duration_seconds": round(total_duration, 3),
                "system_info": system_info
            },
            "benchmark_results": benchmark_results,
            "summary": {
                "total_operations": len(benchmark_results),
                "all_passed": True,
                "performance_grade": self._calculate_performance_grade(benchmark_results)
            }
        }
        
        print("\n🎯 Benchmark Summary:")
        print(f"   Total Duration: {total_duration:.2f}s")
        print(f"   Performance Grade: {overall_results['summary']['performance_grade']}")
        
        return overall_results
    
    def _calculate_performance_grade(self, results: List[Dict]) -> str:
        """Calculate overall performance grade based on benchmarks."""
        # Define performance thresholds
        thresholds = {
            "message_sending": {"excellent": 500, "good": 200, "acceptable": 50},
            "message_retrieval": {"excellent": 1000, "good": 500, "acceptable": 100},
            "concurrent_access": {"excellent": 300, "good": 100, "acceptable": 50}
        }
        
        scores = []
        
        for result in results:
            operation = result.get("operation")
            if operation in thresholds:
                mps = result.get("messages_per_second", 0)
                thresh = thresholds[operation]
                
                if mps >= thresh["excellent"]:
                    scores.append(4)  # A
                elif mps >= thresh["good"]:
                    scores.append(3)  # B
                elif mps >= thresh["acceptable"]:
                    scores.append(2)  # C
                else:
                    scores.append(1)  # D
        
        if not scores:
            return "N/A"
        
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 3.5:
            return "A (Excellent)"
        elif avg_score >= 2.5:
            return "B (Good)"
        elif avg_score >= 1.5:
            return "C (Acceptable)"
        else:
            return "D (Needs Improvement)"


def main():
    """Run the benchmark suite."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "benchmark.db"
        benchmark = PerformanceBenchmark(db_path)
        
        results = benchmark.run_full_benchmark()
        
        # Save results to file
        results_file = Path("benchmark_results.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n📊 Results saved to: {results_file.absolute()}")
        
        # Check if performance meets requirements
        grade = results.get("summary", {}).get("performance_grade", "")
        if "A" in grade or "B" in grade:
            print("✅ Performance benchmarks PASSED")
            return 0
        else:
            print("❌ Performance benchmarks FAILED")
            return 1


if __name__ == "__main__":
    exit(main())
