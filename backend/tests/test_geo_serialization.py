"""Job/Service responses must expose latitude/longitude from PostGIS."""

import binascii
import unittest
from datetime import datetime, timezone

from geoalchemy2.elements import WKBElement

from models import Job, Service
from schemas import FundingStatus, JobResponse, JobStatus, ServiceResponse, ServiceStatus

# POINT(3.3 6.6), SRID 4326, little-endian WKB.
POINT_WKB = binascii.unhexlify(
    "0101000020E61000006666666666660A406666666666661A40"
)


def location() -> WKBElement:
    return WKBElement(POINT_WKB, srid=4326)


class GeoSerializationTests(unittest.TestCase):
    def test_job_response_exposes_latitude_and_longitude(self):
        now = datetime.now(timezone.utc)
        job = Job(
            id=1,
            owner_id=1,
            category_id=1,
            title="Fix the sink",
            description="Leaking tap",
            budget=5000,
            status=JobStatus.OPEN,
            location=location(),
            location_name="Lagos",
            funding_status=FundingStatus.FUNDED,
            client_completed=False,
            worker_completed=False,
            created_at=now,
            updated_at=now,
        )

        response = JobResponse.model_validate(job)

        self.assertAlmostEqual(response.latitude, 6.6, places=5)
        self.assertAlmostEqual(response.longitude, 3.3, places=5)

    def test_service_response_exposes_latitude_and_longitude(self):
        now = datetime.now(timezone.utc)
        service = Service(
            id=1,
            business_id=1,
            title="Plumbing",
            description="Fix leaks",
            starting_price=5000,
            status=ServiceStatus.ACTIVE,
            category_id=1,
            location=location(),
            location_name="Lagos",
            created_at=now,
            updated_at=now,
        )

        response = ServiceResponse.model_validate(service)

        self.assertAlmostEqual(response.latitude, 6.6, places=5)
        self.assertAlmostEqual(response.longitude, 3.3, places=5)


if __name__ == "__main__":
    unittest.main()
