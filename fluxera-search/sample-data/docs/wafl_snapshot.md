# WAFL Snapshot Architecture

WAFL snapshots are point-in-time, read-only copies of a filesystem metadata state.

Snapshots use a redirect-on-write mechanism where changed blocks are written to new locations while unchanged blocks are shared.

This provides space efficiency, rapid restore points, and low overhead compared with full physical copies.
