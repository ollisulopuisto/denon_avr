"""Performance contracts and invalidation on upstream's split architecture."""
import dataclasses
import pytest
from avr.models import AvrState, Discovery, SourceDescriptor, ChannelDescriptor, ZoneDescriptor
from avr.protocol.profile import load_profile
from avr.protocol.telnet_parser import TelnetParser
from avr.protocol.deviceinfo import parse_device_info
from avr.protocol.upnp import parse_upnp_description
from avr.protocol import commands


def test_indexes_are_runtime_only_and_reused():
    discovery = Discovery(sources=[SourceDescriptor('A', 'First')], channels=[ChannelDescriptor('FL', 'Front')])
    assert discovery.source_code('First') == 'A'
    assert discovery.channel_name('FL') == 'Front'
    source_index = discovery._source_name_by_code
    channel_index = discovery._channel_name_by_code
    assert discovery.source_name('A') == 'First'
    assert discovery.channel_name('FL') == 'Front'
    assert discovery._source_name_by_code is source_index
    assert discovery._channel_name_by_code is channel_index
    assert not any(key.startswith('_') for key in dataclasses.asdict(discovery))


def test_source_rename_visibility_append_and_replacement_do_not_go_stale():
    discovery = Discovery(sources=[SourceDescriptor('A', 'Before')])
    parser = TelnetParser(load_profile(), discovery)
    assert discovery.source_code('Before') == 'A'
    parser.feed('SSFUNA After', AvrState())
    assert discovery.source_code('Before') is None
    assert discovery.source_code('After') == 'A'
    parser.feed('SSSODA DEL', AvrState())
    assert discovery.visible_sources() == []
    parser.feed('SSFUNB Other', AvrState())
    assert discovery.source_name('B') == 'Other'
    discovery.sources = [SourceDescriptor('C', 'New'), SourceDescriptor('D', 'New')]
    assert discovery.source_code('New') == 'C'  # preserve first-match semantics
    assert discovery.source_name('A') is None
    discovery.channels = [ChannelDescriptor('FL','Before')]
    assert discovery.channel_name('FL') == 'Before'
    discovery.channels = [ChannelDescriptor('FL','After')]
    assert discovery.channel_name('FL') == 'After'


def test_profile_indexes_do_not_rescan_controls_and_return_fresh_lists():
    profile = load_profile()
    expected = profile.controls_by_scope('core')
    assert expected
    class NoTraversal(dict):
        def values(self):
            raise AssertionError('immutable controls must be indexed once')
    original = profile.controls
    try:
        profile.controls = NoTraversal(profile.controls)
        assert profile.controls_by_scope('core') == expected
        profile.controls_by_scope('core').clear()
        assert profile.controls_by_scope('core') == expected
        assert profile.feature_controls()
    finally:
        profile.controls = original


def test_telnet_buckets_preserve_sorted_order_and_cached_grammar():
    profile = load_profile()
    parser = TelnetParser(profile, Discovery())
    for key, bucket in parser._feature_buckets.items():
        assert bucket == [item for item in parser._feature_matchers if item[0][:2] == key]
    assert parser._speaker_count_re.match('2SP').group(1) == '2'
    assert parser._level_reference == profile.level_reference
    assert parser._list_terminator == profile.list_terminator


def test_resync_cached_static_queries_keep_dynamic_features_and_zones():
    profile = load_profile()
    discovery = Discovery()
    static = commands.static_resync_queries(profile)
    assert commands.resync_queries(profile, discovery, static) == commands.resync_queries(profile, discovery)
    discovery.zones.append(ZoneDescriptor('zone2',2))
    discovery.features.update(spec.feature for spec in profile.feature_controls() if spec.feature)
    expected = commands.resync_queries(profile, discovery)
    assert commands.resync_queries(profile, discovery, static) == expected
    assert 'Z2?' in expected
    assert len(expected) == len(set(expected))


def test_deviceinfo_single_pass_extracts_all_blocks_and_duplicate_sources():
    xml = '''<root><ModelName>Test</ModelName><DeviceZones>2</DeviceZones><FuncName>Tone</FuncName>
    <Tone><DispName> Tone </DispName><DispName> On </DispName></Tone>
    <QuickSelect><Control>1</Control><QuickSelect1><No>1</No><Name>News</Name></QuickSelect1></QuickSelect>
    <SubwooferLevel><SubwooferNum>2</SubwooferNum></SubwooferLevel>
    <Volume><MaxValue>98</MaxValue><StepValue>0.5</StepValue><List><Param><Relative>0dB</Relative><Absolute>80</Absolute></Param></List></Volume>
    <Source><SourcePath>x/A</SourcePath></Source><Source><SourcePath>x/A</SourcePath></Source></root>'''
    result = parse_device_info(xml, {'Tone'}, {'Tone'})
    assert result.feature_names == {'Tone':'Tone'}
    assert result.option_labels == {'Tone':['On']}
    assert result.quick_select_names == {1:'News'}
    assert result.subwoofer_max == 2
    assert result.volume == {'absolute_max':98,'step':0.5,'reference':80}
    assert [source.code for source in result.sources] == ['A']

@pytest.mark.parametrize('namespace',['',' xmlns="urn:test"'])
def test_upnp_first_nonempty_values_and_trailing_duplicates(namespace):
    result = parse_upnp_description(f'<root{namespace}><manufacturer> </manufacturer><manufacturer>Denon</manufacturer><serialNumber>S</serialNumber><firmware_version>F</firmware_version><modelNumber>M</modelNumber><firmwareRevision>R</firmwareRevision><manufacturer>Wrong</manufacturer></root>')
    assert result == {'manufacturer':'Denon','serial_number':'S','firmware_version':'F','network_module_version':'M','firmware_revision':'R'}


def test_upnp_stops_after_all_five_nonempty_fields(monkeypatch):
    from avr.protocol import upnp
    import xml.etree.ElementTree as ET
    original = ET.fromstring
    visits = []
    class Tree:
        def iter(self):
            for node in original('<root><manufacturer>D</manufacturer><serialNumber>S</serialNumber><firmware_version>F</firmware_version><modelNumber>M</modelNumber><firmwareRevision>R</firmwareRevision><trailing>unused</trailing></root>').iter():
                visits.append(node.tag)
                yield node
    monkeypatch.setattr(upnp.ET, 'fromstring', lambda _: Tree())
    assert len(upnp.parse_upnp_description('ignored')) == 5
    assert 'trailing' not in visits


def test_deviceinfo_uses_one_full_tree_scan(monkeypatch):
    from avr.protocol import deviceinfo
    import xml.etree.ElementTree as ET
    original = ET.fromstring
    scans = []
    class Tree:
        def __init__(self):
            self.root = original('<root><FuncName>Tone</FuncName><Source><SourcePath>x/A</SourcePath></Source></root>')
        def findtext(self, path):
            assert not path.startswith('.//'), 'no repeated deep root queries'
            return self.root.findtext(path)
        def iter(self, *args):
            scans.append(args)
            return self.root.iter(*args)
    monkeypatch.setattr(deviceinfo.ET, 'fromstring', lambda _: Tree())
    assert deviceinfo.parse_device_info('ignored').features == {'Tone'}
    assert scans == [()]
