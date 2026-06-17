import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clearance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="clearanceproduct",
            name="date_added",
            field=models.DateField(default=datetime.date.today, verbose_name="วันที่ลงข้อมูล"),
        ),
    ]
