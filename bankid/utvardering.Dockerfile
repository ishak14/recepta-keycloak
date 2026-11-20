# Bara för utvärdering, se UTVARDERING.md. Ingår inte i avbilden.
# Bygger bankid4keycloak (låst commit) mot en vald Keycloak-version.
FROM maven:3.9-eclipse-temurin-21 AS build
ARG BANKID4KEYCLOAK_SHA=34a5932d13005a67ae34ce1f6e6537fe798e1707
ARG KEYCLOAK_VERSION=26.8.2
ARG PROTOSTREAM_VERSION=15.0.13.Final
ADD https://github.com/sweid4keycloak/bankid4keycloak/archive/${BANKID4KEYCLOAK_SHA}.tar.gz /src.tgz
RUN mkdir /source && tar -xzf /src.tgz -C /source --strip-components=1
WORKDIR /source
RUN mvn -B -ntp -DskipTests -Dkeycloak.version=${KEYCLOAK_VERSION} -Dprotostream.version=${PROTOSTREAM_VERSION} package 2>&1 | tee /build.log; ls -la target/*.jar

FROM quay.io/keycloak/keycloak:26.8.2-3 AS load
COPY --from=build /source/target/bankid4keycloak-26.0.0-SNAPSHOT.jar /opt/keycloak/providers/
ENV KC_DB=postgres
RUN /opt/keycloak/bin/kc.sh build 2>&1 | tee /tmp/kc-build.log
