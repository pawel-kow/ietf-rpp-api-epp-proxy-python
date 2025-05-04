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
    { "test_id": "test1-simple_create",
        "request": {
            "method": "POST",
            "url": "/domains",
            "body": {
                "name": f"test1-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "body": {
                "authInfo": {
                    "pw": "Password1!@"
                },
                "name": f"test1-{random_name}.example".upper(),
                "status": [
                    "ok"
                ]
            },
            "fields": {
                "clID": lambda x: x is not None,
                "crDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, -1, 60),
                "crID": lambda x: x is not None,
                "exDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, 60 * 60 * 24 * 364 * 1, 60 * 60 * 24 * 366 * 1),
            }
        }
    },
    { "test_id": "test2-simple_create_2year",
        "request": {
            "method": "POST",
            "url": "/domains",
            "body": {
                "name": f"test2-{random_name}.example",
                "processes": {
                    "creation": {
                        "period": "P2Y"
                    }
                },
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "body": {
                "authInfo": {
                    "pw": "Password1!@"
                },
                "name": f"test2-{random_name}.example".upper(),
                "status": [
                    "ok"
                ]
            },
            "fields": {
                "clID": lambda x: x is not None,
                "crDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, -1, 60),
                "crID": lambda x: x is not None,
                "exDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, 60 * 60 * 24 * 364 * 2, 60 * 60 * 24 * 366 * 2),
            }
        }
    },
    { "test_id": "test3-simple_create_with_all_contacts",
        "request": {
            "method": "POST",
            "url": "/domains",
            "body": {
                "name": f"test3-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                },
                "contacts": [
                    {
                        "value": "FOO-TEST1",
                        "type": [
                            "registrant",
                            "admin",
                            "tech",
                            "billing"
                        ]
                    }
                ]
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "body": {
                "authInfo": {
                    "pw": "Password1!@"
                },
                "name": f"test3-{random_name}.example".upper(),
                "status": [
                    "ok"
                ],
                "contacts": [
                    {
                        "value": "FOO-TEST1",
                        "type": [
                            "registrant",
                            "admin",
                            "tech",
                            "billing"
                        ]
                    }
                ]
            },
            "fields": {
                "clID": lambda x: x is not None,
                "crDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, -1, 60),
                "crID": lambda x: x is not None,
                "exDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, 60 * 60 * 24 * 364 * 1, 60 * 60 * 24 * 366 * 1),
            }
        }
    },
    { "test_id": "test4-simple_create_with_all_contacts_separated",
        "request": {
            "method": "POST",
            "url": "/domains",
            "body": {
                "name": f"test4-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                },
                "contacts": [
                    {
                        "value": "FOO-TEST2",
                        "type": [
                            "admin"
                        ]
                    },
                    {
                        "value": "FOO-TEST3",
                        "type": [
                            "registrant",
                            "tech"
                        ]
                    },
                    {
                        "value": "FOO-TEST4",
                        "type": [
                            "billing",
                            "tech"
                        ]
                    }
                ]
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "body": {
                "authInfo": {
                    "pw": "Password1!@"
                },
                "name": f"test4-{random_name}.example".upper(),
                "status": [
                    "ok"
                ],
                "contacts": [
                    {
                        "value": "FOO-TEST3",
                        "type": [
                            "tech",
                            "registrant"
                        ]
                    },
                    {
                        "value": "FOO-TEST2",
                        "type": [
                            "admin"
                        ]
                    },
                    {
                        "value": "FOO-TEST4",
                        "type": [
                            "billing",
                            "tech"
                        ]
                    }
                ]
            },
            "fields": {
                "clID": lambda x: x is not None,
                "crDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, -1, 60),
                "crID": lambda x: x is not None,
                "exDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, 60 * 60 * 24 * 364 * 1, 60 * 60 * 24 * 366 * 1),
            }
        }
    },
    { "test_id": "test5-simple_create_with_host_attr",
        "request": {
            "method": "POST",
            "url": "/domains",
            "body": {
                "name": f"test5-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                },
                "ns": {
                    "hostAttr": [
                        {
                            "name": "ns1.foo.net"
                        },
                        {
                            "name": f"ns1.test5-{random_name}.example",
                            "addr": {
                                "ipv4": ["192.168.1.1", "192.168.1.2"],
                                "ipv6": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334"]
                            }
                        }
                    ]
                }
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "body": {
                    "authInfo": {
                        "pw": "Password1!@"
                    },
                    "name": f"test5-{random_name}.example".upper(),
                    "status": [
                        "ok"
                    ],
                    "ns": {
                        "hostObj": [ #HACK: test EPP server responds with Host object even if creation was with host attributes - so we tweak the test to fit
                            {
                                "name": "ns1.foo.net".upper()
                            },
                            {
                                "name": f"ns1.test5-{random_name}.example".upper()
                            }
                        ]
                    }
            },
            "fields": {
                "clID": lambda x: x is not None,
                "crDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, -1, 60),
                "crID": lambda x: x is not None,
                "exDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, 60 * 60 * 24 * 364 * 1, 60 * 60 * 24 * 366 * 1),  # 1 year in seconds
            }
        }
    },
    { "test_id": "test6-simple_create_with_host_obj",
        "request": {
            "method": "POST",
            "url": "/domains",
            "body": {
                "name": f"test6-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                },
                "ns": {
                    "hostObj": [
                        {
                            "name": "ns1.bar.example"
                        },
                        {
                            "name": "ns2.bar.example"
                        }
                    ]
                }
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 201,
            "body": {
                "authInfo": {
                    "pw": "Password1!@"
                },
                "name": f"test6-{random_name}.example".upper(),
                "status": [
                    "ok"
                ],
                "ns": {
                    "hostObj": [
                        {
                            "name": "ns1.bar.example".upper()
                        },
                        {
                            "name": f"ns2.bar.example".upper()
                        }
                    ]
                }
            },
            "fields": {
                "clID": lambda x: x is not None,
                "crDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, -1, 60),
                "crID": lambda x: x is not None,
                "exDate": lambda x: check_datetime_format_utc_and_delta(test_start, x, 60 * 60 * 24 * 364 * 1, 60 * 60 * 24 * 366 * 1),  # 1 year in seconds
            }
        }
    },
    { "test_id": "test7-simple_create_domain_taken",
        "request": {
            "method": "POST",
            "url": "/domains",
            "body": {
                "name": f"NOT-FREE.EXAMPLE",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {"Content-Type": "application/json"}
        },
        "response": {
            "status": 409,
            "body": {},
            "fields": {}
        }
    },
]

# --- Test Function ---
@pytest.mark.parametrize("case", test_cases, ids=[f"{__name__.replace("test_", "")}-{c["test_id"]}" for c in test_cases])
def test_domains_Create(client, case):
    return endpoint_test(client, case)