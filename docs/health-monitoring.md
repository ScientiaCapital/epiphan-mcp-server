# Fleet Health Monitoring

This document describes the health scoring system and alerting capabilities for Epiphan Pearl fleet management.

## Overview

The health monitoring system provides:
- **Per-device health scores** (0-100) for quick triage
- **Fleet-level aggregates** for dashboard views
- **AI-summarized reports** with prioritized recommendations
- **Automatic issue detection** with suggested remediation

## Health Score Calculation

### Scoring Breakdown

Each device receives a health score from 0-100 based on two categories:

| Category | Max Points | Description |
|----------|------------|-------------|
| Storage | 50 | Based on storage usage percentage |
| Recording | 50 | Based on recorder system accessibility |

### Storage Scoring

| Storage Used | Points | Status |
|--------------|--------|--------|
| < 75% | 50 | Healthy |
| 75-89% | 30 | Warning |
| ≥ 90% | 10 | Critical |

### Recording Scoring

| Recorder Status | Points | Status |
|-----------------|--------|--------|
| Accessible | 50 | Healthy |
| Degraded/Unreachable | 25 | Warning |

### Overall Thresholds

| Score Range | Status | Recommended Action |
|-------------|--------|-------------------|
| 80-100 | Healthy | No action needed |
| 60-79 | Minor Issues | Review when convenient |
| 40-59 | Needs Attention | Address issues soon |
| 0-39 | Unhealthy | Immediate attention required |

## API Reference

### get_fleet_status

Returns fleet status with health metrics.

```python
result = await get_fleet_status()
```

**Response includes:**
```json
{
  "success": true,
  "fleet_name": "classroom-pearls",
  "total_devices": 5,
  "online_devices": 4,
  "recording_devices": 2,
  "average_health": 92.5,
  "unhealthy_devices": 0,
  "devices": [
    {
      "host": "192.168.1.100",
      "online": true,
      "recording": true,
      "storage_percent": 45.2,
      "health_score": 100,
      "health_issues": []
    },
    {
      "host": "192.168.1.101",
      "online": true,
      "recording": false,
      "storage_percent": 85.0,
      "health_score": 80,
      "health_issues": ["Storage running low: 85% used"]
    }
  ],
  "alerts": [...]
}
```

### fleet_health_report

Generates an AI-summarized health report.

```python
result = await fleet_health_report()
```

**Response:**
```json
{
  "success": true,
  "fleet_name": "classroom-pearls",
  "generated_at": "2025-01-24T15:30:00.000Z",
  "summary": "Fleet is healthy with 4 of 5 devices online. 2 devices currently recording. One device (192.168.1.101) has storage at 85%.",
  "health_score": 92,
  "devices_online": 4,
  "devices_recording": 2,
  "attention_required": [
    {
      "device": "192.168.1.101",
      "issue": "Storage at 85%",
      "action": "Archive or delete old recordings"
    }
  ],
  "recommendations": [
    "Archive or delete old recordings on 192.168.1.101",
    "Continue monitoring fleet health"
  ]
}
```

## Alerting Integration

### Storage Alerts

Storage alerts are generated when `storage_percent > storage_warning_percent` (default: 80%).

Configure via environment:
```bash
PEARL_STORAGE_WARNING_PERCENT=80
```

### Alert Severities

| Severity | Trigger |
|----------|---------|
| `error` | Device offline or unreachable |
| `warning` | Storage above warning threshold |

### Webhook Integration (Coming Soon)

Future releases will support webhook notifications:
```bash
# Planned configuration
PEARL_WEBHOOK_URL=https://your-endpoint.com/alerts
PEARL_WEBHOOK_ON_UNHEALTHY=true
```

## Usage Examples

### Claude Desktop / Claude Code

```
You: How healthy is my fleet?
Claude: [Calls fleet_health_report]
        Fleet "classroom-pearls" is healthy with average score 92/100.
        4 of 5 devices online, 2 recording.

        Attention needed:
        - Room 201 (192.168.1.101): Storage at 85% - archive old recordings

        Recommendation: Clear storage on Room 201 before next week's events.

You: What about the offline device?
Claude: [Calls get_fleet_status]
        192.168.1.104 is offline since the last check.
        Error: Connection refused

        Recommended action: Check network connectivity and power in Room 305.
```

### Programmatic Access

```python
from epiphan_mcp.server import get_fleet_status, fleet_health_report

# Quick health check
status = await get_fleet_status.fn()
if status["unhealthy_devices"] > 0:
    print(f"Warning: {status['unhealthy_devices']} devices need attention")

# Detailed report
report = await fleet_health_report.fn()
for item in report["attention_required"]:
    print(f"{item['device']}: {item['issue']} - {item['action']}")
```

## Best Practices

1. **Monitor `average_health`** - Dashboard metric for fleet overview
2. **Alert on `unhealthy_devices > 0`** - Trigger notifications
3. **Review `attention_required`** - Daily check for issues
4. **Schedule maintenance** when `storage_percent > 70%`
5. **Use `fleet_health_report`** for shift handoffs

## Extending Health Scoring

The health scoring system can be extended by modifying `_calculate_health_score()` in `server.py`:

```python
def _calculate_health_score(
    storage_used_percent: float,
    recorder_accessible: bool = True,
    # Add new parameters here
    temperature_celsius: float | None = None,
    uptime_hours: float | None = None,
) -> dict[str, Any]:
    # Add scoring logic for new metrics
    pass
```

Future categories planned:
- CPU/memory utilization
- Network latency
- Input signal quality
- Firmware version currency
