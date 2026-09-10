import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_multi_filters import MultiFilterTests, request
from app.routers import stock, inventory, mrp
Path('work/multi-filter').mkdir(parents=True,exist_ok=True)
case=MultiFilterTests()
case.setUp()
try:
    login=stock.templates.env.get_template('login.html').render(error=None)
    Path('work/multi-filter/login.html').write_text(login,encoding='utf-8')
    for path, handler, params in [('/stock',stock.inventory_dashboard,[('grade','A'),('grade','B'),('rev','R1')]),('/inventory',inventory.inventory_page,[]),('/mrp/result',mrp.mrp_result,[('year','2025'),('year','2026'),('month','1'),('month','2')])]:
        response=handler(request(path,params),db=case.db)
        Path('work/multi-filter/'+path.strip('/').replace('/','-')+'.html').write_bytes(response.body)
finally:
    case.tearDown()
