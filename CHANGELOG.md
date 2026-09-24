# Change log

## 2.0.5
- Start influxd through the packaged influxdb.service so it keeps running as the 'influxdb' user; never start it as the dashboard user or kill the service (fixes 'permission denied' on /var/lib/influxdb after upgrading from 1.2.x)

## 2.0.4
- Fix path traversal in log file APIs (CVE-2026-25069): validate filename for get-log and delete-log-file
- Harden API: mask secrets in get-config, whitelist history keys, restrict CORS to same-origin

## 1.4.x
- Change config to outside handling
- Remove deprecated code
- Remove influxdb log