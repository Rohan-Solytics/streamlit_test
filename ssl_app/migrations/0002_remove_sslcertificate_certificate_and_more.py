# Generated by Django 5.0.7 on 2024-07-25 04:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ssl_app', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sslcertificate',
            name='certificate',
        ),
        migrations.RemoveField(
            model_name='sslcertificate',
            name='private_key',
        ),
        migrations.AddField(
            model_name='sslcertificate',
            name='certificate_arn',
            field=models.CharField(default='0', max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sslcertificate',
            name='hostname',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
