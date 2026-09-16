# WINDOWS / DEFENDER TELEMETRY WAR MATRIX — 2026-09-15

## Commander direction
Windows Event Viewer and Defender telemetry are standard server evidence planes for server diagnosis, Daemon/MVF decision-making, and any project failure investigation—not emergency afterthoughts.

## Verified trigger
Defender event 1116 at 2026-09-15 18:43:42-04:00 detected `Trojan:Win32/ClickFix.DAD!MTB` Severity Severe on the exact PCMMAD Daemon soak PowerShell command; event 1117 at 18:43:55 recorded remediation and `Get-MpThreatDetection` reports ActionSuccess true. This explains at least one campaign harness failure. It does not by itself establish cause of the later Receiver outage.

## Required native repertoire
- bounded event-log query: log/provider/event-id/level/time/text/path filters;
- Defender detections/history/current status;
- correlation by time, process identity, path/repo, task, command lineage;
- standard project-failure discriminator querying security telemetry when execution/file/process behavior is anomalous;
- compact evidence handles rather than log dumps;
- exact log/record/event IDs retained.

## Laws
- `SECURITY PRODUCT EVENT != CAUSE`
- `DEFENDER DETECTION != RECEIVER OUTAGE CAUSE`
- `FAILED HARNESS + DEFENDER HIT = SECURITY TELEMETRY ENTERS CAUSAL CHAIN`
- `NO EVENT FOUND != EVENT LOG DISABLED`
- `ANTIVIRUS REMEDIATED != ORIGINAL WORKLOAD COMPLETED`

## Hostile matrix
Defender kill mid-write, quarantine after task registration, false positive on generated script, detection only on command line, path removed while process alive, stale protection history, log channel disabled, access denied to channel, giant event payload, duplicate events, clock skew, detection after causal failure, unrelated severe detection nearby, remediation success with orphan child, service/task restart after quarantine.
