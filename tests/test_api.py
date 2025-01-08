from datetime import datetime


def test_get_sundata_real_api(mocker):

    # Apply the mock_run behavior to the mock
    mock_subprocess_run = mocker.patch("kshift.utils.subprocess.run")
    mock_subprocess_run.return_value.stdout = "You have the following color schemes on your system:\n * BreezeClassic\n * BreezeDark (current color scheme)\n * BreezeLight"

    from kshift.conf import Config, defaults

    config = Config()

    default_sunrise = datetime.strptime(defaults["sunrise"], "%H:%M")
    default_sunset = datetime.strptime(defaults["sunset"], "%H:%M")

    # Test fetching sunrise data from the real API
    sunrise = config.get_sundata("sunrise")
    sunset = config.get_sundata("sunset")

    # Assert that the returned sunrise and sunset times are valid datetime objects
    assert sunrise.hour >= 0 and sunrise.hour <= 23
    assert sunset.hour >= 0 and sunset.hour <= 23
    assert sunrise < sunset  # Sunrise must occur before sunset

    assert sunrise.time != default_sunrise.time
    assert sunset.time != default_sunset.time
