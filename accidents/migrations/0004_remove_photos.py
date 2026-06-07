from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accidents", "0003_driver_join_and_vehicle_owner_name"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="witnessstatement",
            name="photo",
        ),
        migrations.DeleteModel(
            name="AccidentPhoto",
        ),
    ]
