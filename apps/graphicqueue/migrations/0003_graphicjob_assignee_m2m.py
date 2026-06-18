from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("graphicqueue", "0002_graphicjob_media_quantities"),
        ("producttest", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="graphicjob",
            name="assignee",
        ),
        migrations.AddField(
            model_name="graphicjob",
            name="assignee",
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={"is_active": True, "is_graphic": True},
                related_name="graphic_jobs",
                to="producttest.employee",
                verbose_name="ผู้รับผิดชอบ",
            ),
        ),
    ]
