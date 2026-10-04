"""Fetch / refresh every open dataset into backend/data/external (needs internet).

  python -m scripts.ingest.fetch_all            # uses cached responses where present
  python -m scripts.ingest.fetch_all --refresh  # re-download everything
"""
import sys

from scripts.ingest import census, dem, osm_boundaries, osm_features, sentinel


def main(refresh: bool = False):
    print("[fetch] 1/5 OSM ward boundaries")
    osm_boundaries.fetch_ward_boundaries(refresh)
    print("[fetch] 2/5 Census 2011 ward tables")
    census.build_census_table(refresh)
    print("[fetch] 3/5 OSM assets, gazetteer, road stats, land use")
    osm_features.run_all(refresh)
    print("[fetch] 4/5 Copernicus DEM (optional deps)")
    dem.run(refresh)
    print("[fetch] 5/5 Sentinel-2 composites (optional deps, several minutes)")
    sentinel.run(refresh)
    print("[fetch] done")


if __name__ == "__main__":
    main("--refresh" in sys.argv)
