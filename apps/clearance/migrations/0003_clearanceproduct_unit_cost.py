from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clearance", "0002_clearanceproduct_date_added"),
    ]

    operations = [
        migrations.AddField(
            model_name="clearanceproduct",
            name="unit_cost",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="ต้นทุนสินค้า",
            ),
        ),
    ]
