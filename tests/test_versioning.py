from sap_role_updater.version import APP_VERSION, bump_version, parse_version


def test_app_version_is_valid_semver():
    major, minor, patch = parse_version(APP_VERSION)
    assert all(isinstance(part, int) for part in (major, minor, patch))


def test_bump_version_resets_lower_parts():
    assert bump_version("1.3.9", "patch") == "1.3.10"
    assert bump_version("1.3.9", "minor") == "1.4.0"
    assert bump_version("1.3.9", "major") == "2.0.0"
