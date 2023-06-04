"""
Bodet Integration
https://github.com/lamauny/hassio-components/bodet
"""

import logging
from bodet import Bodet

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

DOMAIN = "bodet"

DATA_BODET_CLIENT = "bodet_cli"

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [SENSOR_DOMAIN, BINARY_SENSOR_DOMAIN, BUTTON_DOMAIN]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Bodet from a config entry."""

    # initial connection
    try:
        hBodet = await Bodet(data[CONF_LOGIN], data[CONF_PASSWORD])
    except Exception as exception:
        raise ConfigEntryNotReady from exception
    else:
        await async_update_devices()  # get initial list of JDownloaders
        hass.data.setdefault(DOMAIN, {})[entry.entry_id][
            DATA_BODET_CLIENT
        ] = hBodet

    # setup platforms
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    return True
