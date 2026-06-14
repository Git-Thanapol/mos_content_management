"""
Read-only unmanaged mirrors of the JST (po_management) database tables.

These models map to existing tables in the 'jst' database.
Django will never create, alter, or delete these tables (managed=False).
All queries must use .using('jst').
"""
from django.db import models


class JstMasterItem(models.Model):
    """Maps to inventory_masteritem in the JST DB."""
    product_code = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    # image stored as char path — we won't serve it cross-origin
    image = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "inventory_masteritem"

    def __str__(self):
        return f"{self.product_code} — {self.name}"


class JstStockSnapshot(models.Model):
    """Maps to inventory_jststocksnapshot in the JST DB."""
    sku = models.ForeignKey(
        JstMasterItem,
        on_delete=models.DO_NOTHING,
        related_name="snapshots",
    )
    quantity = models.IntegerField()
    snapshot_date = models.DateField()

    class Meta:
        managed = False
        db_table = "inventory_jststocksnapshot"
        ordering = ["-snapshot_date", "-id"]


class JstPOHeader(models.Model):
    """Maps to inventory_poheader in the JST DB (only the fields we need)."""
    order_date = models.DateField()
    shipping_rate_thb_cbm = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        managed = False
        db_table = "inventory_poheader"


class JstPOItem(models.Model):
    """Maps to inventory_poitem in the JST DB (only the fields we need)."""
    header = models.ForeignKey(
        JstPOHeader,
        on_delete=models.DO_NOTHING,
        related_name="items",
    )
    sku = models.ForeignKey(
        JstMasterItem,
        on_delete=models.DO_NOTHING,
        related_name="po_items",
    )
    qty_ordered = models.IntegerField()
    price_baht = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_received_cbm = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    class Meta:
        managed = False
        db_table = "inventory_poitem"
