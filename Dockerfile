FROM quay.io/keycloak/keycloak:26.8.2-3
USER root
COPY realm/recepta-realm.json /opt/keycloak/data/import/recepta-realm.json
RUN chown -R keycloak:keycloak /opt/keycloak/data/import \
    && chmod 644 /opt/keycloak/data/import/recepta-realm.json
USER keycloak
ENV KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true KC_DB=postgres
RUN /opt/keycloak/bin/kc.sh build
CMD ["start", "--optimized"]
