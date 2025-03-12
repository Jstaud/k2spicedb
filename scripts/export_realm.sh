#!/bin/bash

# Example script to export Keycloak realms using kcadm.sh

# Check if the required arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <realm-name> <output-file>"
    exit 1
fi

REALM_NAME=$1
OUTPUT_FILE=$2

# Set the path to kcadm.sh
KC_PATH="/path/to/keycloak/bin/kcadm.sh"

# Login to Keycloak
$KC_PATH config credentials --server http://localhost:8080/auth --realm master --user admin --password admin

# Export the realm
$KC_PATH get realms/$REALM_NAME -o $OUTPUT_FILE

echo "Realm export saved to $OUTPUT_FILE"
