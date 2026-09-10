import ast
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlencode
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request
from app.database import Base
from app.models.stock import Stock
from app.models.inventory import Inventory
from app.models.production_plan import ProductionPlan
from app.models.bom import BOM
from app.models.stock_movement import StockMovement
from app.models.inventory_movement import InventoryMovement
from app.workflow.models.workflow_notification import WorkflowNotification
from app.routers import stock, inventory, mrp, admin, upload
from app.models.activity_log import ActivityLog
from app.models.access_log import AccessLog
from app.models.inbound import Inbound
from app.models.outbound import Outbound
from app.workflow.models.workflow_history import WorkflowHistory
from app.workflow.services.history_service import get_histories
from app.workflow.services.notification_service import get_notifications, count_unread, mark_all_read
from app.utils.filters import filter_values, filter_ints


def request(path, params=()):
    return Request({'type':'http', 'method':'GET', 'path':path, 'root_path':'',
        'scheme':'http', 'server':('testserver',80), 'headers':[],
        'query_string':urlencode(params).encode(), 'session':{'role':'admin','user':'test'},
        'state':{'is_admin':True}})


class MultiFilterTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        for index, (grade, rev, lot) in enumerate([('A','R1','LOT,1'),('B','R1','LOT&2'),('F','R1','LOT3'),('A','R2','LOT4')]):
            self.db.add(Stock(item_code=str(index),item_name='test',category='반제품',grade=grade,rev=rev,qty=10))
            self.db.add(Inventory(item_code=str(index),item_name='test',warehouse_type='창고재고',category='반제품',grade=grade,rev=rev,lot=lot,note='한글 & 비고',qty=10))
        for year, month in [(2025,1),(2026,1),(2026,2),(2026,3)]:
            self.db.add(ProductionPlan(plan_date=date(year,month,5),product_name='P',plan_qty=10))
        self.db.add(BOM(product_name='P',component_code='C',component_name='Component',qty=2))
        for team, read in [('purchase',False),('quality',True),('material',False)]:
            self.db.add(WorkflowNotification(department=team,is_read=read,title=team))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_special_values_and_deduplication(self):
        req = request('/inventory', [('lot','LOT,1'),('lot','LOT&2'),('lot','LOT,1'),('lot','')])
        self.assertEqual(filter_values(req,'lot'), ['LOT,1','LOT&2'])
        with self.assertRaises(Exception):
            filter_ints(request('/mrp',[('year','bad')]),'year')

    def test_stock_or_within_and_between_filters(self):
        req=request('/stock',[('grade','A'),('grade','B'),('rev','R1')])
        response=stock.inventory_dashboard(req,db=self.db)
        self.assertEqual({r.grade for r in response.context['items']},{'A','B'})
        self.assertEqual(len(response.context['items']),2)
        self.assertEqual(len(stock.inventory_dashboard(request('/stock'),db=self.db).context['items']),4)

    def test_inventory_four_combined_filters_and_empty_result(self):
        params=[('grade','A'),('grade','B'),('rev','R1'),('lot','LOT,1'),('lot','LOT&2'),('note','한글 & 비고')]
        response=inventory.inventory_page(request('/inventory',params),db=self.db)
        self.assertEqual(len(response.context['items']),2)
        response=inventory.inventory_page(request('/inventory',params+[('rev','missing')]),db=self.db)
        self.assertEqual(len(response.context['items']),2)
        response=inventory.inventory_page(request('/inventory',[('grade','B'),('rev','R2')]),db=self.db)
        self.assertEqual(len(response.context['items']),0)
        self.assertEqual(response.context['total_pages'],1)

    def test_mrp_multiple_year_month_week(self):
        req=request('/mrp/result',[('year','2025'),('year','2026'),('month','1'),('month','2'),('week','2')])
        response=mrp.mrp_result(req,db=self.db)
        self.assertEqual(len(response.context['plans']),2)
        self.assertEqual(response.context['rows'][0]['required_qty'],40)
        self.assertEqual(response.context['projection_start'],date(2025,1,1))
        dashboard=mrp.mrp_dashboard(request('/mrp',[('year','2025'),('year','2026'),('month','1'),('month','2')]),db=self.db)
        self.assertEqual(dashboard.status_code,200)
        self.assertIn(2,dashboard.context['months'])

    def test_notification_or_states_and_bulk_read_scope(self):
        rows=get_notifications(self.db,department=['purchase','quality'],read_states=['0','1'])
        self.assertEqual(len(rows),2)
        self.assertEqual(count_unread(self.db,['purchase','quality']),1)
        mark_all_read(self.db,['purchase','quality'])
        self.assertEqual(count_unread(self.db,['material']),1)
        self.assertEqual(count_unread(self.db,['purchase','quality']),0)

    def test_history_category_union(self):
        for model in (StockMovement, InventoryMovement):
            for category in ['반제품','제품','원자재']:
                self.db.add(model(item_code=category,category=category,movement_type='IN',qty=1))
        self.db.commit()
        params=[('category','반제품'),('category','제품')]
        for path, handler in [('/stock/history',stock.stock_history),('/inventory/history',inventory.inventory_history)]:
            response=handler(request(path,params),db=self.db)
            self.assertEqual({r.category for r in response.context['history']},{'반제품','제품'})

    def test_admin_filters(self):
        for action in ['LOGIN','LOGOUT','UPLOAD_EXCEL']:
            self.db.add(ActivityLog(user='test',action=action))
        for result in ['성공','실패','거부']:
            self.db.add(AccessLog(user='test',result=result,method='GET',path='/test',action='VIEW',status_code=200))
        self.db.commit()
        with patch.object(admin,'SessionLocal',return_value=self.db):
            response=admin.admin_activity(request('/admin/activity',[('action','LOGIN'),('action','LOGOUT')]))
            self.assertEqual({r.action for r in response.context['logs']},{'LOGIN','LOGOUT'})
            response=admin.admin_access_log(request('/admin/access',[('result','성공'),('result','실패')]))
            self.assertEqual({r.result for r in response.context['logs']},{'성공','실패'})

    def test_search_scope_union_and_workflow_history(self):
        self.db.add(Inbound(serial='test',product='P'))
        self.db.add(Outbound(serial='test',product='P'))
        for department in ['purchase','quality','material']:
            self.db.add(WorkflowHistory(department=department,workflow_no='W'))
        self.db.commit()
        self.assertEqual(len(get_histories(self.db,department=['purchase','quality'])),2)
        with patch.object(upload,'SessionLocal',return_value=self.db):
            response=upload.global_search(request('/search',[('status','inbound'),('status','stock')]),q='test')
            self.assertEqual(len(response.context['inbound']),1)
            self.assertEqual(len(response.context['outbound']),0)
            self.assertEqual({r['domain'] for r in response.context['global_results']},{'가계상 재고'})

    def test_templates_and_python_parse(self):
        for path in Path('app').rglob('*.py'):
            ast.parse(path.read_text(encoding='utf-8-sig'))
        for path in Path('app/templates').rglob('*.html'):
            stock.templates.env.get_template(path.relative_to('app/templates').as_posix())


if __name__ == '__main__':
    unittest.main()
