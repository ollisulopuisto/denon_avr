"""Parser for the goform Deviceinfo document."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

from ..models import (
    ChannelDescriptor,
    Discovery,
    SourceDescriptor,
    ZoneDescriptor,
)

_LOGGER = logging.getLogger(__name__)

_VERSION_TAGS = ("DeviceInfoVers", "CommApiVers", "Gen", "BrandCode")


def _format_mac(raw: str | None) -> str | None:
    """Format a bare MAC such as '0005CD000001' as '00:05:cd:00:00:01'."""

    if not raw:
        return None
    raw = re.sub(r"[:\-.\s]", "", raw)
    if not re.fullmatch(r"[0-9A-Fa-f]{12}", raw) or int(raw, 16) == 0:
        return None
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2)).lower()


def parse_device_info(
    xml_text: str,
    feature_names: set[str] | None = None,
    enum_features: set[str] | None = None,
    interface_type: str | None = None,
) -> Discovery:
    """Parse the Deviceinfo XML into a Discovery object."""

    discovery = Discovery()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as err:
        _LOGGER.warning("Could not parse Deviceinfo XML: %s", err)
        return discovery

    device = discovery.device
    # Some models report a region-variant marker '*' in the name; strip it, as the official
    # integration does, so the model reads cleanly.
    device.model_name = (root.findtext("ModelName") or "").strip().replace("*", "") or None
    device.mac_address = _format_mac(root.findtext("MacAddress"))
    for tag in _VERSION_TAGS:
        text = (root.findtext(tag) or "").strip()
        if text:
            device.versions[tag] = text
    device.hardware_type = interface_type
    zones_text = root.findtext("DeviceZones")
    if zones_text and zones_text.strip().isdigit():
        device.zone_count = max(1, int(zones_text.strip()))

    # Build the zone list from the discovered count.
    discovery.zones.append(
        ZoneDescriptor(id="main", index=1, name=None, is_main=True)
    )
    for index in range(2, device.zone_count + 1):
        discovery.zones.append(
            ZoneDescriptor(id=f"zone{index}", index=index, name=f"Zone {index}")
        )

    # Performance optimization: Consolidate XML tree traversals into a single pass.
    # Deviceinfo.xml contains 2,000+ elements. Previously, 4 separate traversals
    # were performed: root.iter("FuncName"), root.iter("Ch"), root.iter() for
    # indexed blocks, and root.iter("Source"). One index serves all consumers.
    target_blocks = set(feature_names or ()) | {"ToneControlSet_AVR", "SoundMode", "Volume", "QuickSelect", "SubwooferLevel"}
    indexed_blocks: dict[str, ET.Element] = {}
    seen_sources: set[str] = {s.code for s in discovery.sources}

    for node in root.iter():
        tag = node.tag
        if tag == "FuncName":
            if node.text:
                text = node.text.strip()
                if text:
                    discovery.features.add(text)
        elif tag == "Ch":
            code = (node.findtext("Name") or "").strip()
            name = (node.findtext("DispName") or "").strip()
            if not code:
                continue
            # The receiver includes a synthetic "Reset" entry with a zero range;
            # skip anything that is not a real, adjustable channel.
            min_range = node.findtext("MinRange")
            max_range = node.findtext("MaxRange")
            if name.lower() == "reset" or min_range == max_range:
                continue
            discovery.channels.append(ChannelDescriptor(code=code, name=name or code))
            meta = _range_from_block(node)
            if meta:
                discovery.numeric_meta[code] = meta
        elif tag == "Source":
            # Fallback source list from the InputSource tree (used only when the telnet
            # SSFUN/SSSOD introspection is unavailable). The path leaf is the name.
            path = node.findtext("SourcePath") or ""
            leaf = path.rsplit("/", 1)[-1].strip()
            if leaf and leaf.upper() != "SOURCE" and leaf not in seen_sources:
                seen_sources.add(leaf)
                discovery.sources.append(SourceDescriptor(code=leaf, name=leaf))
        elif tag in target_blocks and tag not in indexed_blocks:
            indexed_blocks[tag] = node

    # Tone control dB ranges, read from the receiver's tone control block.
    tone = indexed_blocks.get("ToneControlSet_AVR")
    if tone is not None:
        for feature in ("Bass", "Treble"):
            meta = _range_from_tone(tone, feature)
            if meta:
                discovery.numeric_meta[feature] = meta

    # Titles, option labels and numeric ranges for feature controls.
    enum_features = enum_features or set()
    for feature in feature_names or ():
        block = indexed_blocks.get(feature)
        if block is None:
            continue
        labels = []
        for node in block.iter("DispName"):
            text = (node.text or "").strip()
            if text:
                labels.append(text)
        if labels:
            discovery.feature_names[feature] = labels[0]
            if feature in enum_features and len(labels) >= 2:
                discovery.option_labels[feature] = labels[1:]
        meta = _range_from_block(block)
        if meta:
            discovery.numeric_meta[feature] = meta

    # Quick select presets (capability and default names), when controllable.
    quick = indexed_blocks.get("QuickSelect")
    if quick is not None and (quick.findtext("Control") or "").strip() == "1":
        for child in quick:
            number = (child.findtext("No") or "").strip()
            name = (child.findtext("Name") or "").strip()
            if child.tag.startswith("QuickSelect") and number.isdigit() and name:
                discovery.quick_select_names[int(number)] = name

    # Number of subwoofers the receiver supports (capability, not user setup).
    sub_block = indexed_blocks.get("SubwooferLevel")
    sub_count = sub_block.findtext("SubwooferNum") if sub_block is not None else None
    if sub_count and sub_count.strip().isdigit():
        discovery.subwoofer_max = int(sub_count.strip())

    # Sound mode genre names (Movie/Music/Game/Pure), read from the receiver's SoundMode genre
    # list.
    sound_block = indexed_blocks.get("SoundMode")
    genre_list = sound_block.find("Genre/List") if sound_block is not None else None
    if genre_list is not None:
        for value in genre_list.findall("Value"):
            disp = (value.findtext("DispName") or "").strip()
            if disp:
                discovery.sound_mode_genres[disp[:3].upper()] = disp.title()

    # Master volume scale, read from the receiver's Volume block: the absolute maximum, the step,
    # and the reference (the absolute value shown as 0.0 dB).
    volume = indexed_blocks.get("Volume")
    if volume is not None:
        scale: dict[str, float] = {}
        max_value = _num(volume, "MaxValue")
        step_value = _num(volume, "StepValue")
        if max_value is not None:
            scale["absolute_max"] = max_value
        if step_value is not None:
            scale["step"] = step_value
        # The reference is the Absolute value whose Relative label is "0.0dB".
        for param in volume.iter("Param"):
            relative = (param.findtext("Relative") or "").strip().lower()
            if relative in ("0.0db", "0db"):
                reference = _num(param, "Absolute")
                if reference is not None:
                    scale["reference"] = reference
                break
        if scale:
            discovery.volume = scale

    return discovery


def _num(element: ET.Element, tag: str) -> float | None:
    """Read a numeric child value, or None when absent or not numeric."""

    text = element.findtext(tag)
    try:
        return float(text) if text is not None and text.strip() != "" else None
    except ValueError:
        return None


def _to_db_range(low: float, high: float, default: float, step: float) -> dict[str, float]:
    """Convert a raw min/max/default/step to a dB range around the default."""

    return {
        "min": (low - default) * step,
        "max": (high - default) * step,
        "step": step,
    }


def _range_from_block(block: ET.Element) -> dict[str, float] | None:
    """Derive a dB range from a control block that publishes MinRange etc."""

    low = _num(block, "MinRange")
    high = _num(block, "MaxRange")
    default = _num(block, "DefaultValue")
    step = _num(block, "Step")
    if None in (low, high, default, step):
        return None
    return _to_db_range(low, high, default, step)


def _range_from_tone(tone: ET.Element, prefix: str) -> dict[str, float] | None:
    """Derive a dB range from the tone control block for bass or treble."""

    low = _num(tone, f"{prefix}Min")
    high = _num(tone, f"{prefix}Max")
    default = _num(tone, f"{prefix}Default")
    step = _num(tone, f"{prefix}Step")
    if None in (low, high, default, step):
        return None
    return _to_db_range(low, high, default, step)
