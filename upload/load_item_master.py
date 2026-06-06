import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

import pandas as pd

from app.database import SessionLocal
from app.models.item_master import ItemMaster

db = SessionLocal()

df = pd.read_excel(
    "upload/채번 규칙 및 REV매칭.xlsx"
)

count = 0

for _, row in df.iterrows():

    item_code = str(
        row["품번"]
    ).strip()

    item_name = str(
        row["원자재"]
    ).strip()

    rev = str(
        row["REV"]
    ).strip()

    exists = (
        db.query(ItemMaster)
        .filter(
            ItemMaster.item_code == item_code
        )
        .first()
    )

    if exists:
        continue

    db.add(
        ItemMaster(
            item_code=item_code,
            item_name=item_name,
            rev=rev
        )
    )

    count += 1

db.commit()

print(
    f"{count}건 등록 완료"
)