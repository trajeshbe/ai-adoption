#!/usr/bin/env bash
set -euo pipefail

# Scan all service Docker images with Trivy for HIGH and CRITICAL vulnerabilities.
#
# Usage:
#   ./tests/security/scan-images.sh
#   REGISTRY=myregistry.io TAG=v1.0.0 ./tests/security/scan-images.sh
#   FORMAT=json ./tests/security/scan-images.sh

REGISTRY="${REGISTRY:-ghcr.io/trajeshbe}"
TAG="${TAG:-latest}"
FORMAT="${FORMAT:-table}"
RESULTS_DIR="${RESULTS_DIR:-results/trivy}"
SEVERITY="${SEVERITY:-HIGH,CRITICAL}"
CONFIG_FILE="$(dirname "$0")/trivy-config.yaml"

IMAGES=(gateway agent-engine document-service cache-service cost-tracker frontend)

# Create results directory if outputting JSON
if [[ "${FORMAT}" == "json" ]]; then
    mkdir -p "${RESULTS_DIR}"
fi

EXIT_CODE=0

echo "========================================="
echo " Trivy Image Security Scan"
echo " Registry: ${REGISTRY}"
echo " Tag:      ${TAG}"
echo " Severity: ${SEVERITY}"
echo " Format:   ${FORMAT}"
echo "========================================="
echo ""

for img in "${IMAGES[@]}"; do
    FULL_IMAGE="${REGISTRY}/ai-adoption-${img}:${TAG}"
    echo "-----------------------------------------"
    echo "Scanning: ${FULL_IMAGE}"
    echo "-----------------------------------------"

    TRIVY_ARGS=(
        image
        --severity "${SEVERITY}"
        --ignore-unfixed
        --format "${FORMAT}"
    )

    if [[ "${FORMAT}" == "json" ]]; then
        TRIVY_ARGS+=(--output "${RESULTS_DIR}/${img}.json")
    fi

    TRIVY_ARGS+=("${FULL_IMAGE}")

    if ! trivy "${TRIVY_ARGS[@]}"; then
        echo "WARN: Scan found vulnerabilities in ${img}"
        EXIT_CODE=1
    fi

    echo ""
done

echo "========================================="
if [[ ${EXIT_CODE} -eq 0 ]]; then
    echo " All images passed security scan."
else
    echo " Some images have HIGH/CRITICAL vulnerabilities."
    echo " Review the output above for details."
fi
echo "========================================="

exit ${EXIT_CODE}
