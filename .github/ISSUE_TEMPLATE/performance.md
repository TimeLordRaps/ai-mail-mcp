---
name: Performance Issue ⚡
about: Report performance problems or suggest optimizations
title: '[PERF] '
labels: ['performance', 'needs-investigation']
assignees: ''
---

## ⚡ Performance Issue Type
- [ ] 🐌 **Slow Performance**: Operations take too long
- [ ] 🧠 **High Memory Usage**: Excessive memory consumption
- [ ] 💾 **Database Issues**: Slow queries or storage problems
- [ ] 🔄 **Scalability**: Performance degrades with scale
- [ ] 📊 **Benchmarks**: Performance metrics don't meet expectations
- [ ] 💡 **Optimization Opportunity**: Identified potential improvement

## 📊 Performance Metrics
### Current Performance
- **Operation**: [e.g., sending 1000 messages, checking mail, database query]
- **Current Time**: [e.g., 10 seconds, 500ms, 2 minutes]
- **Current Memory**: [e.g., 100MB, 1GB]
- **Message Volume**: [e.g., 1000 messages, 10K messages]

### Expected Performance
- **Expected Time**: [e.g., should be under 2 seconds]
- **Expected Memory**: [e.g., should be under 50MB]
- **Benchmark Reference**: [e.g., mentioned in docs, compared to similar tools]

## 🔄 Steps to Reproduce
1. Set up environment with [specific configuration]
2. Perform [specific operation]
3. Measure [specific metric]
4. Observe [performance issue]

## 🖥️ Environment
**System Information:**
- **OS**: [e.g., Windows 10, Ubuntu 20.04, macOS 12.0]
- **Python Version**: [e.g., 3.9.0]
- **AI Mail MCP Version**: [e.g., 1.0.0]
- **Hardware**: 
  - CPU: [e.g., Intel i7-9700K, Apple M1]
  - RAM: [e.g., 16GB]
  - Storage: [e.g., SSD, HDD]

**Configuration:**
- **Message Count**: [e.g., 10,000 messages in database]
- **Agent Count**: [e.g., 5 active agents]
- **Database Size**: [e.g., 50MB]
- **Concurrent Users**: [e.g., 3 agents sending simultaneously]

## 📈 Profiling Data
<details>
<summary>Click to expand profiling information</summary>

### Timing Information
```
Paste timing output here (e.g., from time command or Python profiler)
```

### Memory Usage
```
Paste memory profiling data here
```

### Database Query Analysis
```sql
-- Slow queries identified
EXPLAIN QUERY PLAN SELECT ...
```

### Python Profiler Output
```
Paste cProfile or other profiler output here
```
</details>

## 📋 Logs
<details>
<summary>Click to expand relevant logs</summary>

```
Paste logs showing performance issues here
```
</details>

## 🔍 Investigation Done
**What have you already tried?**
- [ ] Tested with different data sizes
- [ ] Profiled the code
- [ ] Checked database indexes
- [ ] Monitored memory usage
- [ ] Tested on different hardware
- [ ] Compared with previous versions

## 💡 Suspected Cause
**What do you think might be causing this issue?**
- [ ] Database query optimization needed
- [ ] Memory leaks
- [ ] Inefficient algorithms
- [ ] Missing indexes
- [ ] Network latency
- [ ] File I/O bottleneck
- [ ] Not sure / need investigation

## 🎯 Proposed Solutions
**Ideas for how to fix this:**
1. **Solution 1**: [Description and expected impact]
2. **Solution 2**: [Description and expected impact]
3. **Solution 3**: [Description and expected impact]

## 📊 Impact Assessment
### User Impact
- **Severity**: 
  - [ ] Low (minor inconvenience)
  - [ ] Medium (affects productivity)
  - [ ] High (blocks normal usage)
  - [ ] Critical (system unusable)

### Affected Operations
- [ ] Message sending
- [ ] Message retrieval
- [ ] Database operations
- [ ] Agent registration
- [ ] Search functionality
- [ ] System startup
- [ ] Other: [specify]

## 🧪 Testing Suggestions
**How can this performance issue be reproduced for testing?**
```bash
# Provide specific commands or scripts to reproduce the issue
python benchmark_script.py --messages=10000 --agents=5
```

## 📚 Additional Context
- **Comparison Data**: How does this compare to similar tools?
- **Regression**: Did this work better in a previous version?
- **Workarounds**: Any temporary solutions you've found?
- **Business Impact**: How does this affect your workflow?

## ✅ Checklist
- [ ] I have provided specific performance metrics
- [ ] I have included profiling data where possible
- [ ] I have tested with different configurations
- [ ] I have searched for existing performance issues
- [ ] I have provided steps to reproduce the issue

## 🤝 Collaboration
- [ ] I can help test potential fixes
- [ ] I can provide more detailed profiling data
- [ ] I have access to different hardware for testing
- [ ] I can benchmark proposed solutions

---

**Note**: Performance issues are taken seriously and investigated thoroughly. Providing detailed metrics and profiling data helps us identify and fix bottlenecks more quickly.
