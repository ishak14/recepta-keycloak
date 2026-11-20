FROM quay.io/keycloak/keycloak:26.8.2-3
ENV KC_HEALTH_ENABLED=true KC_METRICS_ENABLED=true KC_DB=postgres
RUN /opt/keycloak/bin/kc.sh build
CMD ["start", "--optimized"]
