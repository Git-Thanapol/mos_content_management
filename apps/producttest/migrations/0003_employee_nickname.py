from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('producttest', '0002_rename_pang_to_page'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='nickname',
            field=models.CharField(blank=True, max_length=100, verbose_name='ชื่อเล่น'),
        ),
        migrations.AlterField(
            model_name='employee',
            name='is_graphic',
            field=models.BooleanField(default=False, verbose_name='ตำแหน่ง Graphic'),
        ),
        migrations.AlterField(
            model_name='employee',
            name='is_mkt',
            field=models.BooleanField(default=False, verbose_name='ตำแหน่ง MKT'),
        ),
    ]
