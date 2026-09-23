"""Add ``row_hash`` to sat_cancelados and stop treating ``rfc`` as unique.

The same RFC legitimately appears in several distinct rows (a tax-payer can be
cancelled more than once), so de-duplication is now done by the full content
hash of each row: identical rows already stored are skipped on import.

The backfill computes hashes with an inline copy of
``domain.entities.sat_cancelado.sat_cancelado_row_hash`` (keep in sync) so that
rows imported before this change dedupe correctly against freshly imported
ones.
"""

import hashlib
import re

from django.db import migrations, models


def _collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _row_content_hash(row) -> str:
    parts = (
        (row.rfc or "").strip().upper(),
        _collapse_whitespace(row.razon_social),
        (row.tipo_persona or "").strip(),
        _collapse_whitespace(row.supuesto),
        row.fecha_de_cancelacion.isoformat(),
        f"{row.monto:.2f}",
        row.fecha_de_publicacion.isoformat(),
        (row.entidad_federativa or "").strip(),
    )
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


def backfill_row_hashes(apps, schema_editor):
    SatCanceladoORM = apps.get_model("ticketing", "SatCanceladoORM")
    for row in SatCanceladoORM.objects.iterator():
        row.row_hash = _row_content_hash(row)
        row.save(update_fields=["row_hash"])


class Migration(migrations.Migration):

    dependencies = [
        ("ticketing", "0003_satcanceladoorm_sathistoryorm"),
    ]

    operations = [
        migrations.AddField(
            model_name="satcanceladoorm",
            name="row_hash",
            field=models.CharField(max_length=64, null=True),
        ),
        migrations.RunPython(backfill_row_hashes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="satcanceladoorm",
            name="row_hash",
            field=models.CharField(max_length=64, unique=True),
        ),
        migrations.AlterField(
            model_name="satcanceladoorm",
            name="rfc",
            field=models.CharField(db_index=True, max_length=50),
        ),
    ]
