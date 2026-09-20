from app.visual.catalog import CATALOG, catalog_ids


def test_asset_catalog_has_license_on_every_row():
    assert catalog_ids()
    for row in CATALOG:
        assert row["id"]
        assert row["source"]
        assert row["license"]
        assert row["category"]
