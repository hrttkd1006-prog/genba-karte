from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_hospitaladminapplication_official_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='hospitaladminapplication',
            name='prefecture',
            field=models.CharField(blank=True, max_length=10, verbose_name='都道府県'),
        ),
        migrations.AddField(
            model_name='hospitaladminapplication',
            name='address',
            field=models.CharField(blank=True, max_length=300, verbose_name='住所'),
        ),
        migrations.AddField(
            model_name='hospitaladminapplication',
            name='facility_type',
            field=models.CharField(blank=True, max_length=20, verbose_name='施設種別'),
        ),
    ]
