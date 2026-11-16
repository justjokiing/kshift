from datetime import datetime

import pytest


class _FakeResponse:

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def _mock_desktop(mocker):
    from kshift.theme import Colorscheme

    mocker.patch.object(Colorscheme, 'available',
                        ["BreezeClassic", "BreezeDark", "BreezeLight"])
    mocker.patch.object(Colorscheme, 'current', "BreezeDark")


def test_get_sundata_parses_api_response(mocker, tmp_path):
    _mock_desktop(mocker)
    mocker.patch("requests.get",
                 return_value=_FakeResponse({
                     "results": {
                         "sunrise": "6:42:04 AM",
                         "sunset": "4:26:04 PM"
                     }
                 }))

    from kshift.conf import Config

    config = Config(xdg_cache=tmp_path)

    sunrise = config.get_sundata("sunrise")
    sunset = config.get_sundata("sunset")

    assert (sunrise.hour, sunrise.minute, sunrise.second) == (6, 42, 4)
    assert (sunset.hour, sunset.minute, sunset.second) == (16, 26, 4)
    assert sunrise < sunset
    assert config.api_file.exists()


def test_get_sundata_falls_back_to_defaults(mocker, tmp_path):
    _mock_desktop(mocker)
    mocker.patch("requests.get", side_effect=ConnectionError("offline"))

    from kshift.conf import Config, defaults

    config = Config(xdg_cache=tmp_path)

    assert config.get_sundata("sunrise").strftime(
        "%H:%M") == defaults["sunrise"]
    assert config.get_sundata("sunset").strftime("%H:%M") == defaults["sunset"]


@pytest.mark.network
def test_get_sundata_real_api(mocker):
    _mock_desktop(mocker)

    from kshift.conf import Config, defaults

    config = Config()

    default_sunrise = datetime.strptime(defaults["sunrise"], "%H:%M")
    default_sunset = datetime.strptime(defaults["sunset"], "%H:%M")

    sunrise = config.get_sundata("sunrise")
    sunset = config.get_sundata("sunset")

    assert sunrise.hour >= 0 and sunrise.hour <= 23
    assert sunset.hour >= 0 and sunset.hour <= 23
    assert sunrise < sunset
    assert sunrise.time != default_sunrise.time
    assert sunset.time != default_sunset.time
