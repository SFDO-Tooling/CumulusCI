from pytest import fixture


@fixture(scope="session")
def fallback_orgconfig(request):
    def fallback_orgconfig():
        raise AssertionError("--org orgname is required for integration tests.")

    return fallback_orgconfig
