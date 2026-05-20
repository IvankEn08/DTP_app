from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accidents", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE accidents_accident
                    DROP COLUMN IF EXISTS description,
                    DROP COLUMN IF EXISTS status,
                    DROP COLUMN IF EXISTS responsible_driver_id;

                ALTER TABLE accidents_accidentdriver
                    ADD COLUMN IF NOT EXISTS is_ready boolean NOT NULL DEFAULT false,
                    ADD COLUMN IF NOT EXISTS ready_at timestamp with time zone NULL,
                    DROP COLUMN IF EXISTS is_responsible;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
