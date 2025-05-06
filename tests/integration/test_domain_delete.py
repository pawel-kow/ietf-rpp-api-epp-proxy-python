import pytest
import connexion
import json
import uuid
from run import app
import datetime
from tests.helper.integration_api_test import endpoint_test
from tests.helper.check_datetime import check_datetime_format_utc_and_delta


app.app.config.update({
        "TESTING": True,
    })

# --- Test Client Fixture ---
@pytest.fixture(scope='module')
def client():
    """Provides a test client for the Flask application."""
    with app.test_client() as c:
        yield c # The test client instance

random_name = str(uuid.uuid4())  # Generate a random name for testing
test_start = datetime.datetime.now(datetime.UTC)

# --- Test Data ---
# Define various test scenarios for integration testing via HTTP client
# NOTE: Expected responses now depend on the *actual* JSON returned by the API endpoint.
# Error responses (400, 500) should match the structure defined by Connexion/Flask ProblemException.

# Prepare test cases
# Ensure that a contact handle FOO-TEST1, FOO-TEST2, FOO-TEST3, FOO-TEST4 exist in the database
# Ensure that host objects ns1.bar.example and ns2.bar.example exist in the database
# Ensure that the domain NOT-FREE.EXAMPLE is already taken in the database
test_cases = [
    { "test_id": "test1-simple_delete",
       "steps": [{"request": { # create a domain first
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"test1-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
            "body": {
                "name": f"test1-{random_name}.example".upper(),
                "status": [
                    "ok"
                ]
            },
            "fields": {},
            "headers": {},
        }},
        {"request": { # delete the domain
            "method": "DELETE",
            "url": f"/domains/test1-{random_name}.example",
            "headers": {}
        },
        "response": {
            "status": [204, 202],
        }}
        ]
    },
    { "test_id": "test2-simple_delete_domain_not_existing",
      "steps": [{"request": {
            "method": "DELETE",
            "url": f"/domains/test2-{random_name}.example",
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test2-{random_name}-clTRID"
            }
        },
        "response": {
            "status": 404,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test2-{random_name}-clTRID"
            },
        }}]
    },
    { "test_id": "test3-request_with_body",
      "steps": [{"request": { # create a domain first
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"test3-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
            "body": {
                "name": f"test3-{random_name}.example".upper(),
                "status": [
                    "ok"
                ]
            },
            "fields": {},
            "headers": {},
        }},
        {"request": {
            "method": "DELETE",
            "url": f"/domains/test3-{random_name}.example",
            "body_raw": "test",
            "headers": {
                "RPP-clTRID": f"test3-{random_name}-clTRID"
            },
        },
        "response": {
            "status": 400,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test3-{random_name}-clTRID"
            },
        }}]
    },
    { "test_id": "test4-request_with_body_json_and_content_type",
      "steps": [{"request": {
            "method": "DELETE",
            "url": f"/domains/test4-{random_name}.example",
            "body_json": {
                "name": f"NOT-FREE.EXAMPLE",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test4-{random_name}-clTRID"
            }
        },
        "response": {
            "status": 400,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test4-{random_name}-clTRID"
            },
        }}]
    },
]

# --- Test Function ---
@pytest.mark.parametrize("case", test_cases, ids=[f"{__name__.replace("test_", "")}-{c["test_id"]}" for c in test_cases])
def test_domains_Delete(client, case):
    return endpoint_test(client, case)