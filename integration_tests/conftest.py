from pytest import fixture


@fixture(scope="session")
def fallback_org_config(request):
    def fallback_org_config():
        raise AssertionError("--org orgname is required for integration tests.")

    return fallback_org_config
