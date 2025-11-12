# Custom HAPI FHIR Image with Linux utilities and delayed IG installation
FROM hapiproject/hapi:latest

# Switch to root to install packages
USER root

# Install essential Linux utilities
RUN microdnf install -y \
    curl \
    bash \
    coreutils \
    findutils \
    && microdnf clean all

# Create directory for custom scripts
RUN mkdir -p /opt/hapi/scripts

# Copy custom startup script
COPY hapi-scripts/delayed-ig-install.sh /opt/hapi/scripts/
RUN chmod +x /opt/hapi/scripts/delayed-ig-install.sh

# Switch back to the original user
USER 1001

# Keep the original entrypoint
ENTRYPOINT ["/usr/bin/java", "-Djava.awt.headless=true", "-Djava.security.egd=file:/dev/./urandom", "-jar", "/app/main.war"]
