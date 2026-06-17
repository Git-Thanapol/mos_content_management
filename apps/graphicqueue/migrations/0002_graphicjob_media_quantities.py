from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("graphicqueue", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="graphicjob",
            name="media_quantities",
            field=models.JSONField(blank=True, default=dict, verbose_name="จำนวนสื่อต่อประเภท"),
        ),
    ]
