# Use the official DuckDB image
FROM duckdb/duckdb:latest

# Set the working directory inside the container to /data
# This is where we will mount our local GTFS files
WORKDIR /data

# Default entrypoint is the DuckDB CLI
ENTRYPOINT ["duckdb"]