#!/usr/bin/env python3
"""
Monitoring and alerting system for AI Mail MCP.

This script provides continuous monitoring, metrics collection, and alerting
for the AI Mail MCP system.
"""

import json
import smtplib
import time
from datetime import datetime, timezone, timedelta
from email.mime.text import MimeText
from pathlib import Path
from typing import Dict, List, Optional, Any
import sqlite3
import psutil
import os


class MailboxMonitor:
    """Monitor AI Mail MCP system health and performance."""
    
    def __init__(self, db_path: Path, config: Optional[Dict] = None):
        self.db_path = db_path
        self.config = config or self._get_default_config()
        self.alerts = []
        
    def _get_default_config(self) -> Dict:
        """Get default monitoring configuration."""
        return {
            "thresholds": {
                "max_unread_messages": 1000,
                "max_db_size_mb": 500,
                "max_response_time_ms": 1000,
                "min_free_disk_mb": 100,
                "max_memory_usage_mb": 200
            },
            "alerts": {
                "email_enabled": False,
                "smtp_server": "localhost",
                "smtp_port": 587,
                "from_email": "monitor@aimail.local",
                "to_emails": ["admin@aimail.local"],
                "webhook_url": None
            },
            "monitoring": {
                "check_interval_seconds": 300,  # 5 minutes
                "history_retention_days": 7,
                "metrics_file": "monitoring_metrics.json"
            }
        }
    
    def collect_metrics(self) -> Dict:
        """Collect comprehensive system metrics."""
        timestamp = datetime.now(timezone.utc).isoformat()
        metrics = {
            "timestamp": timestamp,
            "database": self._collect_database_metrics(),
            "system": self._collect_system_metrics(),
            "performance": self._collect_performance_metrics()
        }
        
        return metrics
    
    def _collect_database_metrics(self) -> Dict:
        """Collect database-specific metrics."""
        if not self.db_path.exists():
            return {"status": "database_not_found", "error": f"Database not found: {self.db_path}"}
        
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                # Message metrics
                cursor = conn.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM messages WHERE read = FALSE")
                unread_messages = cursor.fetchone()[0]
                
                cursor = conn.execute("SELECT COUNT(*) FROM agents")
                total_agents = cursor.fetchone()[0]
                
                # Recent activity (last hour)
                hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM messages WHERE timestamp > ?", 
                    (hour_ago,)
                )
                recent_messages = cursor.fetchone()[0]
                
                # Database size
                db_size = self.db_path.stat().st_size
                
                # Priority distribution
                cursor = conn.execute("""
                    SELECT priority, COUNT(*) 
                    FROM messages 
                    GROUP BY priority
                """)
                priority_dist = dict(cursor.fetchall())
                
                return {
                    "status": "healthy",
                    "total_messages": total_messages,
                    "unread_messages": unread_messages,
                    "total_agents": total_agents,
                    "recent_activity_1h": recent_messages,
                    "database_size_bytes": db_size,
                    "database_size_mb": round(db_size / (1024 * 1024), 2),
                    "priority_distribution": priority_dist,
                    "messages_per_agent": round(total_messages / total_agents, 2) if total_agents > 0 else 0
                }
                
        except sqlite3.Error as e:
            return {"status": "database_error", "error": str(e)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _collect_system_metrics(self) -> Dict:
        """Collect system resource metrics."""
        try:
            # Memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            
            # Disk usage
            disk_usage = psutil.disk_usage(self.db_path.parent)
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                "status": "healthy",
                "memory_usage_mb": round(memory_info.rss / (1024 * 1024), 2),
                "cpu_percent": cpu_percent,
                "disk_free_mb": round(disk_usage.free / (1024 * 1024), 2),
                "disk_total_mb": round(disk_usage.total / (1024 * 1024), 2),
                "disk_used_percent": round((disk_usage.used / disk_usage.total) * 100, 2)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _collect_performance_metrics(self) -> Dict:
        """Collect performance metrics through basic operations."""
        if not self.db_path.exists():
            return {"status": "database_not_found"}
        
        try:
            # Test database response time
            start_time = time.time()
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute("SELECT COUNT(*) FROM messages LIMIT 1").fetchone()
            db_response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Test message insertion performance
            start_time = time.time()
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                test_id = f"perf-test-{int(time.time())}"
                conn.execute("""
                    INSERT INTO messages (id, sender, recipient, subject, body, timestamp, read)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_id, "monitor", "test", "Performance Test", 
                    "Test message for monitoring", 
                    datetime.now(timezone.utc).isoformat(), 
                    True
                ))
                # Clean up test message
                conn.execute("DELETE FROM messages WHERE id = ?", (test_id,))
            insert_time = (time.time() - start_time) * 1000
            
            return {
                "status": "healthy",
                "db_response_time_ms": round(db_response_time, 3),
                "insert_time_ms": round(insert_time, 3),
                "performance_score": self._calculate_performance_score(db_response_time, insert_time)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def _calculate_performance_score(self, response_time_ms: float, insert_time_ms: float) -> str:
        """Calculate overall performance score."""
        # Performance scoring based on response times
        if response_time_ms < 10 and insert_time_ms < 50:
            return "excellent"
        elif response_time_ms < 50 and insert_time_ms < 200:
            return "good"
        elif response_time_ms < 200 and insert_time_ms < 500:
            return "acceptable"
        else:
            return "poor"
    
    def check_thresholds(self, metrics: Dict) -> List[Dict]:
        """Check metrics against configured thresholds."""
        alerts = []
        thresholds = self.config["thresholds"]
        
        # Database alerts
        db_metrics = metrics.get("database", {})
        if db_metrics.get("status") != "healthy":
            alerts.append({
                "level": "critical",
                "type": "database_error",
                "message": f"Database error: {db_metrics.get('error', 'Unknown error')}",
                "timestamp": metrics["timestamp"]
            })
        else:
            # Check unread messages
            unread = db_metrics.get("unread_messages", 0)
            if unread > thresholds["max_unread_messages"]:
                alerts.append({
                    "level": "warning",
                    "type": "high_unread_count",
                    "message": f"High unread message count: {unread} (threshold: {thresholds['max_unread_messages']})",
                    "value": unread,
                    "threshold": thresholds["max_unread_messages"],
                    "timestamp": metrics["timestamp"]
                })
            
            # Check database size
            db_size_mb = db_metrics.get("database_size_mb", 0)
            if db_size_mb > thresholds["max_db_size_mb"]:
                alerts.append({
                    "level": "warning",
                    "type": "large_database",
                    "message": f"Database size is large: {db_size_mb}MB (threshold: {thresholds['max_db_size_mb']}MB)",
                    "value": db_size_mb,
                    "threshold": thresholds["max_db_size_mb"],
                    "timestamp": metrics["timestamp"]
                })
        
        # System alerts
        sys_metrics = metrics.get("system", {})
        if sys_metrics.get("status") == "healthy":
            # Check memory usage
            memory_mb = sys_metrics.get("memory_usage_mb", 0)
            if memory_mb > thresholds["max_memory_usage_mb"]:
                alerts.append({
                    "level": "warning",
                    "type": "high_memory_usage",
                    "message": f"High memory usage: {memory_mb}MB (threshold: {thresholds['max_memory_usage_mb']}MB)",
                    "value": memory_mb,
                    "threshold": thresholds["max_memory_usage_mb"],
                    "timestamp": metrics["timestamp"]
                })
            
            # Check disk space
            disk_free_mb = sys_metrics.get("disk_free_mb", 0)
            if disk_free_mb < thresholds["min_free_disk_mb"]:
                alerts.append({
                    "level": "critical",
                    "type": "low_disk_space",
                    "message": f"Low disk space: {disk_free_mb}MB free (threshold: {thresholds['min_free_disk_mb']}MB)",
                    "value": disk_free_mb,
                    "threshold": thresholds["min_free_disk_mb"],
                    "timestamp": metrics["timestamp"]
                })
        
        # Performance alerts
        perf_metrics = metrics.get("performance", {})
        if perf_metrics.get("status") == "healthy":
            response_time = perf_metrics.get("db_response_time_ms", 0)
            if response_time > thresholds["max_response_time_ms"]:
                alerts.append({
                    "level": "warning",
                    "type": "slow_response",
                    "message": f"Slow database response: {response_time}ms (threshold: {thresholds['max_response_time_ms']}ms)",
                    "value": response_time,
                    "threshold": thresholds["max_response_time_ms"],
                    "timestamp": metrics["timestamp"]
                })
            
            perf_score = perf_metrics.get("performance_score")
            if perf_score == "poor":
                alerts.append({
                    "level": "warning",
                    "type": "poor_performance",
                    "message": "Database performance is poor",
                    "timestamp": metrics["timestamp"]
                })
        
        return alerts
    
    def send_alerts(self, alerts: List[Dict]) -> Dict:
        """Send alerts via configured channels."""
        if not alerts:
            return {"sent": 0, "channels": []}
        
        results = {"sent": 0, "channels": [], "errors": []}
        
        # Email alerts
        if self.config["alerts"]["email_enabled"]:
            try:
                self._send_email_alerts(alerts)
                results["channels"].append("email")
                results["sent"] += len(alerts)
            except Exception as e:
                results["errors"].append(f"Email alert failed: {e}")
        
        # Webhook alerts
        webhook_url = self.config["alerts"].get("webhook_url")
        if webhook_url:
            try:
                self._send_webhook_alerts(alerts, webhook_url)
                results["channels"].append("webhook")
                results["sent"] += len(alerts)
            except Exception as e:
                results["errors"].append(f"Webhook alert failed: {e}")
        
        # Log alerts to file
        try:
            self._log_alerts(alerts)
            results["channels"].append("log")
        except Exception as e:
            results["errors"].append(f"Log alert failed: {e}")
        
        return results
    
    def _send_email_alerts(self, alerts: List[Dict]):
        """Send alerts via email."""
        config = self.config["alerts"]
        
        # Group alerts by level
        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        warning_alerts = [a for a in alerts if a["level"] == "warning"]
        
        subject = f"AI Mail MCP Alert - {len(critical_alerts)} Critical, {len(warning_alerts)} Warning"
        
        body = f"""AI Mail MCP Monitoring Alert
        
Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
Database: {self.db_path}

CRITICAL ALERTS ({len(critical_alerts)}):
"""
        
        for alert in critical_alerts:
            body += f"- {alert['message']}\n"
        
        body += f"\nWARNING ALERTS ({len(warning_alerts)}):\n"
        for alert in warning_alerts:
            body += f"- {alert['message']}\n"
        
        body += "\nFull alert details available in monitoring logs."
        
        msg = MimeText(body)
        msg['Subject'] = subject
        msg['From'] = config["from_email"]
        msg['To'] = ", ".join(config["to_emails"])
        
        with smtplib.SMTP(config["smtp_server"], config["smtp_port"]) as server:
            server.starttls()
            server.send_message(msg)
    
    def _send_webhook_alerts(self, alerts: List[Dict], webhook_url: str):
        """Send alerts via webhook."""
        import urllib.request
        import urllib.parse
        
        payload = {
            "alerts": alerts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "ai-mail-mcp-monitor",
            "database": str(self.db_path)
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            return response.read()
    
    def _log_alerts(self, alerts: List[Dict]):
        """Log alerts to file."""
        log_file = Path("ai_mail_alerts.log")
        
        with open(log_file, "a") as f:
            for alert in alerts:
                log_entry = {
                    "timestamp": alert["timestamp"],
                    "level": alert["level"],
                    "type": alert["type"],
                    "message": alert["message"]
                }
                f.write(json.dumps(log_entry) + "\n")
    
    def save_metrics(self, metrics: Dict):
        """Save metrics to file for historical tracking."""
        metrics_file = Path(self.config["monitoring"]["metrics_file"])
        
        # Load existing metrics
        if metrics_file.exists():
            with open(metrics_file) as f:
                history = json.load(f)
        else:
            history = {"metrics": []}
        
        # Add new metrics
        history["metrics"].append(metrics)
        
        # Trim old metrics based on retention policy
        retention_days = self.config["monitoring"]["history_retention_days"]
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        history["metrics"] = [
            m for m in history["metrics"]
            if datetime.fromisoformat(m["timestamp"]) > cutoff_date
        ]
        
        # Save updated history
        with open(metrics_file, "w") as f:
            json.dump(history, f, indent=2)
    
    def run_monitoring_cycle(self) -> Dict:
        """Run a complete monitoring cycle."""
        print(f"🔍 Running monitoring cycle at {datetime.now()}")
        
        # Collect metrics
        metrics = self.collect_metrics()
        
        # Check for alerts
        alerts = self.check_thresholds(metrics)
        
        # Send alerts if any
        alert_results = self.send_alerts(alerts) if alerts else {"sent": 0, "channels": []}
        
        # Save metrics history
        self.save_metrics(metrics)
        
        cycle_result = {
            "timestamp": metrics["timestamp"],
            "metrics_collected": True,
            "alerts_found": len(alerts),
            "alerts_sent": alert_results["sent"],
            "alert_channels": alert_results["channels"],
            "alert_errors": alert_results.get("errors", []),
            "status": "completed"
        }
        
        # Print summary
        if alerts:
            critical_count = len([a for a in alerts if a["level"] == "critical"])
            warning_count = len([a for a in alerts if a["level"] == "warning"])
            print(f"   🚨 {critical_count} critical, {warning_count} warning alerts")
        else:
            print("   ✅ All systems healthy")
        
        return cycle_result


def main():
    """Run monitoring from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Mail MCP Monitor")
    parser.add_argument("--db-path", type=Path,
                       default=Path.home() / ".ai_mail" / "mailbox.db",
                       help="Path to mailbox database")
    parser.add_argument("--config", type=Path,
                       help="Path to monitoring configuration file")
    parser.add_argument("--daemon", action="store_true",
                       help="Run as daemon (continuous monitoring)")
    parser.add_argument("--once", action="store_true",
                       help="Run once and exit")
    parser.add_argument("--interval", type=int, default=300,
                       help="Monitoring interval in seconds (default: 300)")
    
    args = parser.parse_args()
    
    # Load configuration
    config = None
    if args.config and args.config.exists():
        with open(args.config) as f:
            config = json.load(f)
    
    monitor = MailboxMonitor(args.db_path, config)
    
    if args.daemon:
        print(f"🤖 Starting AI Mail MCP Monitor daemon (interval: {args.interval}s)")
        try:
            while True:
                monitor.run_monitoring_cycle()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n👋 Monitor daemon stopped")
    else:
        # Run once
        result = monitor.run_monitoring_cycle()
        
        # Exit with error code if there are critical alerts
        alerts = monitor.check_thresholds(monitor.collect_metrics())
        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        
        return 1 if critical_alerts else 0


if __name__ == "__main__":
    exit(main())
