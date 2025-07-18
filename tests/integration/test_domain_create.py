import pytest
import connexion
import json
import uuid
from run import app
import datetime
from tests.helper.integration_api_test import endpoint_test
from tests.helper.check_datetime import check_datetime_format_utc_and_delta
import os


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
test_cases = []
[
    { "test_id": "test1-simple_create",
       "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"test1-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
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
                "clID": { "type": "not_null" },
                "crDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": -1,
                    "max_delta": 60
                },
                "crID": { "type": "not_null" },
                "exDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": 60 * 60 * 24 * 364 * 1,
                    "max_delta": 60 * 60 * 24 * 366 * 1
                }
            },
            "headers": {
                "RPP-clTRID": None,
                "RPP-svTRID": { "type": "not_empty_string" }
            },
        }}]
    },
    { "test_id": "test2-simple_create_2year",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
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
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
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
                "clID": { "type": "not_null" },
                "crDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": -1,
                    "max_delta": 60
                },
                "crID": { "type": "not_null" },
                "exDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": 60 * 60 * 24 * 364 * 2,
                    "max_delta": 60 * 60 * 24 * 366 * 2
                }
            },
            "headers": {
                "RPP-clTRID": None,
                "RPP-svTRID": { "type": "not_empty_string" }
            },
        }}]
    },
    { "test_id": "test3-simple_create_with_all_contacts",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
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
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
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
                "clID": { "type": "not_null" },
                "crDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": -1,
                    "max_delta": 60
                },
                "crID": { "type": "not_null" },
                "exDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": 60 * 60 * 24 * 364 * 1,
                    "max_delta": 60 * 60 * 24 * 366 * 1
                }
            },
            "headers": {
                "RPP-clTRID": None,
                "RPP-svTRID": { "type": "not_empty_string" }
            }
        }}]
    },
    { "test_id": "test4-simple_create_with_all_contacts_separated",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
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
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
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
                "clID": { "type": "not_null" },
                "crDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": -1,
                    "max_delta": 60
                },
                "crID": { "type": "not_null" },
                "exDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": 60 * 60 * 24 * 364 * 1,
                    "max_delta": 60 * 60 * 24 * 366 * 1
                }
            },
            "headers": {
                "RPP-clTRID": None,
                "RPP-svTRID": { "type": "not_empty_string" }
            }
        }}]
    },
    { "test_id": "test5-simple_create_with_host_attr",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
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
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
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
                "clID": { "type": "not_null" },
                "crDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": -1,
                    "max_delta": 60
                },
                "crID": { "type": "not_null" },
                "exDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": 60 * 60 * 24 * 364 * 1,
                    "max_delta": 60 * 60 * 24 * 366 * 1
                }
            },
            "headers": {
                "RPP-clTRID": None,
                "RPP-svTRID": { "type": "not_empty_string" }
            }
        }}]
    },
    { "test_id": "test6-simple_create_with_host_obj",
       "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
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
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
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
                "clID": { "type": "not_null" },
                "crDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": -1,
                    "max_delta": 60
                },
                "crID": { "type": "not_null" },
                "exDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": 60 * 60 * 24 * 364 * 1,
                    "max_delta": 60 * 60 * 24 * 366 * 1
                }
            },
            "headers": {
                "RPP-clTRID": None,
                "RPP-svTRID": { "type": "not_empty_string" }
            }
        }}]
    },
    { "test_id": "test7-simple_create_domain_taken",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"NOT-FREE.EXAMPLE",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test7-{random_name}-clTRID",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 409,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test7-{random_name}-clTRID"
            },
        }}]
    },
    { "test_id": "test8-malformed_json",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_raw": """
{
    "name: "FREE.EXAMPLE",
    "authInfo": {
        "pw": "Password1!@"
    }
}
            """,
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test8-{random_name}-clTRID",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            },
        },
        "response": {
            "status": 400,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test8-{random_name}-clTRID"
            },
        }}]
    },
    { "test_id": "test9-invalid_schema",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "domain_name": "FREE.EXAMPLE",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test9-{random_name}-clTRID",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 400,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test9-{random_name}-clTRID"
            },
        }}]
    },
    { "test_id": "test10-no_body",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test10-{random_name}-clTRID",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 400,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test10-{random_name}-clTRID"
            },
        }}]
    },
    { "test_id": "test11-invalid_content_type_no_clTRID",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"test11-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/epp+xml",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 415,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": None
            },
        }}]
    },
    { "test_id": "test12-simple_create-clTRID",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"test12-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test12-{random_name}-clTRID",
                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
            }
        },
        "response": {
            "status": 201,
            "content_type": "application/json",
            "body": {
                "authInfo": {
                    "pw": "Password1!@"
                },
                "name": f"test12-{random_name}.example".upper(),
                "status": [
                    "ok"
                ]
            },
             "fields": {
                "clID": { "type": "not_null" },
                "crDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": -1,
                    "max_delta": 60
                },
                "crID": { "type": "not_null" },
                "exDate": {
                    "type": "datetime_format_utc_and_delta",
                    "reference": test_start.isoformat(),
                    "min_delta": 60 * 60 * 24 * 364 * 1,
                    "max_delta": 60 * 60 * 24 * 366 * 1
                }
            },
            "headers": {
                "RPP-clTRID": f"test12-{random_name}-clTRID",
                "RPP-svTRID": { "type": "not_empty_string" }
            }
        }}]
    },
    { "test_id": "test13-no-Auth",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"test13-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test13-{random_name}-clTRID"
            }
        },
        "response": {
            "status": 401,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test13-{random_name}-clTRID"
            },
        }}]
    },
    { "test_id": "test14-invalid-auth",
      "steps": [{"request": {
            "method": "POST",
            "url": "/domains",
            "body_json": {
                "name": f"test14-{random_name}.example",
                "authInfo": {
                    "pw": "Password1!@"
                }
            },
            "headers": {
                "Content-Type": "application/json",
                "RPP-clTRID": f"test14-{random_name}-clTRID",
#                "Authorization": "Basic Zm9vOmJhcg==" # foo:bar
#                "Authorization": "Basic YWRtaW46YWRtaW4=" # admin:admin
                "Authorization": "Basic Zm9vOmNhdA==" # foo:cat
            }
        },
        "response": {
            "status": 401,
            "content_type": "application/problem+json",
            "body": {},
            "fields": {},
            "headers": {
                "RPP-clTRID": f"test14-{random_name}-clTRID"
            },
        }}]
    },
]

# --- Test Function ---
@pytest.mark.parametrize("case", test_cases, ids=[f"{__name__.replace("test_", "")}-{c["test_id"]}" for c in test_cases])
def test_domains_Create(client, case):
    return endpoint_test(client, case)