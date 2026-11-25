"""Fork behavior carried from v1.1.3 onto upstream's split architecture."""
import pytest
import conftest
from avr.protocol import commands
from avr.protocol.profile import load_profile

@pytest.mark.parametrize(('name','wire'), [('Dolby Audio - Dolby Surround','DOLBY DIGITAL'),('DTS Neural:X','DTS SURROUND'),('Multi In + DSur','M CH IN+DSUR'),('Stereo','STEREO')])
def test_home_sound_tokens(name, wire):
    assert commands.sound_mode_wire(load_profile(), name) == wire

def test_home_surround_none():
    helpers = conftest.load_ha_module('helpers')
    profile = load_profile()
    assert helpers.speaker_size_options(profile, 'SUA') == {'LAR':'Large','SMA':'Small','NON':'None'}
    assert helpers.speaker_size_options(profile, 'FRO') == {'LAR':'Large','SMA':'Small'}

async def test_home_volume_scale_and_limit(make_device):
    dev, _, telnet, _ = make_device('avr_x3600h')
    await dev.async_discover()
    await dev.async_start()
    dev.state.zone('main').volume_max_raw = 60
    assert dev.volume_raw_to_level(36) == 0.36
    assert dev._control.level_to_raw('main', 0.36) == 36
    assert dev._control.level_to_raw('main', 0.365) == 36.5
    telnet.sent.clear()
    await dev.async_set_volume_level('main', 0.36)
    await dev.async_set_volume_level('main', 0.9)
    assert telnet.sent == ['MV36','MV60']
    await dev.async_stop()


def test_entity_mismatch_warning_does_not_log_identifiers():
    import ast
    from pathlib import Path
    tree = ast.parse((Path(__file__).parents[1] / 'custom_components/denon_avr/entity.py').read_text())
    warnings = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'warning']
    assert warnings
    for node in warnings:
        assert len(node.args) == 1, 'warning must not include unique IDs or expected MAC/serial-derived IDs'
