"""Tests for parser helpers in custom_components/denon_avr/avr/parser.py."""

from __future__ import annotations

from avr.models import AvrState, Discovery
from avr.parser import TelnetParser, parse_device_info, parse_upnp_description
from avr.profile import load_profile


def test_parse_upnp_description_complete() -> None:
    xml_data = """<?xml version="1.0"?>
    <root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:dm="urn:schemas-denon-com:device-1-0">
      <device>
        <deviceType>urn:schemas-upnp-org:device:MediaRenderer:1</deviceType>
        <friendlyName>Denon AVR-X3600H</friendlyName>
        <manufacturer>Denon</manufacturer>
        <modelNumber>A100</modelNumber>
        <serialNumber>123456789012</serialNumber>
        <dm:firmware_version>3.1.0</dm:firmware_version>
        <dm:firmwareRevision>1234-5678</dm:firmwareRevision>
        <serviceList>
          <service><serviceType>test</serviceType></service>
          <service><serviceType>test2</serviceType></service>
        </serviceList>
      </device>
    </root>
    """
    res = parse_upnp_description(xml_data)
    assert res == {
        "manufacturer": "Denon",
        "network_module_version": "A100",
        "serial_number": "123456789012",
        "firmware_version": "3.1.0",
        "firmware_revision": "1234-5678",
    }


def test_parse_upnp_description_partial() -> None:
    xml_data = """<root>
      <manufacturer>Denon</manufacturer>
      <serialNumber>123456789012</serialNumber>
    </root>"""
    res = parse_upnp_description(xml_data)
    assert res == {
        "manufacturer": "Denon",
        "serial_number": "123456789012",
    }


def test_parse_upnp_description_empty_and_invalid() -> None:
    assert parse_upnp_description("<invalid xml") == {}
    assert parse_upnp_description("<root></root>") == {}
    assert parse_upnp_description("") == {}


def test_parse_upnp_description_empty_text_ignored() -> None:
    xml_data = """<root>
      <manufacturer>   </manufacturer>
      <serialNumber>123456789012</serialNumber>
    </root>"""
    res = parse_upnp_description(xml_data)
    assert res == {
        "serial_number": "123456789012",
    }


def test_telnet_parser_speaker_config_and_recompute_channels() -> None:
    profile = load_profile()
    discovery = Discovery()
    state = AvrState()
    parser = TelnetParser(profile, discovery)

    # Initially no configured channels
    assert discovery.configured_channels == set()

    # Feed speaker config for Front speakers (LAR) - group code is FRO
    assert parser.feed("SSSPCFRO LAR", state)
    assert "FL" in discovery.configured_channels
    assert "FR" in discovery.configured_channels
    assert state.speaker_sizes["FRO"] == "LAR"

    # Subwoofer double (2SP) - count group SWF
    assert parser.feed("SSSPCSWF 2SP", state)
    assert "SW" in discovery.configured_channels
    assert "SW2" in discovery.configured_channels

    # Surround Back single (1SP) - count group SBK
    assert parser.feed("SSSPCSBK 1SP", state)
    assert "SB" in discovery.configured_channels
    assert "SBL" not in discovery.configured_channels

    # Center speaker (CEN)
    assert parser.feed("SSSPCCEN SMA", state)
    assert "C" in discovery.configured_channels

    # Non-configured / absent speaker
    assert parser.feed("SSSPCFRH NON", state)
    assert "FHL" not in discovery.configured_channels
    assert "FHR" not in discovery.configured_channels


def test_telnet_parser_dispatch_core_commands() -> None:
    profile = load_profile()
    discovery = Discovery()
    state = AvrState()
    parser = TelnetParser(profile, discovery)

    assert parser.feed("PWON", state)
    assert state.system_power is True

    assert parser.feed("ZMON", state)
    assert state.zone("main").power is True
    assert state.values["main_power"] is True

    assert parser.feed("MV50", state)
    assert state.zone("main").volume_raw == 50.0

    assert parser.feed("MVMAX 80", state)
    assert state.zone("main").volume_max_raw == 80.0

    assert parser.feed("MUON", state)
    assert state.zone("main").muted is True

    assert parser.feed("MSQUICK1", state)
    assert state.values["quick_select"] == 1

    assert parser.feed("MSSTEREO", state)
    assert state.values["sound_mode"] == "STEREO"

    assert parser.feed("SICBL/SAT", state)
    assert state.zone("main").source == "CBL/SAT"

    assert parser.feed("SVGAME", state)
    assert state.values["video_select"] == "GAME"

    assert parser.feed("CVFL 50", state)
    assert state.channel_trims["FL"] == 0.0

    assert parser.feed("SSLEVFL 50", state)
    assert state.channel_levels["FL"] == 0.0

    assert parser.feed("SSSDEFL 0310", state)
    assert state.channel_distances["FL"] == 3.10

    assert parser.feed("SSCFR IDV", state)
    assert state.values["crossover_speaker_selection"] == "IDV"

    assert parser.feed("SSCFRFL 080", state)
    assert state.crossovers["FL"] == 80

    assert parser.feed("SSFUN1 CBL/SAT", state)
    assert discovery.sources[0].name == "CBL/SAT"

    assert parser.feed("SSSOD1 USE", state)
    assert discovery.sources[0].visible is True

    assert parser.feed("SSSMG MOV", state)
    assert state.values["sound_mode_genre"] == "MOV"

    assert parser.feed("SSQSNZMA1 Quick 1", state)
    assert discovery.quick_select_names[1] == "Quick 1"

    assert parser.feed("Z2ON", state)
    assert state.zone("zone2").power is True

    assert parser.feed("OPSMLALL MOV071Virtual", state)
    assert parser.feed("OPSMLALL END", state)
    assert "Virtual" in discovery.all_sound_modes

    assert parser.feed("OPSML 011Direct", state)
    assert state.values["sound_mode_display"] == "Direct"
    assert parser.feed("OPSML END", state)
    assert "Direct" in discovery.current_sound_modes

    assert parser.feed("PSDYNEQ ON", state)
    assert state.values["dynamic_eq"] is True


def test_parse_device_info_complete() -> None:
    xml_data = """<?xml version="1.0" encoding="utf-8"?>
    <Device_Info>
      <ModelName>AVR-X3600H*</ModelName>
      <MacAddress>0005CDBDFD0C</MacAddress>
      <DeviceZones>2</DeviceZones>
      <CommApiVers>0001</CommApiVers>
      <FunctionList>
        <FuncName>Audyssey</FuncName>
        <FuncName>ToneControl</FuncName>
        <FuncName>GraphicEQ</FuncName>
      </FunctionList>
      <ChannelLevel>
        <Ch>
          <Name>FL</Name>
          <DispName>Front Left</DispName>
          <MinRange>0</MinRange>
          <MaxRange>48</MaxRange>
          <DefaultValue>24</DefaultValue>
          <Step>0.5</Step>
        </Ch>
        <Ch>
          <Name>RESET</Name>
          <DispName>Reset</DispName>
          <MinRange>0</MinRange>
          <MaxRange>0</MaxRange>
          <DefaultValue>0</DefaultValue>
          <Step>0</Step>
        </Ch>
      </ChannelLevel>
      <ToneControlSet_AVR>
        <BassMin>0</BassMin>
        <BassMax>12</BassMax>
        <BassDefault>6</BassDefault>
        <BassStep>1</BassStep>
        <TrebleMin>0</TrebleMin>
        <TrebleMax>12</TrebleMax>
        <TrebleDefault>6</TrebleDefault>
        <TrebleStep>1</TrebleStep>
      </ToneControlSet_AVR>
      <SoundMode>
        <Genre>
          <List>
            <Value><DispName>MOVIE</DispName></Value>
            <Value><DispName>MUSIC</DispName></Value>
          </List>
        </Genre>
      </SoundMode>
      <Volume>
        <MaxValue>98.0</MaxValue>
        <StepValue>0.5</StepValue>
        <Param>
          <Absolute>80.0</Absolute>
          <Relative>0.0dB</Relative>
        </Param>
      </Volume>
      <InputSource>
        <Source>
          <SourcePath>/Device/Source/CBL_SAT</SourcePath>
        </Source>
        <Source>
          <SourcePath>/Device/Source/SOURCE</SourcePath>
        </Source>
        <Source>
          <SourcePath>/Device/Source/CBL_SAT</SourcePath>
        </Source>
      </InputSource>
      <CustomFeature>
        <DispName>Custom Feature</DispName>
        <DispName>Opt1</DispName>
        <DispName>Opt2</DispName>
        <MinRange>0</MinRange>
        <MaxRange>10</MaxRange>
        <DefaultValue>5</DefaultValue>
        <Step>1</Step>
      </CustomFeature>
    </Device_Info>
    """
    receiver_type = {
        "avr_x_pattern": r"AVR-X",
        "commapi_pattern": r"^0001$",
        "avr_x_type": "avr-x-2016",
        "default_type": "avr",
    }
    discovery = parse_device_info(
        xml_data,
        feature_names={"CustomFeature"},
        enum_features={"CustomFeature"},
        receiver_type=receiver_type,
    )

    # Device properties
    assert discovery.device.model_name == "AVR-X3600H"
    assert discovery.device.mac_address == "00:05:cd:bd:fd:0c"
    assert discovery.device.zone_count == 2
    assert discovery.device.hardware_type == "avr-x-2016"
    assert len(discovery.zones) == 2

    # Features
    assert discovery.features == {"Audyssey", "ToneControl", "GraphicEQ"}

    # Channels
    assert len(discovery.channels) == 1
    assert discovery.channels[0].code == "FL"
    assert discovery.channels[0].name == "Front Left"
    assert discovery.numeric_meta["FL"] == {"min": -12.0, "max": 12.0, "step": 0.5}

    # Tone Control
    assert discovery.numeric_meta["Bass"] == {"min": -6.0, "max": 6.0, "step": 1.0}
    assert discovery.numeric_meta["Treble"] == {"min": -6.0, "max": 6.0, "step": 1.0}

    # Custom Feature block
    assert discovery.feature_names["CustomFeature"] == "Custom Feature"
    assert discovery.option_labels["CustomFeature"] == ["Opt1", "Opt2"]
    assert discovery.numeric_meta["CustomFeature"] == {"min": -5.0, "max": 5.0, "step": 1.0}

    # Sound Mode genres
    assert discovery.sound_mode_genres == {"MOV": "Movie", "MUS": "Music"}

    # Volume
    assert discovery.volume == {"absolute_max": 98.0, "step": 0.5, "reference": 80.0}

    # Fallback Sources (ignores 'SOURCE' and duplicates)
    assert len(discovery.sources) == 1
    assert discovery.sources[0].code == "CBL_SAT"
    assert discovery.sources[0].name == "CBL_SAT"
