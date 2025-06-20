#!/usr/bin/env python3
"""
Database health checker and maintenance tool for AI Mail MCP.

This script provides database integrity checks, optimization, and maintenance.
"""

import os
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class DatabaseHealthChecker:
    """Database health checking and maintenance utility."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def check_integrity(self) -> Dict:
        """Check database integrity."""
        print("🔍 Checking database integrity...")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_path": str(self.db_path),
            "checks": {}
        }
        
        with sqlite3.connect(self.db_path) as conn:
            # Integrity check
            cursor = conn.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            results["checks"]["integrity"] = {
                "status": "PASS" if integrity_result == "ok" else "FAIL",
                "result": integrity_result
            }
            
            # Foreign key check
            cursor = conn.execute("PRAGMA foreign_key_check")
            fk_violations = cursor.fetchall()
            results["checks"]["foreign_keys"] = {
                "status": "PASS" if not fk_violations else "FAIL",
                "violations": len(fk_violations),
                "details": fk_violations if fk_violations else None
            }
            
            # Quick check
            cursor = conn.execute("PRAGMA quick_check")
            quick_result = cursor.fetchone()[0]
            results["checks"]["quick_check"] = {
                "status": "PASS" if quick_result == "ok" else "FAIL",
                "result": quick_result
            }
            
            # WAL mode check
            cursor = conn.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            results["checks"]["journal_mode"] = {
                "mode": journal_mode,
                "recommended": journal_mode in ["WAL", "MEMORY"]
            }
            
        overall_status = all(
            check.get("status") == "PASS" for check in results["checks"].values()
            if "status" in check
        )
        results["overall_status"] = "HEALTHY" if overall_status else "ISSUES_FOUND"
        
        print(f"   ✅ Database integrity: {results['overall_status']}")
        return results
    
    def analyze_performance(self) -> Dict:
        """Analyze database performance metrics."""
        print("📊 Analyzing database performance...")
        
        with sqlite3.connect(self.db_path) as conn:
            # Get database statistics
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM agents")
            agent_count = cursor.fetchone()[0]
            
            # Check database size
            db_size_bytes = self.db_path.stat().st_size
            db_size_mb = db_size_bytes / (1024 * 1024)
            
            # Analyze message distribution
            cursor = conn.execute("""
                SELECT priority, COUNT(*) 
                FROM messages 
                GROUP BY priority 
                ORDER BY COUNT(*) DESC
            """)
            priority_distribution = dict(cursor.fetchall())
            
            # Check unread messages
            cursor = conn.execute("SELECT COUNT(*) FROM messages WHERE read = FALSE")
            unread_count = cursor.fetchone()[0]
            
            # Analyze recent activity (last 24 hours)
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE timestamp > ?", 
                (yesterday,)
            )
            recent_messages = cursor.fetchone()[0]
            
            # Check for potential performance issues
            cursor = conn.execute("ANALYZE")
            
            # Get table sizes
            cursor = conn.execute("""
                SELECT name, 
                       (SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND tbl_name=name) as table_count
                FROM sqlite_master 
                WHERE type='table'
            """)
            tables = cursor.fetchall()
        
        performance_metrics = {
            "database_size": {
                "bytes": db_size_bytes,
                "megabytes": round(db_size_mb, 2),
                "size_per_message_bytes": round(db_size_bytes / message_count, 2) if message_count > 0 else 0
            },
            "message_metrics": {
                "total_messages": message_count,
                "unread_messages": unread_count,
                "recent_activity_24h": recent_messages,
                "priority_distribution": priority_distribution
            },
            "agent_metrics": {
                "total_agents": agent_count,
                "messages_per_agent": round(message_count / agent_count, 2) if agent_count > 0 else 0
            },
            "tables": {table[0]: {"exists": True} for table in tables}
        }
        
        # Performance recommendations
        recommendations = []
        
        if db_size_mb > 100:
            recommendations.append("Consider message cleanup for databases over 100MB")
        
        if unread_count > 1000:
            recommendations.append(f"High unread count ({unread_count}) may impact performance")
        
        if message_count > 50000:
            recommendations.append("Consider partitioning or archiving for large message volumes")
        
        performance_metrics["recommendations"] = recommendations
        
        print(f"   📊 {message_count} messages, {agent_count} agents, {db_size_mb:.1f}MB")
        return performance_metrics
    
    def optimize_database(self) -> Dict:
        """Optimize database performance."""
        print("⚡ Optimizing database...")
        
        optimization_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operations": []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")
            optimization_results["operations"].append({
                "operation": "enable_wal_mode",
                "status": "completed"
            })
            
            # Update statistics
            start_time = time.time()
            conn.execute("ANALYZE")
            analyze_duration = time.time() - start_time
            optimization_results["operations"].append({
                "operation": "analyze_statistics",
                "duration_seconds": round(analyze_duration, 3),
                "status": "completed"
            })
            
            # Rebuild indexes
            start_time = time.time()
            conn.execute("REINDEX")
            reindex_duration = time.time() - start_time
            optimization_results["operations"].append({
                "operation": "rebuild_indexes",
                "duration_seconds": round(reindex_duration, 3),
                "status": "completed"
            })
            
            # Vacuum database (compact and defragment)
            start_time = time.time()
            conn.execute("VACUUM")
            vacuum_duration = time.time() - start_time
            optimization_results["operations"].append({
                "operation": "vacuum_database",
                "duration_seconds": round(vacuum_duration, 3),
                "status": "completed"
            })
            
            # Optimize auto-vacuum setting
            conn.execute("PRAGMA auto_vacuum=INCREMENTAL")
            optimization_results["operations"].append({
                "operation": "set_auto_vacuum",
                "status": "completed"
            })
        
        total_duration = sum(
            op.get("duration_seconds", 0) 
            for op in optimization_results["operations"]
        )
        optimization_results["total_duration_seconds"] = round(total_duration, 3)
        
        print(f"   ⚡ Optimization completed in {total_duration:.2f}s")
        return optimization_results
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict:
        """Clean up old messages and data."""
        print(f"🧹 Cleaning up data older than {days_to_keep} days...")
        
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_to_keep)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Count messages to be deleted
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE timestamp < ?", 
                (cutoff_date,)
            )
            messages_to_delete = cursor.fetchone()[0]
            
            # Delete old messages
            cursor = conn.execute(
                "DELETE FROM messages WHERE timestamp < ?", 
                (cutoff_date,)
            )
            deleted_messages = cursor.rowcount
            
            # Clean up orphaned agents (no messages in last 90 days)
            agent_cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
            cursor = conn.execute(
                "DELETE FROM agents WHERE last_seen < ?", 
                (agent_cutoff,)
            )
            deleted_agents = cursor.rowcount
        
        cleanup_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cutoff_date": cutoff_date,
            "messages_deleted": deleted_messages,
            "agents_deleted": deleted_agents,
            "days_to_keep": days_to_keep
        }
        
        print(f"   🧹 Deleted {deleted_messages} old messages, {deleted_agents} inactive agents")
        return cleanup_results
    
    def backup_database(self, backup_dir: Optional[Path] = None) -> Dict:
        """Create a backup of the database."""
        if backup_dir is None:
            backup_dir = self.db_path.parent / "backups"
        
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"mailbox_backup_{timestamp}.db"
        
        print(f"💾 Creating database backup...")
        
        start_time = time.time()
        
        # Use SQLite backup API for consistent backup
        with sqlite3.connect(self.db_path) as source:
            with sqlite3.connect(backup_path) as dest:
                source.backup(dest)
        
        backup_duration = time.time() - start_time
        backup_size = backup_path.stat().st_size
        
        backup_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "backup_path": str(backup_path),
            "backup_size_bytes": backup_size,
            "backup_size_mb": round(backup_size / (1024 * 1024), 2),
            "duration_seconds": round(backup_duration, 3),
            "status": "completed"
        }
        
        print(f"   💾 Backup created: {backup_path.name} ({backup_results['backup_size_mb']}MB)")
        return backup_results
    
    def run_full_health_check(self) -> Dict:
        """Run complete health check and maintenance."""
        print("🏥 Running comprehensive database health check")
        print("=" * 50)
        
        start_time = time.time()
        
        health_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database_path": str(self.db_path),
            "checks": {}
        }
        
        try:
            # Run all health checks
            health_report["checks"]["integrity"] = self.check_integrity()
            health_report["checks"]["performance"] = self.analyze_performance()
            
            # Create backup before any modifications
            health_report["checks"]["backup"] = self.backup_database()
            
            # Optimize database
            health_report["checks"]["optimization"] = self.optimize_database()
            
            # Determine if cleanup is needed
            perf_data = health_report["checks"]["performance"]
            message_count = perf_data["message_metrics"]["total_messages"]
            
            if message_count > 10000:
                print("🧹 Large message count detected, running cleanup...")
                health_report["checks"]["cleanup"] = self.cleanup_old_data(30)
            
        except Exception as e:
            health_report["error"] = str(e)
            print(f"❌ Health check failed: {e}")
        
        total_duration = time.time() - start_time
        health_report["total_duration_seconds"] = round(total_duration, 3)
        
        # Overall health assessment
        integrity_status = health_report["checks"].get("integrity", {}).get("overall_status")
        health_report["overall_health"] = "HEALTHY" if integrity_status == "HEALTHY" else "NEEDS_ATTENTION"
        
        print(f"\n🏥 Health Check Summary:")
        print(f"   Overall Health: {health_report['overall_health']}")
        print(f"   Total Duration: {total_duration:.2f}s")
        
        return health_report


def main():
    """Run database health check from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Mail MCP Database Health Checker")
    parser.add_argument("--db-path", type=Path, 
                       default=Path.home() / ".ai_mail" / "mailbox.db",
                       help="Path to mailbox database")
    parser.add_argument("--full-check", action="store_true",
                       help="Run full health check and maintenance")
    parser.add_argument("--integrity-only", action="store_true",
                       help="Run integrity check only")
    parser.add_argument("--optimize", action="store_true",
                       help="Optimize database performance")
    parser.add_argument("--cleanup", type=int, metavar="DAYS",
                       help="Clean up messages older than DAYS")
    parser.add_argument("--backup", action="store_true",
                       help="Create database backup")
    
    args = parser.parse_args()
    
    if not args.db_path.exists():
        print(f"❌ Database not found: {args.db_path}")
        return 1
    
    checker = DatabaseHealthChecker(args.db_path)
    
    try:
        if args.full_check:
            result = checker.run_full_health_check()
        elif args.integrity_only:
            result = checker.check_integrity()
        elif args.optimize:
            result = checker.optimize_database()
        elif args.cleanup:
            result = checker.cleanup_old_data(args.cleanup)
        elif args.backup:
            result = checker.backup_database()
        else:
            # Default: run performance analysis
            result = checker.analyze_performance()
        
        # Save results
        output_file = Path(f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, "w") as f:
            import json
            json.dump(result, f, indent=2)
        
        print(f"\n📊 Results saved to: {output_file}")
        
        # Exit code based on health status
        overall_health = result.get("overall_health", "UNKNOWN")
        if overall_health == "HEALTHY":
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
