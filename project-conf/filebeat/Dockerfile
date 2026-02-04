# Filebeat: reads app log file(s) from shared volume and ships to Logstash.
FROM docker.elastic.co/beats/filebeat:8.11.0

USER root

COPY docker/filebeat/filebeat.template.yml /usr/share/filebeat/filebeat.template.yml
COPY docker/filebeat/entrypoint.sh /usr/share/filebeat/entrypoint.sh
RUN sed -i 's/\r$//g' /usr/share/filebeat/entrypoint.sh && chmod +x /usr/share/filebeat/entrypoint.sh

ENTRYPOINT ["/usr/share/filebeat/entrypoint.sh"]
