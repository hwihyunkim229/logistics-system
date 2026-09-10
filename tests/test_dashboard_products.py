import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.product_category import ProductCategory
from app.models.inbound import Inbound
from app.models.outbound import Outbound
from app.models.movement import Movement
from app.routers import dashboard, upload
from app.services.product_categories import product_categories, dashboard_product_names
from test_multi_filters import request


class DashboardProductTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        with self.sessions() as db:
            product_categories(db)
        self.patch = patch.object(dashboard, 'SessionLocal', self.sessions)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.engine.dispose()

    def add_category(self, code='custom_product', name='새 제품'):
        with patch.object(upload, 'SessionLocal', self.sessions):
            result = upload.add_product_category({'code':code, 'name':name})
            self.assertEqual(result['status'], 'success')

    def trend(self, start='2026-09-09', end='2026-09-10'):
        return dashboard.dashboard_trend(request('/dashboard/trend'),start=start,end=end)

    def activity(self):
        return dashboard.dashboard_activity(request('/dashboard/activity'),start='2026-09-09',end='2026-09-10')

    def test_new_category_appears_immediately_with_zero_activity(self):
        self.assertNotIn('custom_product', {c['service'] for c in self.trend().context['charts']})
        self.add_category()
        chart = next(c for c in self.trend().context['charts'] if c['service']=='custom_product')
        self.assertEqual((chart['display_name'],chart['total_in'],chart['total_out']),('새 제품',0,0))
        sizes = dashboard.dashboard_size(request('/dashboard/size')).context['charts']
        self.assertIn('custom_product', {c['service'] for c in sizes})
        response = self.activity()
        self.assertIn('custom_product', response.context['SERVICES'])
        series = next(s for s in response.context['activity_series'] if s['code']=='custom_product')
        self.assertEqual(series['counts'],[0,0])

    def test_new_category_counts_and_period_boundaries(self):
        self.add_category()
        with self.sessions() as db:
            for model, kind, serial, day in [(Inbound,'IN','IN1',9),(Outbound,'OUT','OUT1',10),(Outbound,'OUT','OUT2',10),(Inbound,'IN','OLD',8)]:
                dt=datetime(2026,9,day,12)
                db.add(model(serial=serial,product='custom_product',size='9',created_at=dt))
                db.add(Movement(serial=serial,product='custom_product',type=kind,created_at=dt))
            db.commit()
        for end in ['2026-09-10','2026-10-10','2027-01-10']:
            response=self.trend(end=end)
            chart=next(c for c in response.context['charts'] if c['service']=='custom_product')
            self.assertEqual((chart['total_in'],chart['total_out']),(1,2))
            self.assertEqual(sum(c['total_in'] for c in response.context['charts']),response.context['total_in'])
            self.assertEqual(sum(c['total_out'] for c in response.context['charts']),response.context['total_out'])
        sizes=dashboard.dashboard_size(request('/dashboard/size')).context['charts']
        custom=next(c for c in sizes if c['service']=='custom_product')
        self.assertEqual((sum(custom['in_counts']),sum(custom['out_counts'])),(2,2))
        activity=self.activity().context
        self.assertEqual(next(s['counts'] for s in activity['activity_series'] if s['code']=='custom_product'),[1,2])
        self.assertEqual(next(s['count'] for s in activity['service_stats'] if s['name']=='새 제품'),3)
        overview=dashboard.dashboard_overview(request('/dashboard/overview'),start='2026-09-09',end='2026-09-10').context
        self.assertEqual((overview['period_in'],overview['period_out']),(1,2))

    def test_historical_code_without_catalog_entry_is_not_lost(self):
        with self.sessions() as db:
            db.add(Outbound(serial='legacy',product='legacy_product',created_at=datetime(2026,9,10)))
            db.commit()
            self.assertEqual(dashboard_product_names(db)['legacy_product'],'legacy_product')
        chart=next(c for c in self.trend().context['charts'] if c['service']=='legacy_product')
        self.assertEqual(chart['total_out'],1)

    def test_chart_serialization_and_display_name_refresh(self):
        self.add_category(name='새 "제품" <테스트>')
        response=self.activity()
        self.assertEqual(response.context['SERVICE_NAMES']['custom_product'],'새 "제품" <테스트>')
        self.assertIn('새 &#34;제품&#34; &lt;테스트&gt;', response.body.decode())
        Path('work/dashboard-tests').mkdir(parents=True,exist_ok=True)
        Path('work/dashboard-tests/activity.html').write_bytes(response.body)
        with self.sessions() as db:
            db.query(ProductCategory).filter_by(code='custom_product').one().name='변경된 제품'
            db.commit()
        self.assertEqual(self.activity().context['SERVICE_NAMES']['custom_product'],'변경된 제품')


if __name__ == '__main__':
    unittest.main()
