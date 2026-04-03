"""Sample unit tests (no GEE / DB required)."""

from app.schemas import NDVIRequest, SamplePointRequest


def test_ndvi_request_accepts_polygon_roi():
    body = NDVIRequest(
        roi={
            "type": "Polygon",
            "coordinates": [[[78.0, 17.0], [78.1, 17.0], [78.1, 17.1], [78.0, 17.1], [78.0, 17.0]]],
        },
        start_date="2024-01-01",
        end_date="2024-03-01",
        satellite="sentinel2",
        max_cloud_pct=20,
    )
    assert body.satellite == "sentinel2"


def test_sample_point_request():
    SamplePointRequest(
        roi={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        lat=17.4,
        lon=78.5,
        start_date="2024-01-01",
        end_date="2024-02-01",
        satellite="landsat89",
    )
