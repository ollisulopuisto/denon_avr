import sys,timeit,statistics,json
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'tests'));import conftest
from avr.protocol.profile import load_profile
from avr.protocol.deviceinfo import parse_device_info
from avr.protocol.telnet_parser import TelnetParser
from avr.protocol.upnp import parse_upnp_description
from avr.protocol import commands
from avr.models import Discovery,AvrState,SourceDescriptor,ChannelDescriptor
p=load_profile();xml=(root/'tests/fixtures/avr_x3600h/goform_Deviceinfo.xml').read_text();upnp=(root/'tests/fixtures/avr_x3600h/upnp_aios_device.xml').read_text();d=parse_device_info(xml,set(spec.feature for spec in p.feature_controls() if spec.feature));parser=TelnetParser(p,d);state=AvrState();lines=json.loads((root/'tests/fixtures/avr_x3600h/telnet_corpus.json').read_text());print('corpus',type(lines).__name__,len(lines))
if isinstance(lines,dict):lines=next(v for v in lines.values() if isinstance(v,list))
if lines and isinstance(lines[0],dict):lines=[row.get('line',row.get('text','')) for row in lines]
static=commands.static_resync_queries(p) if hasattr(commands,'static_resync_queries') else None
cases={'deviceinfo':(lambda:parse_device_info(xml,set(spec.feature for spec in p.feature_controls() if spec.feature)),300),'upnp':(lambda:parse_upnp_description(upnp),1000),'profile_index':(lambda:p.controls_by_scope('core'),10000),'resync':(lambda:commands.resync_queries(p,d,static) if static else commands.resync_queries(p,d),3000),'telnet_replay':(lambda:[parser.feed(line,state) for line in lines],100),'source_lookup':(lambda:d.source_name(d.sources[-1].code),10000)}
for name,(fn,n) in cases.items():
 fn();t=statistics.median(timeit.repeat(fn,number=n,repeat=7))/n*1e6;print(name,round(t,3))
