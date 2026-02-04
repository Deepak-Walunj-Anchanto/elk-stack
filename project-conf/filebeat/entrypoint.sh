#!/bin/sh
set -e

LOGSTASH_HOST="${LOGSTASH_HOST:-logstash}"
LOGSTASH_PORT="${LOGSTASH_PORT:-5044}"

sed "s|\${LOGSTASH_HOST}|${LOGSTASH_HOST}|g; s|\${LOGSTASH_PORT}|${LOGSTASH_PORT}|g" \
  /usr/share/filebeat/filebeat.template.yml > /usr/share/filebeat/filebeat.yml

exec filebeat -c /usr/share/filebeat/filebeat.yml -e
