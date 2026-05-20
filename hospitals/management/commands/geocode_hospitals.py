import time
import requests
from django.core.management.base import BaseCommand
from hospitals.models import Hospital

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
HEADERS = {'User-Agent': 'genba-karte/1.0 (hrttkd1006@gmail.com)'}


def geocode(address):
    try:
        res = requests.get(NOMINATIM_URL, params={
            'q': address,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'jp',
        }, headers=HEADERS, timeout=10)
        data = res.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None


class Command(BaseCommand):
    help = '病院の住所から緯度・経度を取得してDBに保存します'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='すでに座標があるものも上書き')

    def handle(self, *args, **options):
        force = options['force']
        qs = Hospital.objects.all() if force else Hospital.objects.filter(lat__isnull=True)
        total = qs.count()
        self.stdout.write(f'対象: {total}件')

        ok = skip = fail = 0
        for i, hospital in enumerate(qs, 1):
            query = f"{hospital.address}" if hospital.address else f"{hospital.prefecture} {hospital.name}"
            lat, lng = geocode(query)

            if lat and lng:
                hospital.lat = lat
                hospital.lng = lng
                hospital.save(update_fields=['lat', 'lng'])
                ok += 1
                self.stdout.write(f'[{i}/{total}] OK {hospital.name} ({lat:.4f}, {lng:.4f})')
            else:
                # 住所で失敗したら施設名+都道府県で再試行
                lat, lng = geocode(f"{hospital.name} {hospital.prefecture}")
                if lat and lng:
                    hospital.lat = lat
                    hospital.lng = lng
                    hospital.save(update_fields=['lat', 'lng'])
                    ok += 1
                    self.stdout.write(f'[{i}/{total}] OK {hospital.name} (retry)')
                else:
                    fail += 1
                    self.stdout.write(f'[{i}/{total}] NG {hospital.name}')

            # Nominatimの利用規約: 1秒に1リクエスト
            time.sleep(1.1)

        self.stdout.write(f'\nDone: OK={ok} NG={fail}')
