# Generated by Django 2.1.1 on 2018-09-27 19:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainsite', '0007_csvfiledata_designation'),
    ]

    operations = [
        migrations.CreateModel(
            name='MLModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('model_data', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]